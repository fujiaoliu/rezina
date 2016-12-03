#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------

import pickle

from zmq.utils import strtypes

from rezina.service.database import DBClient
from rezina.utils.network import generate_tcp_sock


__all__ = ['Typology']


class Typology(object):
    ''''''

    delimiter = '::'

    def __init__(self, devices_addr, workload,
                 typology_name, hydrants, notchs, bocca,
                 start_time=None, interval=None):

        self.typology_name = typology_name
        self._workload = workload
        self.hydrants = hydrants
        self.notchs = notchs
        self.bocca = bocca
        self._devices_addr = devices_addr
        self.start_time = start_time
        self.interval = interval
        self.rgasc = DBClient(self._devices_addr['db_server'])

    def _get_the_most_idle_worker(self):
        return min([[v, k] for k, v in self._workload.items()])[1]

    def _generate_brokers(self):
        ''''''
        self.broker_num = len(self.notchs) + 1
        self.addr_pairs = []
        for _ in range(self.broker_num):
            worker_ip = self._get_the_most_idle_worker()
            self.addr_pairs.append((generate_tcp_sock(worker_ip),
                                    generate_tcp_sock(worker_ip)))
            self._workload[worker_ip] += 1

    def _construct(self):
        ''''''
        components = []
        # construct brokers
        for n, pairs in enumerate(self.addr_pairs):
            components.append(('Broker', pairs,
                               self.delimiter.join([self.typology_name,
                                                    'Broker', str(n)])))

        # construct hydrant args
        for n, hydrant in enumerate(self.hydrants):
            components.append(('Hydrant', (self.addr_pairs[0][0],
                                           self._devices_addr, hydrant[0],
                                           hydrant[1], hydrant[2],
                                           self.start_time, self.interval),
                               self.delimiter.join([self.typology_name,
                                                    'Hydrant', str(n)])))

        for n, notch in enumerate(self.notchs):
            for _ in range(int(notch[1])):  # duplicate process_num
                components.append(('Notch', (self.addr_pairs[n][1],
                                             self.addr_pairs[n+1][0],
                                             self._devices_addr, notch[0],
                                             notch[2]),
                                   self.delimiter.join([self.typology_name,
                                                        'Notch', str(n)])))

        for n in range(int(self.bocca[3])):
            components.append(('Bocca', (self.addr_pairs[-1][1],
                                         self._devices_addr, self.bocca[0],
                                         self.bocca[1], self.bocca[2],
                                         self.bocca[4]),
                               self.delimiter.join([self.typology_name,
                                                    'Bocca', str(n)])))

        # save addr for manager reuse
        # TODO
        # args include devices addr
        for c in components:
            self.rgasc.set(c[2], c)

        return components

    def distribut_components_with_load_balance(self, components):
        ''''''
        component_with_worker_ip = []
        for c in components:
            if c[0] == 'Broker':
                worker_ip = c[1][0].split(':')[1].strip('//')
            else:
                worker_ip = self._get_the_most_idle_worker()
                # compute new workload
                if c[0] == 'Notch':
                    self._workload[worker_ip] += c[1][-1]
                else:
                    self._workload[worker_ip] += 1
            component_with_worker_ip.append([strtypes.b(worker_ip),
                                             pickle.dumps(c)])
        return component_with_worker_ip

    def run(self):
        ''''''
        try:
            self._generate_brokers()
            return self.distribut_components_with_load_balance(
                self._construct())
        except:
            return []
