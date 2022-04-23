from bnp.config import Config
from bnp.diary import DiaryException, DiaryFactory
from bnp.heap import MinHeap
from datetime import datetime
from flask import Flask, abort, request, jsonify, render_template, url_for, session, redirect
from itsdangerous import URLSafeSerializer
import os
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from sqlalchemy.sql import func, and_
from werkzeug.utils import secure_filename 
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)
app.secret_key = b'kjlaqetgffrvdup980j3'

sqlite_uri = 'sqlite:///' + os.path.abspath(os.path.curdir) + '/server/Main.db'
app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

SERVER_CONFIG_ROOT = './.bnp-server'
UPLOADS_DIR = 'server/static/img/profilephotos'
DEFAULT_MAIN_ENTRY_PRINT = 5

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
minHeap = MinHeap(1000)

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
DEFAULT_MAIN_ENTRY_PRINT = 5

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
    ###     Website funcs   ###
    ###########################

def verify_diary_creation(diary_name, profile):
    message = ""
    display_message = False
    if diary_name == 'default' or diary_name == 'config':
        display_message = True
        message = f"Cannot make a diaryname called {diary_name}"
    
    diary_key = generate_key(diary_name, profile)

    # verify the diary doesn't already exist
    config = Config(SERVER_CONFIG_ROOT)
    diarypath = config.basepath / diary_key
    if diarypath.exists():
        display_message = True
        message = "That diary already exists. Pick a different name."

    # if errors, return back to post create screen
    if display_message:
        profile = get_current_profile().username
        return 'error', message

    # otherwise create diary and add to session
    DiaryFactory.get_diary(diary_key, config)
    session['keys'][diary_name] = diary_key
    return 'ok', diary_key

def website_log_entry(diarykey, text, username):
    config = Config(SERVER_CONFIG_ROOT)
    diary = DiaryFactory.get_diary(diarykey, config)

    date = datetime.now()
    diary.add_entry(text, date, username)

def get_diaries_from_nologinuser(username):
    config = Config(SERVER_CONFIG_ROOT)
    diary_objs = config.get_diaries()[0]
    usr_diary_objs = [d for d in diary_objs if d.written_by_usr(username)]
    d_names = [get_diaryname_from_key(d.name) for d in diary_objs]
    d_key_lst = [k.name for k in diary_objs]
    
    diaries = dict(zip(d_names, d_key_lst))
    return diaries

def init_session(username):
    config = Config(SERVER_CONFIG_ROOT)
    diary_objs = config.get_diaries()[0]
    usr_diary_objs = [d for d in diary_objs if d.written_by_usr(username)]
    d_names = [get_diaryname_from_key(d.name) for d in diary_objs]
    d_key_lst = [k.name for k in diary_objs]
    
    session['keys'] = dict(zip(d_names, d_key_lst))
   
def get_private_dnames():
    u_id = get_current_profile().id
    diaries = PrivateDiary.query.filter_by(profile_id=u_id).all()
    dnames = [d.name for d in diaries]
    return dnames

def get_client_diaries():
    diary_names = list(session['keys'].keys())
    private_diaries = get_private_dnames()
    diary_names += private_diaries
    return diary_names

def get_main_diaries():
    config = Config(SERVER_CONFIG_ROOT)
    diaries = config.get_diaries()[0]
    entry_list = []
    for diary in diaries:
        name = get_diaryname_from_key(diary.name)
        entries = diary.get_entries()
        for entry in entries:
            entry.diaryname = name
            user = Profile.query.filter_by(username=entry.username).first()
            
            entry.u_id = user.id
            
        entry_list += entries
            
    for entry in entry_list:
        minHeap.insert(entry) 

    ###########################
    ###     Website routes  ###
    ###########################


@app.route('/api/get_main_diary_entries/', methods=['GET'])
def main_diary_entries():
    done = False
    size = minHeap.size
    if size < DEFAULT_MAIN_ENTRY_PRINT:
        size = minHeap.size
        done=True
    else:
        size = DEFAULT_MAIN_ENTRY_PRINT
    entry_lst = [minHeap.getMin().serialize() for i in range(size)]
    return jsonify(entry_lst)
    
@app.route('/api/get_public_profile_diaries/', methods=['GET'])
def get_public_profile_diaries():
    # get the username if passed one. 
    # This is for visiting other people's profiles
    logged_in = True    

    profile = get_current_profile()
    if not profile:
        logged_in = False
    else:
        username = profile.username

    if 'profile_id' in request.args:
        profile_id = request.args.get('profile_id')
        profile = Profile.query.get(profile_id)
        username = profile.username
 
    config = Config(SERVER_CONFIG_ROOT)
    if logged_in:
        diaries = session['keys']

    else:
        diaries = get_diaries_from_nologinuser(profile.username)
    
    entries_lst = []
    for diary in diaries:
        diaryname = diaries[diary]
        diary_obj = DiaryFactory.get_diary(diaryname, config)
        entries = diary_obj.get_entries(username)
        for entry in entries:
            entry.diaryname = diary
            entries_lst.append(entry.serialize())
    return jsonify(entries_lst)


