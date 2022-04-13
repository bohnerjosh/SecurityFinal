from bnp.config import Config
from bnp.diary import DiaryException, DiaryFactory
from datetime import datetime
from flask import Flask, abort, request, jsonify, render_template, url_for, session
from itsdangerous import URLSafeSerializer
import os

app = Flask(__name__)
app.secret_key = b'kjlaqetgffrvdup980j3'


SERVER_CONFIG_ROOT = './.bnp-server'
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


@app.route('/diaries', methods=['GET'])
def web_diaries():
    config = Config(SERVER_CONFIG_ROOT)
    combo_diaries = config.get_diaries()
    diary_objs = combo_diaries[0]

    d_names = [get_diaryname_from_key(d.name) for d in diary_objs]
    d_key_lst = [k.name for k in diary_objs]

    length = len(d_names)
    ids = [i for i in range(length)]

    session['keys'] = dict(zip(ids, d_key_lst))
    return render_template(
        "diaries.html",
        d_names=d_names,
        d_ids=ids,
        _len=length
    )


@app.route('/diaries/<string:diary_id>/', methods=['GET'])
def web_entries(diary_id):
    config = Config(SERVER_CONFIG_ROOT)
    diary_key = session['keys'][diary_id]
    diary = DiaryFactory.get_diary(diary_key, config)
    entries = diary.get_entries()
    name = get_diaryname_from_key(diary_key)
    return render_template("entries.html", entries=entries, name=name)


@app.route('/')
def index():
    return 'Server running... brief documentation should go here'


if __name__ == '__main__':
    app.run()
