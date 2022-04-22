from abc import ABC, abstractmethod
from datetime import datetime
from bnp.utils import sorted_iterdir
import shutil
import requests
import getpass
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError

__all__ = ['DiaryException', 'DiaryFactory', 'Entry',
           'LocalDiary', 'RemoteDiary']

REMOTE_DIARY_FNAME = 'remote'


class DiaryException(Exception):
    pass


class DiaryFactory(object):
    @staticmethod
    def get_diary(diaryname, config):
        diarypath = config.basepath / diaryname
        remotefile = diarypath / REMOTE_DIARY_FNAME

        if remotefile.exists():
            return RemoteDiary(diaryname, diarypath)
        else:
            return LocalDiary(diaryname, diarypath)

    @staticmethod
    def create_remote_diary(diaryname, config, url, name):
        diarypath = config.basepath / diaryname
        remotefile = diarypath / REMOTE_DIARY_FNAME
        if diaryname == 'default' or diaryname == 'config':
            raise DiaryException(f"You can't make a diary called {diaryname}")
        elif diarypath.exists() and not remotefile.exists():
            raise(DiaryException("That already exists locally"))
        elif diarypath.exists() and remotefile.exists():
            raise(DiaryException(
                'Cannot switch to a diary that already exists locally.\n'
                'Please wipe and try again'
                ))
        try:
            result = requests.post('{}/api/init'.format(url),
                                   data={
                                       'diaryname': diaryname,
                                       'username': name,
                                       })
        except ConnectionError:
            raise DiaryException('Failed to connect to the server')
        r = result.json()
        key = r['key']
        if not diarypath.exists():
            diarypath.mkdir()

        # Make the remote file
        with open(remotefile, 'w+') as remfile:
            remfile.write(f'url:{url}\nkey:{key}\nusername:{name}\n')

        return RemoteDiary(diaryname, diarypath)

    @staticmethod
    def create_local_remote_diary(diaryname, key, username, config, url):
        diarypath = config.basepath / diaryname
        remotefile = diarypath / REMOTE_DIARY_FNAME
        if diarypath.exists() and not remotefile.exists():
            raise(DiaryException("That already exists locally"))
        elif diarypath.exists() and remotefile.exists():
            raise(DiaryException(
                'Cannot switch to a diary that already exists locally.\n'
                'Please wipe and try again'
                ))
        if not diarypath.exists():
            diarypath.mkdir()

        with open(remotefile, 'w+') as remfile:
            remfile.write(f'url:{url}\nkey:{key}\nusername:{username}\n')

        return RemoteDiary(diaryname, diarypath)


class AbstractDiary(ABC):
    def __init__(self, name, path):
        self.name = name
        self.path = path

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def add_entry(self, content, date=datetime.now(), username=None):
        pass

    @abstractmethod
    def remove_entry(self, entry_id):
        pass

    @abstractmethod
    def get_entries(self):
        pass


