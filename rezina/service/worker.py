#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------


import threading
import time
import multiprocessing
import pickle

import zmq

from rezina.service.log import Logging
from rezina.service.manager import WorkerPMClient, ProcessManager
from rezina.service.monitor import MonitorClient
from rezina.typology.broker import Broker
from rezina.typology.components import Hydrant, Notch, Bocca


__all__ = ['Worker']


class Worker(object):
    ''''''

    def __init__(self, devices_addr, worker_ip):
        ''''''
        self._devices_addr = devices_addr
        self._worker_ip = worker_ip
        self._mapping = {'Hydrant': Hydrant, 'Notch': Notch,
                         'Bocca': Bocca, 'Broker': Broker}
        self._worker_process = []
        self._lock = threading.Lock()
        self.logger = Logging(self._devices_addr['log_server'],
                              ip=worker_ip).get_logger()
        self.pm = ProcessManager(devices_addr)

        self._thread_num_of_componet = {}

    def _run_pm_client(self):
        pmc = WorkerPMClient(self._devices_addr, self._lock,
                             self._worker_process, self._worker_ip,
                             self.logger)
        pmc.run()

    def _run_monitor_client(self):
        mc = MonitorClient(self._devices_addr['monitor_server'],
                           self._worker_process, self._thread_num_of_componet,
                           self._lock, self._worker_ip, self.logger)
        mc.run()

    # TODO
    # reinfine
    def _executor(self):
        ''''''
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
                        sock.setsockopt(zmq.SUBSCRIBE, self._worker_ip)
                    except TypeError:
                        sock.setsockopt_string(zmq.SUBSCRIBE, self._worker_ip)
                    time.sleep(0.1)
                except:
                    self.logger.exception('ZMQ Connect Error')
                else:
                    try:
                        while True:
                            data = sock.recv_multipart()
                            c = pickle.loads(data[1])
                            try:
                                p = multiprocessing.Process(
                                    target=self._mapping[c[0]](self.logger,
                                                               *c[1]).run,
                                    name=c[2])
                            except SystemExit:
                                self.logger.info('Typology %s UDF Error,\
                                    Killed!' % (c[2].split('::', -1)[0]))
                                self.pm.remove(c[2].split('::', -1)[0])
                            except:
                                self.logger.exception('UDF Error')
                            else:
                                # get thread num for computing workload
                                if c[0] == 'Notch':
                                    thread_num = c[1][-1]
                                else:
                                    thread_num = 1
                                self._lock.acquire()
                                self._thread_num_of_componet[c[2]] = thread_num
                                self._worker_process.append(p)
                                self._lock.release()
                                p.start()
                    except KeyboardInterrupt:
                        self.logger.info('worker control c')
                    except:
                        self.logger.exception('Worker Error')
                    finally:
                        [w.terminate() for w in self._worker_process]
                        [w.join(timeout=0.1) for w in self._worker_process]
                finally:
                    sock.close()
            finally:
                cxt.term()

    def run(self):
        ''''''
        # TODO
        # multiprocessing (manager or shared mem)
        t = threading.Thread(target=self._run_pm_client)
        t.daemon = True
        t.start()
        t1 = threading.Thread(target=self._run_monitor_client)
        t1.daemon = True
        t1.start()
        self._executor()
