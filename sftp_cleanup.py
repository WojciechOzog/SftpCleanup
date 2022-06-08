#!/usr/bin/python3.8

# script to remove files and dirs from sftp servers older than $max_file_age param
# it remove recursively with sub dirs

# docs https://docs.paramiko.org/en/stable/api/sftp.html

import paramiko
import time
import os
from stat import S_ISDIR
import sys
import argparse
import os.path


class SftpCleanup():
    # path log file
    log_file = '/root/sftp_cleanup.log'
    # contains list of directories from sftp to cleanup (one line one dir name)
    # it`s not full path, only dir name on sftp server from root dir "/"
    list_path = '/root/sftp_cleanup_dirs'

    # max_file_age in days (older will be removed)
    max_file_age = 30

    def __init__(self):
        self.menu()

        if not os.path.exists(self.list_path):
            print('You should create file "{0}" with root direcory names to check'.format(list_path))
            sys.exit(1)

        if self.args.key:
            private_key = paramiko.RSAKey.from_private_key_file(self.args.key)

        current_time = int(time.time())
        file_age = int(self.max_file_age) * 86400
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=self.args.host, username=self.args.user, pkey=private_key)

        self.sftp = ssh.open_sftp()
        self.top_dirs = self.sftp.listdir('.')

        if self.args.check:
            print('I check root directory on sftp from "{0}"'.format(self.list_path))
            for dirname in self.get_list_path(self.list_path):
                print(dirname)
                self.log_msg(dirname)
            print('----------------')

        for dirname in self.top_dirs:
            if dirname in self.get_list_path(self.list_path):
                for backup in sorted(self.sftp.listdir_attr(dirname), key=lambda f: f.st_mtime):
                    if backup.filename == '.ssh':
                        continue
                    if current_time - backup.st_mtime > file_age:
                        if self.args.check:
                            print(dirname + "/" + backup.filename)
                        elif self.args.delete:
                            path = "/" + dirname + "/" + backup.filename
                            self.get_recursive(path)
        self.sftp.close()
        ssh.close()

    def menu(self):
        parser = argparse.ArgumentParser(description='script to cleanup logs from sftp server')
        parser.add_argument('--host', help='sftp hostname', type=str, required=True)
        parser.add_argument('--user', help='sftp user', type=str, required=True)
        parser.add_argument('--key', help='path to private key', type=str, required=True)
        parser.add_argument('--check', help='list path to delete', action="store_true")
        parser.add_argument('--delete', help='delete from check list with sub-dictionaries', action="store_true")
        self.args = parser.parse_args()

    def rm(self, path):
        try:
            if S_ISDIR(self.sftp.stat(path).st_mode) is True:
                self.sftp.rmdir(path)
                msg = "directory removed: {0}".format(path)
                print(msg)
                self.log_msg(msg)
            else:
                self.sftp.remove(path)
                msg = "file removed: {0}".format(path)
                print(msg)
                self.log_msg(msg)
        except:
            pass

    def get_recursive(self, path):
        removed = []
        deep = []
        deep.insert(0, path)
        for i in range(1, 10):
            try:
                for l1 in self.sftp.listdir(path):
                    if S_ISDIR(self.sftp.stat(path).st_mode) is True:
                        path = path + "/" + l1 + "/"
                        deep.insert(i, path)
            except:
                pass

        for directory in deep:
            try:
                for f in self.sftp.listdir(directory):
                    if f not in removed:
                        removed.append(f)
                        self.rm(directory + f)
            except:
                pass

        for directory in reversed(deep):
            self.rm(directory)

        removed.clear()
        deep.clear()

    def log_msg(self, log):
        with open(self.log_file, 'a+') as f:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write("{0} - {1}\n".format(current_time, log))

    def get_list_path(self, list_path):
        dir_name = []
        with open(self.list_path, 'r') as f:
            list_servers = (f.readlines())

        for name in list_servers:
            name = name.replace('\n', '')
            dir_name.append(name)

        return dir_name

clenup = SftpCleanup()
