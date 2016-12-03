#!/usr/bin/env python
# -*- coding: utf-8 -*-


import time

import zmq


__all__ = ['Broker', 'Forwarder']


class Device(object):

    def __init__(self, logger, upstream_tcp_addr, downstream_tcp_addr):
        self.upstream_tcp_addr = upstream_tcp_addr
        self.downstream_tcp_addr = downstream_tcp_addr
        self.logger = logger
        self.upstream_type = None
        self.downstream_type = None

    @property
    def cls_name(self):
        return self.__class__.__name__

    def _run_device(self):
        raise NotImplementedError

    def _set_sock_opt(self):
        pass

    def run(self):
        try:
            cxt = zmq.Context()
        except:
            self.logger.exception('ZMQ Error')
        else:
            try:
                self.upstream = cxt.socket(self.upstream_type)
                self.downstream = cxt.socket(self.downstream_type)
            except:
                self.logger.exception('ZMQ Error')
            else:
                try:
                    self.upstream.bind(self.upstream_tcp_addr)
                    self.downstream.bind(self.downstream_tcp_addr)
                    time.sleep(0.2)
                    self._set_sock_opt()
                    self._run_device()
                except:
                    self.logger.exception("%s Bind Address Error or \
                                           Device Error" % (self.cls_name))
                finally:
                    self.upstream.close()
                    self.downstream.close()
            finally:
                cxt.destroy()


class Broker(Device):

    def __init__(self, *args):
        super(Broker, self).__init__(*args)
        self.upstream_type = zmq.PULL
        self.downstream_type = zmq.PUSH

    def _run_device(self):
        zmq.proxy(self.upstream, self.downstream)


class Forwarder(Device):

    def __init__(self, *args):
        super(Forwarder, self).__init__(*args)
        self.upstream_type = zmq.SUB
        self.downstream_type = zmq.PUB

    def _run_device(self):
        zmq.device(zmq.FORWARDER, self.upstream, self.downstream)

    def _set_sock_opt(self):
        self.upstream.setsockopt(zmq.SUBSCRIBE, b"")
