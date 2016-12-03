#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------


import signal
from contextlib import contextmanager


class TimeoutError(Exception):
    pass


def default_handler(signum, frame):
    raise TimeoutError('Connection Timeout.')


@contextmanager
def timeout(sec, handler=default_handler):
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(sec)
    yield
    signal.alarm(0)
