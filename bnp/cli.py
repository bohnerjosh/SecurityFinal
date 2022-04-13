import os
from sys import argv
from bnp.diary import DiaryException, DiaryFactory
from bnp.config import Config, ConfigException
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError
import requests

DEFAULT_PROG_NAME = 'bnp'

commands = ['log', 'rm', 'ls', 'switch', 'diaries',
            'wipe', 'connect', 'key', 'promote', 'demote']

progname = DEFAULT_PROG_NAME
if 'DIARY_PROG_NAME' in os.environ:
    progname = os.environ['DIARY_PROG_NAME']


class CommandException(Exception):
    pass


class CLI(object):
    def __init__(self):
        self.config = Config()

    def run(self):
        if len(argv) == 1:
            self.print_usage()
            exit(1)

        command = argv[1]
        if command not in commands:
            print('Unknown command "{}"'.format(argv[1]))
            print()
            self.print_usage()
            exit(1)

        try:
            command_args = argv[2:]
            eval('self.'+command)(command_args)
        except CommandException as ce:
            print(ce)
            exit(1)
        except ConfigException as cfe:
            print(cfe)
            exit(1)
        except DiaryException as de:
            print(de)
            exit(1)

    def print_usage(self):
        print(f'Usage: {progname} <command> <command-args>')
        print('  where <command> is one of:')
        for cmd in commands:
            print(f'    {cmd}')
        print()

    def log(self, args=[]):
        if args == []:
            raise CommandException(
                f'"{progname} log" must be followed by diary entry text'
                )

        text = ' '.join(args)
        diary = self.config.get_current_diary()
        diary.add_entry(text)
        print(f'Logged to {diary.name} diary')

    def rm(self, args=[]):
        if args == []:
            raise CommandException(
                f'"{progname} rm" must be followed by a diary entry ID'
            )

        diary = self.config.get_current_diary()
        for entry_id_str in args:
            try:
                diary.remove_entry(int(entry_id_str))
                print(f'Removed entry {entry_id_str}')
            except ValueError:
                raise CommandException(
                    f'"{progname} rm" must be followed by a diary entry' +
                    'ID not text'
                )

    def ls(self, args=[]):
        curr_diary = self.config.get_current_diary()
        entries = curr_diary.get_entries()
        if entries == -1:
            raise DiaryException(("Failed to connect to the server"))
        for ent in entries:
            print(f'[{ent.date_str()} (#{ent.id}) by {ent.username}]')
            print(ent.text)
            print()

    def switch(self, args=[]):
        is_remote_create = False
        error_http = 'http://'
        url = ''
        username = ''
        diarykey = ''
        diary = None
        printKey = False
        for arg in args:
            if arg.startswith('--remote='):
                is_remote_create = True
                url = arg[len('--remote='):]
                if not url.startswith(error_http) and url != '':
                    url = error_http + url
            elif arg.startswith('--user='):
                is_remote_create = True
                username = arg[len('--user='):]
        if args == []:
            raise CommandException(
                f'"{progname} switch" must be followed by a diary name'
            )

        if is_remote_create and len(args) < 3:
            raise CommandException(
                f'"{progname} switch" must be followed by a diary name'
            )

        elif is_remote_create and (url == '' or username == ''):
            raise CommandException(
                    "Cannot have blank url or username for remote diary"
            )

        if is_remote_create:
            diaryname = args[2]
            if not self.config.has_diary(name=diaryname):
                printKey = True
            diary = DiaryFactory.create_remote_diary(diaryname, self.config,
                                                     url, username)
            print(f'Switched to {diaryname} diary.')
            if printKey:
                diarykey = diary.get_diarykey()
                print(f'secret diary key: {diarykey}')

        else:

            diaryname = args[0]
            print(f'Switched to {diaryname} diary.')

        self.config.set_current_diary(name=diaryname)

    def key(self, args=[]):
        if args != []:
            raise CommandException(
                f'"{progname} key" does not take additional arguments'
                )
        key = ''
        diary = self.config.get_current_diary()
        if self.config.has_remote_file(diary=diary, f_name='key'):
            key = diary.get_diarykey()
            print(f'secret diary key: {key}')

    def diaries(self, args=[]):
        if args != []:
            raise CommandException(
                f'"{progname} diaries" does not take additional arguments'
                )

        diaries = self.config.get_diaries()
        curr_diary = self.config.get_current_diary()

        for local_diary in diaries[0]:
            local_diary_name = local_diary.name
            if local_diary.name == curr_diary.name:
                local_diary_name = '* ' + local_diary.name

            entries = local_diary.get_entries()
            if entries == []:
                print('{0:15} ({1} entries)'
                      .format(local_diary_name, len(entries)))
            else:
                start_str = entries[0].date_str()[:-6]
                end_str = entries[-1].date_str()[:-6]
                print('{0:15} ({1} entries, from {2} to {3})'
                      .format(local_diary_name,
                              len(entries),
                              start_str,
                              end_str))
        for remote_diary in diaries[1]:
            remote_diary_name = remote_diary.name
            if remote_diary.name == curr_diary.name:
                remote_diary_name = '* ' + remote_diary.name

            entries = remote_diary.get_entries()
            if entries == -1:
                print('{0:15} (*cannot connect to server*) (remote)'
                      .format(remote_diary_name))
            elif entries == []:
                print('{0:15} ({1} entries) (remote)'
                      .format(remote_diary_name, len(entries)))
            else:
                start_str = entries[0].date_str()[:-6]
                end_str = entries[-1].date_str()[:-6]
                print('{0:15} ({1} entries, from {2} to {3}) (remote)'
                      .format(remote_diary_name,
                              len(entries),
                              start_str,
                              end_str))

    def wipe(self, args=[]):
        if args == []:
            raise CommandException(
                f'"{progname} wipe" must be followed by a diary name'
                )
        elif len(args) > 1:
            raise CommandException(
                f'"{progname} wipe" takes only one diary name'
                )
        diaryname = args[0]
        self.config.delete_diary(name=args[0])
        print(f'Wiped {diaryname}')

    def connect(self, args=[]):
        if len(args) < 3:
            raise CommandException(
                f'"{progname} connect" must include the url of the \n'
                f'server, the username, and the diary_key \n'
                f'The command should look like: blurg \n'
                f'connect --remote=HOST --user=USERNAME --key=KEY'

            )
        if len(args) > 3:
            raise CommandException(
                f'"{progname} connect" recieved too many arguments'
            )
        error_http = 'http://'
        is_remote_create = False
        url = ''
        username = ''
        key = ''
        for arg in args:
            if arg.startswith('--remote='):
                is_remote_create = True
                url = arg[len('--remote='):]
                if not url.startswith(error_http) and url != '':
                    url = error_http + url
            elif arg.startswith('--user='):
                is_remote_create = True
                username = arg[len('--user='):]
            elif arg.startswith('--key='):
                is_remote_create = True
                key = arg[len('--key='):]

        if is_remote_create and (url == '' or username == ''):
            raise CommandException(
                    "Cannot have blank url or username for remote diary"
            )

        if is_remote_create:
            try:
                result = requests.get(
                    '{}/api/verify'.format(url),
                    auth=HTTPBasicAuth(key, ''),
                    data={})
            except ConnectionError:
                raise DiaryException("Failed to connect to the server")
            r = result.json()
            if(r["result"] != 'ok'):
                raise CommandException("diarykey is invalid")
            diaryname = r["diaryname"]
            DiaryFactory.create_local_remote_diary(
                diaryname,
                key,
                username,
                self.config,
                url)
            self.config.set_current_diary(name=diaryname)
            print(f'Switched to {diaryname} diary.')
            return
        raise CommandException("An invalid command was entered")

    def promote(self, args=[]):
        if len(args) < 3:
            raise CommandException(
                f'"{progname} promote" must include the diary name, \n'
                f'the url to the server you want to connect too, and \n'
                f'the username. \n'
                f'The command should look like: blurg \n'
                f'promote LOCALDIARY --remote=HOST --user=USERNAME '

            )
        if len(args) > 3:
            raise CommandException(
                f'"{progname} promote" recieved too many arguments'
            )
        error_http = 'http://'
        if args[0] == "":
            raise CommandException(
                    "Cannot have a blank diary name"
            )
        if args[0] == 'default' or args[0] == 'config':
            raise CommandException(
                    "Cannot promote default or config"
            )
        diaryname = args[0]
        url = ''
        username = ''
        for arg in args:
            if arg.startswith('--remote='):
                url = arg[len('--remote='):]
                if not url.startswith(error_http) and url != '':
                    url = error_http + url
                elif url == error_http:
                    raise CommandException(
                        "That is not a full url,"
                    )
            elif arg.startswith('--user='):
                username = arg[len('--user='):]

        if url == '' or username == '':
            raise CommandException(
                    "Cannot have blank url or username for remote diary"
            )

        new_key = self.config.promote_diary(diaryname, url, username)
        print(f'Promoted {diaryname} to a remote diary.')
        print(f'secret diary key: {new_key}')

    def demote(self, args=[]):
        if args == []:
            raise CommandException(
                f'"{progname} demote" must be followed by a diary name'
                )
        elif len(args) > 1:
            raise CommandException(
                f'"{progname} demote" takes only one diary name'
                )
        diary_name = args[0]
        self.config.demote_diary(diary_name)
        print('Demotion was a success.')
