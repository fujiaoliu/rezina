#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------


import socket

import zmq


def generate_tcp_sock(ip=None, port=None, min_port=12345,
                      max_port=54321, retry=20):
    ip = ip or get_ip()
    port = port or get_port(min_port, max_port, retry)
    tcp_addr = 'tcp://%s:%d' % (ip, port)
    return tcp_addr


# TODO cross platform not test
def get_ip():
    try:
        return socket.gethostbyname(socket.getfqdn())
    except:
        return '127.0.0.1'


def get_port(min_port, max_port, retry):
    cxt = zmq.Context()
    socket = cxt.socket(zmq.PULL)
    port = socket.bind_to_random_port('tcp://*', min_port=min_port,
                                      max_port=max_port, max_tries=retry)
    socket.close()
    cxt.destroy()
    return port
