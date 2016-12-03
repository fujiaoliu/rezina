#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
database is a python data structure store for maintaining configuration
information needed by rezina.
'''
# -----------------------------------------
# Desc:
# History:
# -----------------------------------------

import time
import hashlib
import os
import shelve
from collections import defaultdict

import zmq

from rezina.service.log import Logging


__all__ = ['DBServer', 'DBClient']


class DBServer(object):

    def __init__(self, devices_addr, refresh=False):

        self._devices_addr = devices_addr
        db_dir = os.path.join(os.path.expanduser('~'), '.rezina', '.db')
        db_name = 'db.s'
        self.db_path = os.path.join(db_dir, db_name)
        # Open existing database for reading and writing,
        # creating it if it doesn’t exist
        flag = 'c'
        if refresh:
            # Always create a new, empty database, open for reading and writing
            flag = 'n'
        try:
            os.makedirs(db_dir)
        except OSError:
            pass
        devices_key = hashlib.sha1('rezina'.encode('utf-8')).hexdigest()
        self._db = shelve.open(self.db_path, flag, writeback=True)
        if flag == 'c' and devices_key in self._db:
            self._devices_addr = self._db[devices_key]
        else:
            self._db[devices_key] = self._devices_addr
        # persistent master info immediately
        self._sync_db()

        meta_key = hashlib.sha1('meta'.encode('utf-8')).hexdigest()
        if meta_key not in self._db:
            self._db[meta_key] = {}

        db_ip = self._devices_addr['db_server'].split(':')[1].strip('//')
        self.logger = Logging(self._devices_addr['log_server'],
                              ip=db_ip).get_logger()

    def _sync_db(self):
        self._db.close()
        time.sleep(0.2)
        self._db = shelve.open(self.db_path, 'c', writeback=True)

    def get_devices_addr_and_logger(self):
        return self._devices_addr, self.logger

    def save_startup_setting(self, setting):
        key = hashlib.sha1('startup_setting'.encode('utf-8')).hexdigest()
        self._db[key] = setting

    def _operate_db(self):
        try:
            cxt = zmq.Context()
        except:
            self.logger.exception('ZMQ Error')
        else:
            try:
                sock = cxt.socket(zmq.REP)
            except:
                self.logger.exception('ZMQ Error')
            else:
                try:
                    sock.bind(self._devices_addr['db_server'])
                except:
                    self.logger.exception('DB Service Bind Error')
                else:
                    try:
                        while True:
                            cmd_type, method_name, args = sock.recv_pyobj()
                            try:
                                value = getattr(self, cmd_type)(method_name,
                                                                args)
                            except:
                                self.logger.exception('DB Server Error')
                                value = '_Error_'
                            sock.send_pyobj(value)
                    except:
                        self.logger.exception('ZMQ Send or Recv Error')
                finally:
                    sock.close()
            finally:
                cxt.destroy()
                self._db.close()

    def _set(self, save, args):
        self._db[args[0]] = args[1]
        if save:
            self._sync_db()

    def _get(self, method_name, args):
        return self._db[args[0]]

    def _update_by_key(self, method_name, args):
        if method_name == 'update':
            self._db[args[0]].update({args[1]: args[2]})
        if method_name == 'del':
            del self._db[args[0]][args[1]]
        self._sync_db()

    def _del(self, method_name, args):
        del self._db[args[0]]

    def _common(self, method_name, args):
        return list(getattr(self._db, method_name)(*args))

    def _rm(self, method_name, args):
        delimiter = '::'
        for key in self._db.keys():
            if key.split(delimiter)[0] == args[0]:
                del self._db[key]
        self._sync_db()

    def run(self):
        self._operate_db()


# TODO add error control when client connect to wrong addr
class DBClient(object):
    '''database client'''

    def __init__(self, db_server_addr):
        self._db_server_addr = db_server_addr
        self.sock = None

    def _create_sock(self):
        self.cxt = zmq.Context()
        self.sock = self.cxt.socket(zmq.REQ)
        self.sock.connect(self._db_server_addr)
        self.sock.setsockopt(zmq.LINGER, 0)
        time.sleep(0.1)

    def _send(self, cmd_type, method_name, *args):
        try:
            if self.sock is None:
                self._create_sock()
            self.sock.send_pyobj((cmd_type, method_name, args))
            return self.sock.recv_pyobj()
        except:
            if self.sock:
                self.sock.close()
                self.cxt.destroy()
                self.sock = None

    def keys(self):
        return self._send('_common', 'keys')

    def items(self):
        return self._send('_common', 'items')

    def values(self):
        return self._send('_common', 'values')

    def get(self, key=None):
        key = key or hashlib.sha1('rezina'.encode('utf-8')).hexdigest()
        return self._send('_get', None, key)

    def delete(self, key):
        return self._send('_del', None, key)

    def set(self, key, value, save=False):
        return self._send('_set', save, key, value)

    def remove(self, key):
        return self._send('_rm', None, key)

    # methods for specific operations
    def set_meta(self, meta_in_key, value=True):
        key = hashlib.sha1('meta'.encode('utf-8')).hexdigest()
        return self._send('_update_by_key', 'update', key, meta_in_key, value)

    def del_meta(self, key_in_meta):
        key = hashlib.sha1('meta'.encode('utf-8')).hexdigest()
        return self._send('_update_by_key', 'del', key, key_in_meta)

    def get_meta(self):
        key = hashlib.sha1('meta'.encode('utf-8')).hexdigest()
        return self.get(key)

    def set_master_status(self, value):
        key = hashlib.sha1('master_status'.encode('utf-8')).hexdigest()
        self.set(key, value)

    def set_worker_status(self, value):
        key = hashlib.sha1('worker_status'.encode('utf-8')).hexdigest()
        self.set(key, value)

    def get_master_status(self):
        key = hashlib.sha1('master_status'.encode('utf-8')).hexdigest()
        return self.get(key)

    def get_worker_status(self):
        key = hashlib.sha1('worker_status'.encode('utf-8')).hexdigest()
        return self.get(key)

    def get_startup_setting(self):
        key = hashlib.sha1('startup_setting'.encode('utf-8')).hexdigest()
        return self.get(key)

    def list_typos(self):
        filter_list = [hashlib.sha1(name.encode('utf-8')).hexdigest()
                       for name in ['rezina', 'worker_status', 'master_status',
                                    'startup_setting', 'meta']]
        typos = defaultdict(dict)
        for k, v in self.items():
            if k in filter_list:
                continue
            else:
                if v[0] == "Typology":
                    typos[k]["start_time"] = v[1][-2]
                    typos[k]["interval"] = v[1][-1]
                    for n, t in enumerate(v[1][1]):
                        udf = '.'.join([name for name in t[0] if name])
                        args = str(t[1])
                        kwargs = t[2]
                        typos[k]["::".join([k, "Hydrant",
                                            str(n)])] = {'udf': udf,
                                                         'args': args,
                                                         'kwargs': kwargs}
                    for n, t in enumerate(v[1][2]):
                        udf = '.'.join([name for name in t[0] if name])
                        prce_num = t[1]
                        thrd_num = t[2]
                        typos[k]["::".join([k, "Notch", str(n)])] = {
                            'udf': udf,
                            'thread_num': thrd_num,
                            'process_num': prce_num
                            }

                    t = v[1][3]
                    udf = '.'.join([name for name in t[0] if name])
                    args = str(t[1])
                    kwargs = t[2]
                    prce_num = t[3]
                    persit_mode = t[4]
                    typos[k]["::".join([k, "Bocca", '0'])] = {
                        'udf': udf,
                        'args': args,
                        'kwargs': kwargs,
                        'process_num': prce_num,
                        'persistent_mode': persit_mode
                        }
        return typos

    def list_typos_without_broker(self):
        filter_list = [hashlib.sha1(name.encode('utf-8')).hexdigest()
                       for name in ['rezina', 'worker_status', 'master_status',
                                    'startup_setting', 'meta']]
        return {k: v for k, v in self.items()
                if k not in filter_list and v[0] != "Broker"}

    @property
    def size(self):
        return len(self.keys())
