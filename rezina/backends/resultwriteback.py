#!/usr/bin/evn python

'''
rezina is a distributed process running framework, that means Bocca would be
running on any worker and send typology's output to backends from that server,
but when backend is Stdout or PlainFile, we would like to redirect the
typology's output to master. This module implemented this
feather for redirect the typology's output to the master's terminal or file.
'''


from __future__ import print_function
import time

import zmq

from rezina.backends.base import StorageBackend


class BoccaWriteBack(StorageBackend):

    def open(self):
        cxt = zmq.Context()
        self.sock = cxt.socket(zmq.PUSH)
        self.sock.connect(*self.args)
        time.sleep(0.1)

    def write(self, message):
        self.sock.send_pyobj(message)

    def close(self):
        self.sock.close()
        self.sock.context.destroy()


class ResultReciver(object):

    def __init__(self, tcp_addr, backend, args, kwargs):
        self.tcp_addr = tcp_addr
        self.backend_instance = backend(args, kwargs)
        self.backend_instance.open()

    def run(self):
        cxt = zmq.Context()
        self.sock = cxt.socket(zmq.PULL)
        self.sock.bind(self.tcp_addr)
        time.sleep(0.1)
        while True:
            self.backend_instance.write(self.sock.recv_pyobj())

    def close(self):
        self.backend_instance.close()
        self.sock.close()
        self.sock.context.destroy()


class Stdout(object):

    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def open(self):
        pass

    def write(self, message):
        print(message)

    def close(self):
        pass


class PlainFile(object):

    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def open(self):
        self.f = open(*self.args, **self.kwargs)

    def write(self, message):
        self.f.write(str(message)+'\n')
        self.f.flush()

    def close(self):
        self.f.close()
