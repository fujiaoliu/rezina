#!/usr/bin/env python

from __future__ import print_function

from rezina.backends.base import StorageBackend


class Null(StorageBackend):

    def open(self):
        pass

    def write(self, message):
        print(message)
