from bnp.config import Config
from bnp.diary import DiaryException, DiaryFactory
from datetime import datetime
from flask import Flask, abort, request, jsonify, render_template, url_for, session, redirect
from itsdangerous import URLSafeSerializer
import os
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from sqlalchemy.sql import func, and_
from werkzeug.utils import secure_filename 

app = Flask(__name__)
app.secret_key = b'kjlaqetgffrvdup980j3'

sqlite_uri = 'sqlite:///' + os.path.abspath(os.path.curdir) + '/server/Main.db'
app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

SERVER_CONFIG_ROOT = './.bnp-server'
UPLOADS_DIR = 'server/static/img/profilephotos'

from server.models import *

# Although it is called 'username, the authorization key is not
# actually the user's username. The authorization header that
# is sent to the Flask server is just called 'username', but
# in actuality we are passing the diary's secret key,
# which is sent back from the server when the user initially
# creates the remote diary.

'''
The user passes the secret key, this becomes the diary's name.
'''
AUTH_KEY = 'username'

def get_current_profile():
    if 'id' in session:
        return Profile.query.get(session['id'])
    else:
        return False

@app.before_first_request
def app_init():
    imgdir = Path(UPLOADS_DIR)
    if not imgdir.exists():
        imgdir.mkdir(parents=True)
    try:
        profile.query.all()
    except:
        db.create_all()

def generate_key(diaryname, username):
    auth_s = URLSafeSerializer(os.environ['SECRET_KEY'], 'auth')
    diarykey = auth_s.dumps({'diaryname': diaryname, 'username': username})
    return diarykey


def get_diaryname_from_key(diarykey):
    if diarykey == 'default':
        return 'default'
    auth_s = URLSafeSerializer(os.environ['SECRET_KEY'], 'auth')
    data = auth_s.loads(diarykey)
    return data['diaryname']


@app.route('/api/init', methods=['POST'])
def init_diary():
    f = request.form
    if not f.get('username') or not f.get('diaryname'):
        abort(400)

    diarykey = generate_key(f['diaryname'], f['username'])

    config = Config(SERVER_CONFIG_ROOT)
    DiaryFactory.get_diary(diarykey, config)

    return jsonify({'key': diarykey})


@app.route('/api/verify', methods=['GET'])
def connect():
    if request.authorization:
        diarykey = request.authorization.get(AUTH_KEY)
        try:
            diaryname = get_diaryname_from_key(diarykey)
            config = Config(SERVER_CONFIG_ROOT)
            if config.has_diary(name=diarykey):
                return jsonify({'result': 'ok', 'diaryname': diaryname})
        except Exception:
            return jsonify({'result': "error"})
    return jsonify({'result': "error"})


@app.route('/api/wipe', methods=['DELETE'])
def delete_diary():
    diarykey = ''
    if request.authorization:
        diarykey = request.authorization.get(AUTH_KEY)

    config = Config(SERVER_CONFIG_ROOT)
    # diaryname = get_diaryname_from_key(key)
    config.delete_diary(name=diarykey, config=config)

    return jsonify({})


@app.route('/api/log', methods=['POST'])
def add_entry():
    '''
        The client must provide a project key via
        BasicAuth and 'text' via the POST form.
        Failure to do so will result in a 400 error.

        If both are provided, the server will return
            { 'result': 'ok' }

        There is currently no further error checking
        in this route.
    '''
    diarykey = ''
    if request.authorization:
        diarykey = request.authorization.get(AUTH_KEY)

    config = Config(SERVER_CONFIG_ROOT)
    # diaryname = get_diaryname_from_key(key)
    diary = DiaryFactory.get_diary(diarykey, config)
    date = datetime.now()
    form = request.form
    diary.add_entry(form.get('text'), date, form.get('username'))

    return jsonify({'result': 'ok'})


@app.route('/api/rm/<int:the_id>/', methods=['DELETE'])
def remove_entry(the_id):
    '''
        The client must provide a project key via
        BasicAuth and an entry ID as part of the URL.
        Failure to do so will result in a 400 error.

        If both are provided, the server will return either
            { 'result': 'ok' }
        or
            { 'result': 'error', 'type': ERROR_STR }
        where ERROR_STR is currently one of
            'bad_id'    -- there is no entry with that ID
            'internal'  -- unknown internal error; this should
                           never happen
    '''
    diarykey = ''
    if request.authorization:
        diarykey = request.authorization.get(AUTH_KEY)

    config = Config(SERVER_CONFIG_ROOT)
    # diaryname = get_diaryname_from_key(key)
    diary = DiaryFactory.get_diary(diarykey, config)
    try:
        diary.remove_entry(the_id)
    except DiaryException:
        return jsonify({'result': 'error', 'type': 'bad_id'})

    return jsonify({'result': 'ok'})


