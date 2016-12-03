#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------


import threading
import time
import os
import math
from collections import deque

import zmq

from rezina.utils.udfutil import UDFUtil

__all__ = ['Hydrant', 'Notch', 'Bocca']


class Hydrant(object):

    def __init__(self, logger, downstream_tcp_addr, devices_addr,
                 handler, hdl_args, hdl_kwargs,
                 start_time=None, interval=None):
        self.downstream_tcp_addr = downstream_tcp_addr
        self._devices_addr = devices_addr
        self.logger = logger
        self.interval = interval

        try:
            if start_time is None:
                if interval is None:
                    self.start_time = time.time()
                else:
                    self.start_time = math.ceil(time.time() / self.interval) * self.interval
            else:
                self.start_time = time.mktime(time.strptime(
                    start_time, '%Y-%m-%d %H:%M:%S'))
                last_start_time = (math.ceil(time.time() / self.interval) - 1) * self.interval
                # prevent rerun old job when restart
                if self.interval and self.start_time < last_start_time:
                    self.start_time = last_start_time
        except ValueError:
            self.logger.exception('Time or Interval Format Error')
            # os._exit(-1)
            exit(-1)

        self.handler = UDFUtil().import_udf(*handler)
        self.hdl_args = hdl_args
        self.hdl_kwargs = hdl_kwargs

    def run(self):
        try:
            cxt = zmq.Context()
        except:
            self.logger.exception('ZMQ Error')
        else:
            try:
                sock = cxt.socket(zmq.PUSH)
            except:
                self.logger.exception('ZMQ Error')
            else:
                try:
                    sock.connect(self.downstream_tcp_addr)
                    time.sleep(0.1)
                except:
                    self.logger.exception('Connection Error')
                else:
                    while True:
                        if time.time() > self.start_time:
                            try:
                                for item in self.handler(*self.hdl_args,
                                                         **self.hdl_kwargs):
                                    sock.send_pyobj(item)
                            except zmq.ZMQError:
                                self.logger.exception('Send Error')
                                break
                            except:
                                self.logger.exception('UDF Error -> %s, %s'
                                                      % (str(self.hdl_args),
                                                         str(self.hdl_kwargs)))
                            # TODO flow control by adjusting interval
                            try:
                                self.start_time += abs(self.interval)
                            except TypeError:
                                self.logger.info('hydrant run once finished!')
                                break
                        time.sleep(0.2)
                finally:
                    sock.close()
            finally:
                cxt.destroy()
                # os._exit(-1)
                exit(-1)


class Notch(object):

    def __init__(self, logger, upstream_tcp_addr, downstream_tcp_addr,
                 devices_addr, handler, thread_num):
        self.upstream_tcp_addr = upstream_tcp_addr
        self.downstream_tcp_addr = downstream_tcp_addr
        self._devices_addr = devices_addr
        self.handler = UDFUtil().import_udf(*handler)
        self.thread_num = thread_num
        self.logger = logger

    def _thread_handler(self):
        ''''''
        try:
            consumer_socket = self.cxt.socket(zmq.PULL)
            producer_socket = self.cxt.socket(zmq.PUSH)
        except:
            self.logger.exception('ZMQ Error')
        else:
            try:
                consumer_socket.connect(self.upstream_tcp_addr)
                producer_socket.connect(self.downstream_tcp_addr)
                time.sleep(0.2)
            except:
                self.logger.exception('ZMQ Error')
            else:
                try:
                    while True:
                        args = consumer_socket.recv_pyobj()
                        try:
                            output = self.handler(args)
                            if output is None:
                                continue
                        except:
                            self.logger.exception('Notch UDF Error -> args(%s)'
                                                  % (str(args)))
                        else:
                            producer_socket.send_pyobj(output)
                except:
                    self.logger.exception('Send or Recv Error')
            finally:
                consumer_socket.close()
                producer_socket.close()
        finally:
            if not self.cxt.closed:
                self.cxt.destroy()
            os._exit(-1)

    def run(self):
        ''''''
        try:
            self.cxt = zmq.Context()
        except:
            self.logger.exception('ZMQ Error')
            # os._exit(-1)
            exit(-1)
        threads = []
        for _ in range(self.thread_num):
            t = threading.Thread(target=self._thread_handler)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()


class Bocca(object):

    def __init__(self, logger, upstream_tcp_addr, devices_addr,
                 backends, args, kwargs, persistent_mode):
        self.upstream_tcp_addr = upstream_tcp_addr
        self._devices_addr = devices_addr
        self.logger = logger
        try:
            self.backend_instance = UDFUtil().get_bocca_instance(self.logger,
                                                                 backends[0],
                                                                 backends[1],
                                                                 args, kwargs)
        except:
            self.logger.exception('Backend Error')
            # os._exit(-1)
            exit(-1)
        self.persistent_mode = persistent_mode
        self.persistent_mode_map = {'stream': self._stream_persistence,
                                    'batch': self._batch_persistence}

    def _stream_persistence(self):
        while True:
            data = self.bocca_sock.recv_pyobj()
            try:
                self.backend_instance.write(data)
            except:
                self.logger.exception('Backend Write Method Error')

    def run(self):
        try:
            cxt = zmq.Context()
        except:
            self.logger.exception('ZMQ Error')
        else:
            try:
                self.bocca_sock = cxt.socket(zmq.PULL)
            except:
                self.logger.exception('ZMQ Error')
            else:
                try:
                    self.bocca_sock.connect(self.upstream_tcp_addr)
                    time.sleep(0.1)
                except:
                    self.logger.exception('ZMQ Error')
                else:
                    try:
                        self.backend_instance.open()
                    except NotImplementedError:
                        self.logger.exception('Backend Open Method Error')
                    else:
                        try:
                            self.persistent_mode_map[self.persistent_mode]()
                        except:
                            self.logger.exception('ZMQ Error')
                        finally:
                            try:
                                self.backend_instance.close()
                            except:
                                self.logger.exception('Backend Close Method Error')
                finally:
                    self.bocca_sock.close()
            finally:
                cxt.destroy()
                # os._exit(-1)
                exit(-1)

    def _batch_persistence(self):
        poller = zmq.Poller()
        poller.register(self.bocca_sock, zmq.POLLIN)
        data_buffer = []
        poller_state = 'Wait'
        while True:
            socks = dict(poller.poll(200))
            if self.bocca_sock in socks:
                data = self.bocca_sock.recv_pyobj()
                data_buffer.append(data)
                if poller_state == 'Wait':
                    poller_state = 'Ready'
            else:
                if poller_state == 'Ready':
                    poller_state = 'Insert'
            if poller_state == 'Insert':
                try:
                    self.backend_instance.write(data_buffer)
                except:
                    self.logger.exception('Backend Write Method Error')
                data_buffer = []
                poller_state = 'Wait'