class RemoteDiary(AbstractDiary):
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.params = {}

        if not self.path.exists():
            self.path.mkdir()

    def delete(self):
        self.load_remote()
        try:
            requests.delete('{}/api/wipe'.format(self.params['url']),
                            auth=HTTPBasicAuth(self.params['key'], ''),
                            data={})
        except ConnectionError:
            raise DiaryException('Failed to connect to the server')
        shutil.rmtree(str(self.path))

    def add_entry(self, content, date=datetime.now(), username=None):
        self.load_remote()
        username = self.params['username']
        try:
            result = requests.post('{}/api/log'.format(self.params['url']),
                                   auth=HTTPBasicAuth(self.params['key'], ''),
                                   data={
                                         'text': content,
                                         'username': username
                                        })
        except ConnectionError:
            raise DiaryException('Failed to connect to the server')
        res = result.json()
        if not res['result'] == 'ok':
            raise DiaryException("Error upon creating entry.")

    def remove_entry(self, entry_id):
        self.load_remote()
        try:
            result = requests.delete('{}/api/rm/{}/'.format(self.params["url"],
                                                            str(entry_id)),
                                     auth=HTTPBasicAuth(self.params["key"],
                                                        ''))
        except ConnectionError:
            raise DiaryException('Failed to connect to the server')
        r = result.json()
        if r['result'] == 'error' and r['type'] == 'bad_id':
            raise DiaryException(f'No such entry {entry_id}')

    def get_entries(self):
        self.load_remote()
        # Server gives list of entries as a result
        try:
            result = requests.get('{}/api/list'.format(self.params["url"]),
                                  auth=HTTPBasicAuth(self.params['key'],
                                                     ''))
        except ConnectionError:
            return -1
        results = result.json()
        res = results['result']
        E = []
        # Each entry has entry ID, text, date, so make Entry object with them
        for entry in res:
            ent_id = entry.get('id')
            ent_text = entry.get('text')
            ent_date = entry.get('date')
            ent_date = datetime.strptime(ent_date, '%m-%d-%Y %H:%M')
            ent_username = entry.get('username')
            ent = Entry(ent_id, ent_text, ent_date, ent_username)
            E.append(ent)
        return E

    def get_diarykey(self):
        self.load_remote()
        return self.params['key']

    def load_remote(self):
        with open(self.path / REMOTE_DIARY_FNAME, 'r') as remfile:
            for name_value in remfile:
                name, value = name_value.strip().split(':', 1)
                self.params[name] = value


class LocalDiary(AbstractDiary):
    def __init__(self, name, path, username=None):
        self.name = name
        self.path = path
        self.username = ""

        if not self.path.exists():
            self.path.mkdir()

    def delete(self):
        shutil.rmtree(str(self.path))

    def next_idnum(self):
        max_idnum = 0
        for p in self.path.iterdir():
            fname = p.name
            if fname.endswith('.txt'):
                idnum = int(fname[fname.rfind('/')+1:fname.rfind('-')])
                max_idnum = max(idnum, max_idnum)
        return max_idnum + 1

    def add_entry(self,
                  content,
                  date=datetime.now(),
                  username=getpass.getuser()):

        filename = f'{self.next_idnum()}-{username}$' \
                   f'{date.strftime("%Y%m%d%H%M")}.txt'

        with open(str(self.path / filename), 'w') as f:
            f.write(content + '\n')

    def remove_entry(self, entry_id):
        success = False
        for fp in self.path.iterdir():
            if fp.name.startswith(f'{entry_id}-'):
                fp.unlink()
                success = True
                break

        if not success:
            raise DiaryException(f'No such entry {entry_id}')

    def get_entries(self, username=None):
        E = []
        filter_username = False

        if username is not None:
            filter_username = True

        for p in sorted_iterdir(self.path):
            text = p.open().read()
            if filter_username:
                ent_username = p.name[p.name.find('-')+1:p.name.find('$')]
                if ent_username != username:
                    continue
            ent_id = int(p.name[:p.name.find('-')])
            username = p.name[p.name.find('-')+1:p.name.find('$')]
            timestr = p.name[p.name.find('$')+1:p.name.find('.txt')]
            ent = Entry(ent_id,
                        text,
                        datetime.strptime(timestr, '%Y%m%d%H%M'),
                        username)

            E.append(ent)

        return E

    def written_by_usr(self, username):
        for p in sorted_iterdir(self.path):
            text = p.open().read()
            ent_username = p.name[p.name.find('-')+1:p.name.find('$')]
            if ent_username == username:
                return True

        return False

class Entry(object):
    def __init__(self, ent_id, text, date, username=None, u_id=None):
        self.id = ent_id
        self.text = text
        self.date = date
        self.username = username
        self.u_id = u_id
        self.diaryname = None

    def date_str(self):
        return self.date.strftime('%m-%d-%Y %H:%M')

    def serialize(self):
        return {
            'diaryname': self.diaryname,
            'id': self.id,
            'text': self.text,
            'date': self.date,
            'username': self.username,
            'u_id': self.u_id
        }