@app.route('/api/list', methods=['GET'])
def list_entries():
    '''
        The client must provide a project key via
        BasicAuth.  Failure to do so will result in
        a 400 error.

        If both are provided, the server will return
            { 'result': entry_list }
        where entry_list is a list of dicts, each
        containing the same properties as a blurg.diary.Entry
        object.

        There is currently no further error checking
        in this route.
    '''
    diarykey = ''
    if request.authorization:
        diarykey = request.authorization.get(AUTH_KEY)

    config = Config(SERVER_CONFIG_ROOT)
    # diaryname = get_diaryname_from_key(key)
    diary = DiaryFactory.get_diary(diarykey, config)
    entries = diary.get_entries()
    entries = list(map(lambda ent: {
        'id': ent.id,
        'text': ent.text,
        'username': ent.username,
        'date': ent.date.strftime('%m-%d-%Y %H:%M'),
    }, entries))

    return jsonify({'result': entries})

    ###########################
    ###     Website routes  ###
    ###########################

def get_web_diaries():
    config = Config(SERVER_CONFIG_ROOT)
    combo_diaries = config.get_diaries()
    diary_objs = combo_diaries[0]

    d_names = [get_diaryname_from_key(d.name) for d in diary_objs]
    d_key_lst = [k.name for k in diary_objs]

    length = len(d_names)
    ids = [i for i in range(length)]

    session['keys'] = dict(zip(ids, d_key_lst))
    return d_names, ids, length
    

@app.route('/diaries/<string:diary_id>/', methods=['GET'])
def web_entries(diary_id):
    config = Config(SERVER_CONFIG_ROOT)
    diary_key = session['keys'][diary_id]
    diary = DiaryFactory.get_diary(diary_key, config)
    entries = diary.get_entries()
    name = get_diaryname_from_key(diary_key)
    return render_template("entries.html", entries=entries, name=name)

@app.route('/main/', methods=['GET'])
def main():
    # Query from database
    profile = get_current_profile()
    if profile:
        profile = Profile.query.get(session['id'])
    else:
        profile=0
    d_names, d_ids, _len = get_web_diaries()
    return render_template('main.html', profile=profile, d_names=d_names, d_ids = d_ids, _len=_len)

@app.route('/login/', methods=['GET'])
def login_form():
    return render_template('login.html')

@app.route('/login/', methods=['POST'])
def post_form():
    #make sure that thing below is adding to session properly
    inuser = request.form['username']
    inpw = request.form['pw']
    message = ""
    usermatch = Profile.query.filter_by(username=inuser, password=inpw).first()
    try:
        if usermatch.username == inuser and usermatch.password == inpw:
            session['id'] = usermatch.id

            return redirect(url_for('main'))
        else:
        
            message = "Invalid username/password combination."
            return render_template('login.html', message=message)
    except:
        message = "Invalid username/password combination."
    return render_template('login.html', message=message)



@app.route('/profile/create/', methods=['GET'])
def create_profile():
    return render_template('createprofile.html')

@app.route('/profile/create/', methods=['POST'])
def post_profile():
    #create profile from given items
    showerror = False
    message = ""
    inuser = request.form['username']
    usermatch = Profile.query.filter_by(username=inuser).first()
    try:
        if usermatch.username == inuser:
            showerror = True
            message = "Could not create profile: that username is already taken."
    except:
        message = ""

    inemail = request.form['email']
    inpw = request.form['pw']
    infile = request.files['propic']
    filename = secure_filename(infile.filename)
    filename = inuser + filename
    filepath = os.path.join(UPLOADS_DIR, filename)
    
    if inuser == "":
        showerror = True
        message = "Username cannot be blank."
    elif inemail == "":
        showerror = True
        message = "Email cannot be blank."
    elif inpw == "":
        showerror = True
        message = "Password cannot be blank."
    
    if showerror:
        return render_template('createprofile.html', message=message)

    if infile:
        infile.save(filepath)
        prof_id = db.session.query(func.count(Profile.id).label('count'))
        prof_id = str(prof_id.first())
        prof_id = int(prof_id[1:-2])
        prof_id += 1
        p = Profile(id=prof_id, username=inuser, password=inpw, email=inemail, photofn = filename)
        db.session.add(p)
        db.session.commit() 

        return redirect(url_for('login_form'))
    else:
        message = "Invalid file type."
        return render_template('createprofile.html', message=message)

@app.route('/profile/', methods=['GET'])
def my_profile():
    profile = get_current_profile()
    return render_template('profile.html', profile=profile, username=profile.username)

@app.route('/profile/<int:profile_id>/', methods=['GET'])
def show_profile(profile_id):
    other_profile = Profile.query.get(profile_id)
    if other_profile:
        return render_template('profile.html', profile=other_profile)
    else:
        abort(404)

@app.route('/post/create', methods=['GET'])
def create_post():
    profile = get_current_profile()
    return render_template("createpost.html", profile=profile) 

@app.route('/')
def index():
    return redirect(url_for("main"))


if __name__ == '__main__':
    app.run()
