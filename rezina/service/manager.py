#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------
# Desc:
# History:
# Author:
# ----------------------------------------------


import time
import os
import pickle

import zmq
from zmq.utils import strtypes

from rezina.service.database import DBClient
from rezina.service.log import Logging
from rezina.typology.typology import Typology


__all__ = ['ProcessManager', 'MasterPMClient', 'WorkerPMClient']


MASTER_CMD_TOPIC = b'MASTER_CMD'
WORKER_CMD_TOPIC = b'WORKER_CMD'


class ProcessManager(object):
    '''manage process'''

    def __init__(self, devices_addr):
        self._devices_addr = devices_addr
        self.logger = Logging(self._devices_addr['log_server'],
                              ip='Console').get_logger()
        self.dbclient = DBClient(self._devices_addr['db_server'])
        self._workspace_dir = None

    def _set_workerspace_dir(self):
        self._workspace_dir = self.dbclient.get_startup_setting()['workspace']

    def _create_manager_sock(self):
        try:
            cxt = zmq.Context()
        except:
            self.logger.exception('ZMQ Error')
        else:
            try:
                sock = cxt.socket(zmq.PUB)
            except:
                self.logger.exception('ZMQ Error')
            else:
                sock.connect(self._devices_addr['fwd_frtd'])
                time.sleep(0.1)
                return sock

    def _send_cmd(self, *args):
        try:
            sock = self._create_manager_sock()
            sock.send_multipart([args[0], pickle.dumps(args[1:])])
        except:
            self.logger.exception('ZMQ Error')
        finally:
            sock.close()
            sock.context.destroy()

    def stop(self, name):
        self.dbclient.set_meta(name, False)
        self._send_cmd(WORKER_CMD_TOPIC, '_kill_process_by_name', name)

    def kill_workers(self):
        self._send_cmd(WORKER_CMD_TOPIC, '_kill_workers')

    def kill_selected_worker(self, ip):
        self._send_cmd(WORKER_CMD_TOPIC, '_kill_selected_worker', ip)

    def kill_master(self):
        self._send_cmd(MASTER_CMD_TOPIC, '_kill_master')

    def get_workload(self):
        data = self.dbclient.get_worker_status()['status']
        return dict([(k, v['workload']) for k, v in data.items()])

    def start(self, name):
        self.dbclient.set_meta(name)
        component_args = self.dbclient.get(name)
        self.sync_files()
        workload = self.get_workload()
        if component_args[0] == "Broker":
            return 'Broker cant not be adjust'

        if component_args[0] == 'Typology':
            components = Typology(self._devices_addr, workload,
                                  *component_args[1]).run()
        else:
            worker_ip = min([[v, k] for k, v in workload.items()])[1]
            components = [[strtypes.b(worker_ip),
                           pickle.dumps(component_args)]]
        try:
            sock = self._create_manager_sock()
            for c in components:
                sock.send_multipart(c)
        except:
            self.logger.exception('ZMQ Error')
        finally:
            sock.close()
            sock.context.destroy()

    def launch_more(self, name, value, writeback=True):
        component_args = self.dbclient.get(name)
        if component_args[0] in ('Broker', 'Typology'):
            self.logger.warning('launch failed, %s can not be Typology\
             or Bocca type' % (name))
            return

        if writeback and component_args[0] in ('Notch', 'Bocca'):
            typo_name, comp_type, idx = name.split('::')
            typo_args = self.dbclient.get(typo_name)
            if comp_type == 'Notch':
                typo_args[1][2][int(idx)][1] += value
            else:
                typo_args[1][3][3] += value
            self.commit_typology(typo_args)

        if component_args[0] == 'Notch':
            load = component_args[1][-1]
        else:
            load = 1

        workload = self.get_workload()
        try:
            sock = self._create_manager_sock()
            for _ in range(value):
                worker_ip = min([[v, k] for k, v in workload.items()])[1]
                c = [strtypes.b(worker_ip), pickle.dumps(component_args)]
                sock.send_multipart(c)
                workload[worker_ip] += load
                time.sleep(0.1)
        except:
            self.logger.exception('ZMQ Error')
        finally:
            sock.close()
            sock.context.destroy()

    def commit_typology(self, typo_args):
        if self.dbclient.set(typo_args[1][0], typo_args, True) != '_Error_':
            self.logger.info('%s commit settings done' % (typo_args[0],))
        else:
            self.logger.error('%s commit settings Faild' % (typo_args[0],))

    def restart(self, name):
        self.stop(name)
        time.sleep(0.5)
        self.start(name)

    def remove(self, name):
        self.stop(name)
        time.sleep(0.5)
        self.dbclient.remove(name)
        self.dbclient.del_meta(name)

    def sync_files(self):
        if self._workspace_dir is None:
            self._set_workerspace_dir()
        exclude_dirs = ['.git', '.hg', '.svn']
        try:
            sock = self._create_manager_sock()

            for root, dirs, files in os.walk(self._workspace_dir):
                # modify the dirnames list in-place
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                try:
                    root = root.split(self._workspace_dir, 1)[1]
                except IndexError:
                    root = ''
                for f_name in files:
                    if os.path.splitext(f_name)[1] in ('.pyc', '.pyo'):
                        continue
                    # this implementsion is not for big file
                    f_path = os.path.join(self._workspace_dir, root, f_name)
                    with open(f_path, 'r') as f:
                        sock.send_multipart([WORKER_CMD_TOPIC,
                                             pickle.dumps(('_sync_file', root,
                                                           f_name, f.read()))])
        except ImportError:
            self.logger.exception('SYNC Error')
        except:
            self.logger.exception('ZMQ Error')
        finally:
            sock.close()
            sock.context.destroy()
            self.logger.info('sync file done')