@app.route('/api/get_private_diaries/', methods=['GET'])
def get_private_profile_diaries():
    # gets posts
    profile_id = get_current_profile().id
    if 'profile_name' in request.args:
        u_name = request.args.get('profile_name')
        profile_id = Profile.query.filter_by(username=u_name).id()
    
    entries = PrivateDiary.query.filter_by(profile_id=profile_id).all()
    entries = list(map(lambda private_diary: private_diary.serialize(), entries))
    return jsonify(entries)

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
    minHeap.clear()
    get_main_diaries()
    profile = get_current_profile()
    if not profile:
        profile=0
    return render_template('main.html', login_profile=profile)
    

@app.route('/login/', methods=['GET'])
def login_form():
    profile = get_current_profile()
    if profile:
        profile = Profile.query.get(session['id'])
    else:
        profile=0
    return render_template('login.html', login_profile=profile)

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
            session['keys'] = {}
            session['viewed'] = {}
            init_session(usermatch.username)
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
    return render_template('profile.html', login_profile=profile, profile=profile)

@app.route('/profile/<int:profile_id>/', methods=['GET'])
def show_profile(profile_id):
    login_user = get_current_profile()
    other_profile = Profile.query.get(profile_id)
    if other_profile:
        return render_template('profile.html', login_profile=login_user, profile=other_profile)
    else:
        abort(404)

@app.route('/diary/log', methods=['GET'])
def log_diary():
    profile = get_current_profile()
    diary_names = get_client_diaries()
    return render_template("createpost.html", login_profile=profile, dnames=diary_names) 

    diary_names = session['keys'].keys()
    private_diaries = get_private_dnames()
    diary_names += private_diaries

@app.route('/diary/log', methods=['POST'])
def post_log_diary():
    diary_key = ""

    profile = get_current_profile()
    diary_type = request.form['dtype']
    diary_name = request.form['dname']
    diary_text = request.form['content']

    if diary_type == "public":

        profile = profile.username
        if diary_name in session['keys']:
            diary_key = session['keys'][diary_name]
        else:
            status, message = verify_diary_creation(diary_name, profile)
            if status == 'error':
                return render_template("createpost.html", login_profile=profile, message=message)

            diary_key = message
        
        
        website_log_entry(diary_key, diary_text, profile)
        return redirect(url_for('my_profile'))

    
    date = datetime.now()
    date = date.strftime('%m-%d-%Y %H:%M')
    private_diary = PrivateDiary(content=diary_text, profile_id=profile.id, name=diary_name, date=date)

    db.session.add(private_diary)
    db.session.commit()
    return redirect(url_for('my_profile'))

@app.route('/profile/key_management', methods=['GET'])
def get_key_management():
    profile = get_current_profile()
    diary_names = get_client_diaries()
    return render_template("key_management.html", login_profile=profile, dnames=diary_names)

@app.route('/key_management/new/private', methods=['POST'])
def new_private():
    message = ""
    diary_name = request.form['dname']
    profile = get_current_profile()
    usermatch = PrivateDiary.query.filter_by(name=diary_name).first()
    try:
        if usermatch == diary_name:
            message = "A diary with that name already exists"
        elif diary_name == "":
            message = "Diary name cannot be blank"

        diary_names = get_client_diaries()
        return render_template("key_management.html", login_profile=profile, dnames=diary_names, message=message)
    except:
        date = datetime.now()
        date = date.strftime('%m-%d-%Y %H:%M')
        private_diary = PrivateDiary(content=diary_text, profile_id=profile.id, name=diary_name, date=date)

        db.session.add(private_diary)
        db.session.commit()
        return redirect(url_for('get_key_management'))

@app.route('/key_management/connect', methods=['POST'])
def mgmnt_connect():
    pass

@app.route('/key_management/new/public', methods=['POST'])
def new_public():
    message = ""
    diary_name = request.form["dname"]
    profile = get_current_profile()
    status, message = verify_diary_creation(diary_name, profile.username)
    
    diary_names = get_client_diaries()
    if status == 'error':
        return render_template("key_management.html", login_profile=profile, dnames=diary_names, message=message)
    else:
        diary_key = message
        print(session['keys'])
        return render_template("key_management.html", login_profile=profile, dnames=diary_names, diary_key=diary_key)

@app.route('/key_management/get_diarykey', methods=['POST'])
def get_diarykey():
    profile = get_current_profile()
    message = ""
    diary_names = session['keys'].keys()
    diary_name = request.form["diaryname"]
    if diary_name in session['keys']:
        print(session['keys'])
        diary_key = session['keys'][diary_name]
        return render_template("key_management.html", login_profile=profile, dnames=diary_names, diary_key=diary_key)
    else:
        message = "invalid diary name or it is a private diary"
        return render_template("key_management.html", login_profile=profile, dnames=diary_names, message=message)

@app.route('/logout/', methods=['GET'])
def logout():
    # remove username from session to logout and then just go to login page
    del session['id']
    del session['keys']
    del session['viewed']
    return redirect(url_for('main'))

@app.route('/')
def index():
    return redirect(url_for("main"))


if __name__ == '__main__':
    app.run()
