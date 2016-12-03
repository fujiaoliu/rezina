#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------

import time
import os
import signal

from rezina.service.log import Logging
from rezina.service.database import DBClient
from rezina.service.manager import ProcessManager
from rezina.utils.udfutil import UDFUtil
from rezina.utils.timeout import timeout
from rezina.utils.colorterminal import colorful_print
from rezina.backends.resultwriteback import BoccaWriteBack, ResultReciver
from rezina.utils.network import generate_tcp_sock
from rezina.utils.timeout import timeout


__all__ = ['TypologyBuilder']


class TypologyBuilder(object):

    def __init__(self, host, port, name):
        self.host = host
        self.port = port
        # TODO get caller's filename as typo name
        self.name = name
        self.hydrants = []
        self.notchs = []
        self.boccas = None
        self._init_with_check()
        self.is_writeback = False
        self.udfutil = UDFUtil()

    def _init_with_check(self):
        with timeout(3):
            self.dbclient = DBClient('tcp://'+self.host+':'+str(self.port))
            devices_addr = self.dbclient.get()
            if devices_addr is None:
                colorful_print('Connection Timeout, Check the IP and PORT \
                            of Master. [Error]', 'red', True)
                exit(-1)
        self.pm = ProcessManager(devices_addr)
        self.logger = Logging(devices_addr['log_server'],
                              ip=self.host).get_logger()

    def add_hydrant(self, target, args=(), kwargs={}):
        self.hydrants.append([self.udfutil.get_obj_imp_tup(target),
                              args, kwargs])
        return self

    def add_notch(self, target, process_num=1, thread_num=1):
        self.notchs.append([self.udfutil.get_obj_imp_tup(target),
                            process_num, thread_num])
        return self

    def add_bocca(self, target, args=(), kwargs={}, process_num=1,
                  persistent_mode='batch'):
        if target.__name__ in ('Stdout', 'PlainFile'):
            reciver_tcpaddr = generate_tcp_sock(self.host)
            self.result_reciver = ResultReciver(reciver_tcpaddr, target,
                                                args, kwargs)
            target = BoccaWriteBack
            args = (reciver_tcpaddr,)
            kwargs = {}
            self.is_writeback = True
        self.boccas = [self.udfutil.get_obj_imp_tup(target), args, kwargs,
                       process_num, persistent_mode]
        return self

    def check_components(self):
        if '::' in self.name:
            colorful_print('Sorry, Typology name could not contain "::"',
                           'red')
            exit()
        if not self.hydrants or not self.boccas:
            colorful_print('Hydrant and Bocca must be set', 'red')
            exit()

    def start(self, start_time=None, interval=None):
        self.check_components()
        typo_args = ('Typology', (self.name, self.hydrants,
                                  self.notchs, self.boccas,
                                  start_time, interval))
        self.pm.commit_typology(typo_args)
        self.pm.start(self.name)
        if self.is_writeback:
            try:
                signal.signal(signal.SIGTERM, cleanup_handler)
                self.result_reciver.run()
            except:
                self.result_reciver.close()
            finally:
                colorful_print('Waiting %s to stop...' % (self.name), 'yellow')
                with timeout(2, handler=timeout_handler):
                    self.stop()
                    colorful_print('%s Stoped. [OK]' % (self.name), 'green')
                exit(0)
                # os._exit(0)

    def restart(self, start_time=None, interval=None):
        self.pm.remove(self.name)
        time.sleep(0.5)
        self.start(start_time, interval)

    def stop(self):
        self.pm.remove(self.name)


def timeout_handler(signum, frame):
    colorful_print("[Error] Stop Failed.", 'red')
    colorful_print('Connection timeout, pls check if master is alive.', 'red')
    os._exit(-1)


def cleanup_handler(signum, frame):
    colorful_print("recv kill signal...", 'red')
    exit()
