#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------


import sys
import os


def daemonize():
    os.umask(0)

    try:
        pid = os.fork()
    except OSError:
        sys.exit(0)
    if pid > 0:
        sys.exit(0)
    os.setsid()

    try:
        pid = os.fork()
    except OSError:
        sys.exit(0)
    if pid > 0:
        os._exit(0)

    os.chdir('/')

    import resource     # Resource usage information.
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = 1024

    # Iterate through and close all file descriptors.
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:   # ERROR, fd wasn't open to begin with (ignored)
            pass

    fd = os.open(os.devnull, os.O_RDWR)
    os.dup2(fd, sys.stdin.fileno())
    os.dup2(fd, sys.stdout.fileno())
    os.dup2(fd, sys.stderr.fileno())
