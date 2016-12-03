#!/usr/bin/evn python


'''
This module implements a base class for Bocca, if you want to implement your
own backend, just inherit the base class and implement open, write and close
methods.
'''


class StorageBackend(object):

    def __init__(self, logger, *args, **kwargs):
        self.logger = logger
        self.args = args
        self.kwargs = kwargs

    def open(self):
        raise NotImplementedError

    def write(self, message):
        raise NotImplementedError

    def close(self):
        pass
