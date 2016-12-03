#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------


from __future__ import print_function

import logging
import logging.handlers
import traceback
import time
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import os
import hashlib

import zmq

from rezina.utils.network import get_ip


__all__ = ['Logging', 'LogServer']


class Formatter(object):
    ''''''

    def __init__(self, fmt=None, datefmt=None, ip=None):
        ''''''
        self._fmt = fmt or "[%(ip)s->%(processName)s#%(process)d] - [%(asctime)s] - %(levelname)s - %(message)s"
        self.datefmt = datefmt or "%Y-%m-%d %H:%M:%S"
        self._ip = ip

    def fmt_asctime(self, record):
        ct = time.localtime(record.created)
        t = time.strftime(self.datefmt, ct)
        return t

    def get_ip(self):
        return self._ip or get_ip()

    @property
    def asctime_in_fmt(self):
        return self._fmt.find("%(asctime)") >= 0

    @property
    def ip_in_fmt(self):
        return self._fmt.find("%(ip)") >= 0

    def fmt_exception(self, exc_info):
        ''''''
        sio = StringIO()
        traceback.print_exception(exc_info[0], exc_info[1],
                                  exc_info[2], None, sio)
        s = sio.getvalue()
        sio.close()
        return s

    def format(self, record):
        record.message = record.getMessage()
        if self.asctime_in_fmt:
            record.asctime = self.fmt_asctime(record)
        if self.ip_in_fmt:
            record.ip = self.get_ip()
        s = self._fmt % record.__dict__
        if record.exc_info and not record.exc_text:
            record.exc_text = self.fmt_exception(record.exc_info)

        if record.exc_text:
            if s[-1] != "\n":
                s += "\n"
            try:
                s += record.exc_text
            except UnicodeError:
                s += record.exc_text.decode(sys.getfilesystemencoding(),
                                            'replace')
        return s


class Handler(logging.Handler):

    def __init__(self, log_server_addr, ip):
        logging.Handler.__init__(self)
        self.log_server_addr = log_server_addr
        self.sock = None
        self._defaultFormatter = Formatter(ip=ip)

    def format(self, record):
        fmt = self.formatter or self._defaultFormatter
        return fmt.format(record)

    def make_socket(self):
        cxt = zmq.Context()
        sock = cxt.socket(zmq.PUB)
        sock.connect(self.log_server_addr)
        sock.setsockopt(zmq.LINGER, 0)
        time.sleep(0.1)
        return sock

    def create_socket(self):
        for n in range(5):
            try:
                self.sock = self.make_socket()
                break
            except zmq.ZMQError:
                time.sleep(n + 1)

    def handleError(self, record):
        if self.sock is not None:
            self.sock.close()
            self.sock.context.destroy()
            self.sock = None
        else:
            logging.Handler.handleError(self, record)

    def emit(self, record):
        try:
            self.create_socket()
            self.sock.send_pyobj(self.format(record))
            self.sock.close()
            self.sock.context.destroy()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def close(self):
        self.acquire()
        try:
            if self.sock:
                self.sock.close()
                self.sock.context.destroy()
        finally:
            self.release()
        logging.Handler.close(self)


class Logging(object):
    ''''''

    def __init__(self, log_server_addr, handler=None, ip=None):
        self.log_server_addr = log_server_addr
        self.handler = handler or self._construct_sock_handler(ip)
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            self.logger.addHandler(self.handler)

    def _construct_sock_handler(self, ip):
        return Handler(self.log_server_addr, ip)

    def get_logger(self):
        return self.logger


class LogServer(object):
    ''''''

    def __init__(self, log_server_addr, log_dir=None):
        self.log_server_addr = log_server_addr
        self.log_dir = log_dir

    def _log_to_stdout(self):
        while True:
            message = self.sock.recv_pyobj()
            print(message)

    def _get_logger(self, name):
        logger = logging.getLogger(name)
        fh = logging.handlers.TimedRotatingFileHandler(os.path.join(
            self.log_dir, name + '.log'), when='midnight')
        formatter = logging.Formatter('%(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
        return logger

    def _log_to_file(self):
        rezina_name = hashlib.sha1('rezina'.encode('utf-8')).hexdigest()
        try:
            os.makedirs(self.log_dir)
        except OSError:
            pass

        logger_map = {rezina_name: self._get_logger(rezina_name)}

        while True:
            message = self.sock.recv_pyobj()
            name = message.split('->', 1)[-1].split('#', 1)[0]
            if '::' in name:
                name = name.split('::')[0].strip()
            else:
                name = rezina_name

            if name not in logger_map:
                logger_map[name] = self._get_logger(name)
            logger_map[name].info(message)

    def run(self):
        cxt = zmq.Context()
        self.sock = cxt.socket(zmq.SUB)
        self.sock.bind(self.log_server_addr)
        self.sock.setsockopt(zmq.SUBSCRIBE, b"")
        time.sleep(0.1)
        try:
            if self.log_dir:
                self._log_to_file()
            else:
                self._log_to_stdout()
        finally:
            self.sock.close()
            cxt.destroy()