class Client(object):

    def __init__(self, devices_addr, process_container, logger):
        self._devices_addr = devices_addr
        self._process_container = process_container
        self.logger = logger
        self._topic = b""

    @property
    def cls_name(self):
        return self.__class__.__name__

    def run(self):
        try:
            cxt = zmq.Context()
        except:
            self.logger.exception('ZMQ Error')
        else:
            try:
                sock = cxt.socket(zmq.SUB)
            except:
                self.logger.exception('ZMQ Error')
            else:
                try:
                    sock.connect(self._devices_addr['fwd_bckd'])
                    time.sleep(0.1)
                    try:
                        sock.setsockopt(zmq.SUBSCRIBE, self._topic)
                    except TypeError:
                        sock.setsockopt_string(zmq.SUBSCRIBE, self._topic)
                    time.sleep(0.1)
                    self.logger.info('%s sock connected' % (self.cls_name))
                except:
                    self.logger.exception('ZMQ Connect Error')
                else:
                    try:
                        while True:
                            data = sock.recv_multipart()
                            data = pickle.loads(data[1])
                            try:
                                getattr(self, data[0])(*data[1:])
                            except:
                                self.logger.exception('%s Error'
                                                      % (self.cls_name))
                    except:
                        self.logger.exception('ZMQ Recv Error')
                finally:
                    sock.close()
            finally:
                cxt.destroy()


class WorkerPMClient(Client):

    def __init__(self, devices_addr, lock,
                 worker_process_container, worker_ip, logger):
        super(WorkerPMClient, self).__init__(devices_addr,
                                             worker_process_container, logger)
        self._lock = lock
        self.worker_ip = worker_ip
        self._topic = WORKER_CMD_TOPIC

    def _kill_process_by_name(self, name):
        delimiter = '::'
        self._lock.acquire()
        try:
            self.logger.info('in kill process')
            processes = [p for p in self._process_container if p.name == name]
            if not processes:
                processes = [p for p in self._process_container
                             if p.name.split(delimiter)[0] == name]
            self.logger.info('kill list' + str(processes))

            for p in processes:
                self._process_container.remove(p)
                p.terminate()
                p.join(timeout=0.1)
            self.logger.info('remian' + str(self._process_container))
        finally:
            self._lock.release()

    def _sync_file(self, root, f_name, f_content):
        path = os.path.join(os.path.expanduser('~'), '.rezina', root)
        try:
            os.makedirs(path)
        except OSError:
            pass

        with open(os.path.join(path, f_name), 'w') as f:
            f.write(f_content)

    def _kill_workers(self):
        self._lock.acquire()
        try:
            [p.terminate() for p in self._process_container]
            [p.join(timeout=0.1) for p in self._process_container]
        finally:
            os._exit(0)

    def _kill_selected_worker(self, ip):
        if ip == self.worker_ip:
            self.logger.info('Kill Worker %s' % (ip))
            self._kill_workers()


class MasterPMClient(Client):

    def __init__(self, devices_addr, master_process_container, logger):
        super(MasterPMClient, self).__init__(devices_addr,
                                             master_process_container, logger)
        self._topic = MASTER_CMD_TOPIC
        self.dbclient = DBClient(self._devices_addr['db_server'])
        self._check_interval = 10  # master processes check interval in seconds

    def _kill_master(self):
        [p.terminate() for p in self._process_container]
        [p.join(timeout=0.1) for p in self._process_container]
        os._exit(0)

    def manage_master(self):
        while True:
            self.dbclient.set_master_status({
                'master_processes': [str(p.pid)+'#'+p.name
                                     for p in self._process_container],
                'alive': [p.name for p in self._process_container
                          if p.is_alive()],
                'timestamp': time.time()})
            time.sleep(self._check_interval)
