#!/usr/bin/env python
# -*- coding: utf-8 -*-


import multiprocessing

from rezina.service.worker import Worker


def init_worker(devices_addr, worker_ip):
    proc = multiprocessing.current_process()
    proc.name = 'Worker'
    worker = Worker(devices_addr, worker_ip)
    worker.run()
