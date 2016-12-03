#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------
# Desc:
# History:
# ----------------------------------------------


import time
import threading
import os
from collections import Counter

import zmq

from rezina.service.database import DBClient
from rezina.service.manager import ProcessManager


__all__ = ['MonitorClient', 'MonitorServer']


class MonitorClient(object):
    ''''''

    def __init__(self, monitor_server_addr,
                 worker_process_container, thread_num_map,
                 lock, worker_ip, logger):
        # heartbeat interval 4s, this means if a process is killed master will
        # get the change less than 4 seconds.
        self.interval = 4
        self.monitor_server_addr = monitor_server_addr
        self.worker_process_container = worker_process_container
        self.thread_num_map = thread_num_map
        self.lock = lock
        self.worker_ip = worker_ip
        self.logger = logger
        self.previous_process_status = []

    def run(self):
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
                try:
                    sock.hwm = 1
                    sock.connect(self.monitor_server_addr)
                    time.sleep(0.1)
                except:
                    self.logger.exception('ZMQ Connenction Error')
                else:
                    try:
                        while True:
                            self.lock.acquire()
                            try:
                                status = []
                                workload = 0
                                names = set()
                                killed_procs = []
                                for p in self.worker_process_container:
                                    if p.is_alive():
                                        status.append(str(p.pid) + '#'+ p.name)
                                        workload += self.thread_num_map[p.name]
                                        names.add(p.name)
                                    else:
                                        killed_procs.append(p)
                                for p in killed_procs:
                                    self.worker_process_container.remove(p)
                                for k in (set(self.thread_num_map) - names):
                                    del self.thread_num_map[k]
                            finally:
                                self.lock.release()
                                sock.send_pyobj({self.worker_ip: {
                                    "processes": status,
                                    "new_process": list(set(status) - set(
                                        self.previous_process_status)),
                                    "offline_process": [str(p.pid) + '#' + p.name
                                                        for p in killed_procs],
                                    "workload": workload}})
                            self.previous_process_status = status[:]
                            time.sleep(self.interval)
                    except:
                        self.logger.exception('ZMQ Send Error')
                finally:
                    sock.close()
            finally:
                cxt.destroy()


class MonitorServer(object):

    def __init__(self, logger, devices_addr):
        self._devices_addr = devices_addr
        self.monitor_server_addr = devices_addr['monitor_server']
        self.logger = logger
        self.dbclient = DBClient(self._devices_addr['db_server'])
        self.pm = ProcessManager(self._devices_addr)
        # loop check interval, in seconds. if a worker is disconnected, master
        # would know the event less than 9 seconds.
        self._check_interval = 9
        self._lock = threading.Lock()
        self._diff_lock = threading.Lock()
        self._status = {}
        self._worker_status = {'status': {}, 'new_workers': [],
                               'offline_workers': []}

    def diff(self):
        now = time.time()
        self._lock.acquire()
        try:
            new_workers = self._worker_status['new_workers']
            offline_workers = [k for k, v in self._status.items()
                               if (now-v['timestamp']) > self._check_interval]
            # keep offline process to check if it should be restart later
            offline_processes = []
            for k in offline_workers:
                # if worker disconnect, all processes running
                # before regards offline now
                offline_processes.extend(self._status[k]['processes'])
                del self._status[k]

            self._worker_status['status'] = dict(self._status)
            self._worker_status['offline_workers'] = offline_workers
            # get offline processes from connected workers
            for k, v in self._status.items():
                offline_processes.extend(v['offline_process'])
                # clear to prevent repeart start
                self._status[k]['offline_process'] = []
            self.dbclient.set_worker_status(self._worker_status)
            self._worker_status = {'status': {}, 'new_workers': [],
                                   'offline_workers': []}
        except:
            self.logger.exception('Monitor check-diff Error')
        finally:
            self._lock.release()

        # if processes are not stop by user, they would be restart to make sure
        # typo is continue running.
        if offline_processes:
            try:
                running_typo = [k for k, v in self.dbclient.get_meta().items()
                                if v]
                rerun_typo = set()
                rerun_comps = []
                offline_processes = Counter([proc.split('#')[1]
                                            for proc in offline_processes])
                for k, v in offline_processes.items():
                    typo_name, comp_name, idx = k.split('::')
                    if typo_name not in running_typo:
                        continue
                    if comp_name == 'Broker':
                        rerun_typo.add(typo_name)
                    else:
                        rerun_comps.append((k, v))

                rerun_comps = [k for k in rerun_comps
                               if k[0].split('::')[0] not in rerun_typo]
                if rerun_comps:
                    [self.pm.launch_more(*comp, writeback=False)
                     for comp in rerun_comps]
                    self.logger.warning('re-run components: %s'
                                        % (str(rerun_comps)))
                if rerun_typo:
                    [self.pm.restart(typo) for typo in rerun_typo]
                    self.logger.warning('re-run typo: %s'
                                        % (', '.join(rerun_typo)))
            except:
                self.logger.exception('Moniter re-run failed typology Error')

        if new_workers:
            new_workers.insert(0, 'New Workers:')
            self.logger.info(os.linesep.join(new_workers))

        if offline_workers:
            offline_workers.insert(0, 'Offline Workers:')
            self.logger.warning(os.linesep.join(offline_workers))

    def loop_check(self):
        while True:
            self._diff_lock.acquire()
            try:
                self.diff()
            finally:
                self._diff_lock.release()
            time.sleep(self._check_interval)

    def recv_heartbeat(self):
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
                    sock.bind(self.monitor_server_addr)
                    time.sleep(0.1)
                    sock.setsockopt(zmq.SUBSCRIBE, b"")
                    time.sleep(0.1)
                except:
                    self.logger.exception('ZMQ Error')
                else:

                    diff_flag = False
                    try:
                        while True:
                            data = sock.recv_pyobj()
                            ip = list(data.keys())[0]
                            data[ip]['timestamp'] = time.time()
                            self._lock.acquire()
                            try:
                                if ip not in self._status:
                                    diff_flag = True
                                    self._worker_status['new_workers'].append(ip)

                                if (data[ip]['new_process'] or
                                        data[ip]['offline_process']):
                                    diff_flag = True

                                self._status.update(data)
                            except:
                                self.logger.exception('Recive Heartbeat Error')
                            finally:
                                self._lock.release()

                            if diff_flag:
                                self._diff_lock.acquire()
                                try:
                                    self.diff()
                                finally:
                                    self._diff_lock.release()
                                diff_flag = False
                    except:
                        self.logger.exception('ZMQ Recv Error')
                finally:
                    sock.close()
            finally:
                cxt.destroy()

    def run(self):
        t = threading.Thread(target=self.loop_check)
        t.daemon = True
        t.start()
        self.recv_heartbeat()
