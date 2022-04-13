from pathlib import Path
import shutil
from bnp.diary import LocalDiary, DiaryFactory
from bnp.utils import sorted_iterdir

__all__ = ['Config', 'ConfigException']

DEFAULT_DIARY_BASEDIR = '.bnp'
DEFAULT_DIARY_NAME = 'default'
DEFAULT_CONFIG_NAME = 'config'
DEFAULT_REMOTE_NAME = 'remote'


class ConfigException(Exception):
    pass


class Config(object):
    def __init__(self, basedir=DEFAULT_DIARY_BASEDIR):
        self.basepath = Path.home() / basedir
        self.configpath = self.basepath / DEFAULT_CONFIG_NAME
        self.params = {}
        self.current_diary = None
        self.ensure_config()
        self.valid = True
        self.load_config()

    def delete(self):
        shutil.rmtree(str(self.basepath))
        self.valid = False

    def check_invalid(self):
        if not self.valid:
            raise ConfigException(
                'Internal error: operation attempted on a configuration ' +
                'that has been deleted.'
            )

    def ensure_config(self):
        if not self.basepath.exists():
            self.basepath.mkdir()

        if not self.configpath.exists():
            with open(str(self.configpath), 'w') as cfgfile:
                cfgfile.write(f'diary_name:{DEFAULT_DIARY_NAME}\n')

    def load_config(self):
        with open(str(self.configpath), 'r') as cfgfile:
            for name_value in cfgfile:
                name, value = name_value.rstrip().split(':')
                self.params[name] = value

        diary_name = self.params['diary_name']
        self.set_current_diary(name=diary_name)

    def update_config(self):
        self.params['diary_name'] = self.current_diary.name
        with open(str(self.configpath), 'w') as cfgfile:
            for name in self.params:
                value = self.params[name]
                cfgfile.write('{}:{}\n'.format(name, value))

    def get_current_diary(self):
        self.check_invalid()

        return self.current_diary

    def set_current_diary(self, **kwargs):
        self.check_invalid()

        if 'diary' in kwargs:
            self.current_diary = kwargs['diary']
        elif 'name' in kwargs:
            if kwargs['name'] == DEFAULT_CONFIG_NAME:
                raise ConfigException(
                    f'Cannot name a diary "{DEFAULT_CONFIG_NAME}"'
                )
            self.current_diary = DiaryFactory.get_diary(kwargs['name'], self)
        else:
            raise ConfigException(
                'Internal error: attempt to change diaries ' +
                'without specifying which one'
            )

        self.update_config()

    def get_diaries(self):
        self.check_invalid()
        local_diaries = []
        remote_diaries = []

        for p in sorted_iterdir(self.basepath):
            if p.name != DEFAULT_CONFIG_NAME:
                a_diary = DiaryFactory.get_diary(p.name, self)
                if type(a_diary).__name__ == 'RemoteDiary':
                    remote_diaries.append(a_diary)
                else:
                    local_diaries.append(a_diary)
        diaries = [local_diaries, remote_diaries]
        return diaries

    def has_diary(self, **kwargs):
        self.check_invalid()

        diary_name = ''
        if 'diary' in kwargs:
            diary_name = kwargs['diary'].name
        elif 'name' in kwargs:
            diary_name = kwargs['name']
        else:
            raise ConfigException(
                'Internal error: attempt to check for existence of ' +
                'a diary without specifying its name'
            )

        if diary_name:
            return (self.basepath / diary_name).exists()

        return False

    def has_remote_file(self, **kwargs):
        self.check_invalid()
        diary_name = ''
        func = ''
        if 'f_name' in kwargs:
            func = kwargs['f_name']
        if 'diary' in kwargs:
            diary_name = kwargs['diary'].name
        elif 'name' in kwargs:
            diary_name = kwargs['name']
        else:
            raise ConfigException(
                'Internal error: attempt to check for existence of ' +
                'a diary without specifying its name'
            )
        if func == 'key':
            if (self.basepath / diary_name / DEFAULT_REMOTE_NAME).exists():
                return True
            else:
                raise ConfigException(
                    f'{diary_name} is not a remote diary.'
                )
        return (self.basepath / diary_name / DEFAULT_REMOTE_NAME).exists()

    def delete_diary(self, **kwargs):
        self.check_invalid()

        diary_name = ''
        if 'diary' in kwargs:
            diary_name = kwargs['diary'].name
            kwargs['diary'].delete()
        elif 'name' in kwargs and kwargs['name'] == 'config':
            raise ConfigException('No such diary "config"')
        elif 'name' in kwargs and kwargs['name'] != '':
            diary_name = kwargs['name']
            diary_path = self.basepath / diary_name
            if diary_path.exists():
                diary = DiaryFactory.get_diary(diary_name, self)
                diary.delete()
            else:
                raise ConfigException(
                    f'No such diary "{diary_name}"'
                )
        else:
            raise ConfigException(
                'Internal error: attempt to delete ' +
                'a diary without specifying its name'
            )

        # If we just deleted the current diary, we need to move back
        # to default.  Default is always local.
        if self.current_diary.name == diary_name:
            d = LocalDiary(
                DEFAULT_DIARY_NAME,
                self.basepath / DEFAULT_DIARY_NAME
            )
            self.current_diary = d
            self.update_config()

    def promote_diary(self, diaryname, url, user):
        if not self.has_diary(name=diaryname):
            raise ConfigException(
                f'No such diary "{diaryname}"'
            )
        elif self.has_remote_file(name=diaryname):
            raise ConfigException(
                f'"{diaryname}" is not a local diary'
            )
        diary = DiaryFactory.get_diary(diaryname, self)
        entries = diary.get_entries()
        diary.delete()
        try:
            remote_diary = DiaryFactory.create_remote_diary(
                    diaryname,
                    self,
                    url,
                    user)
        except Exception:
            diary = DiaryFactory.get_diary(diaryname, self)
            for entry in entries:
                diary.add_entry(entry.text,
                                entry.date,
                                entry.username)
            raise ConfigException(
                'Failed to connect to the server'
            )
        for entry in entries:
            remote_diary.add_entry(entry.text,
                                   entry.date,
                                   entry.username)
        return remote_diary.get_diarykey()

    def demote_diary(self, diary_name):
        if not self.has_diary(name=diary_name):
            raise ConfigException(
                f'No such diary "{diary_name}"'
            )
        diary = DiaryFactory.get_diary(diary_name, self)
        diarypath = self.basepath / diary_name
        remotefile = diarypath / 'remote'
        if not remotefile.exists():
            raise ConfigException(
                f'"{diary_name}" is not a remote diary'
            )
        entries = diary.get_entries()
        diary.delete()
        diary = DiaryFactory.get_diary(diary_name, self)
        for ent in entries:
            diary.add_entry(ent.text, ent.date, ent.username)
