#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------


import multiprocessing
import threading
import os
import os.path
import time
import signal

from rezina.service.log import LogServer
from rezina.service.database import DBServer
from rezina.utils.network import generate_tcp_sock
from rezina.typology.broker import Forwarder
from rezina.service.monitor import MonitorServer
from rezina.service.manager import MasterPMClient
from rezina.web.httpserver import init_webserver


def init_master_service(ip, port, log_dir, daemon, refresh, http_port,
                        workspace):

    service_processes = []
    names = ['log_server', 'fwd_frtd', 'fwd_bckd', 'monitor_server']
    devices_addr = {name: generate_tcp_sock(ip) for name in names}
    devices_addr.update({'db_server': generate_tcp_sock(ip, port=port)})
    devices_addr.update({'web_server': ip + ':' + str(http_port)})

    try:
        dbs = DBServer(devices_addr, refresh)
        log_dir = os.path.join(os.path.abspath(log_dir), '')
        workspace = os.path.join(os.path.abspath(workspace), '')
        dbs.save_startup_setting({'ip': ip,
                                  'port': port,
                                  'log_dir': log_dir,
                                  'daemon': daemon,
                                  'refresh': refresh,
                                  'http_port': http_port,
                                  'workspace': workspace})

        devices_addr, logger = dbs.get_devices_addr_and_logger()
        cmd_forwarder = Forwarder(logger, devices_addr['fwd_frtd'],
                                  devices_addr['fwd_bckd'])
        if not daemon:
            log_dir = None
        logserver = LogServer(devices_addr['log_server'], log_dir=log_dir)
        ms = MonitorServer(logger, devices_addr)

        masters = [(logserver, 'LogService'),
                   (dbs, 'DBService'),
                   (cmd_forwarder, 'CommandForworder'),
                   (ms, 'MoniterService')]
        for service, name in masters:
            p = multiprocessing.Process(target=service.run, name=name)
            service_processes.append(p)
            p.start()

        httpd = multiprocessing.Process(target=init_webserver,
                                        args=(ip, int(http_port),
                                              devices_addr, logger),
                                        name='WebServer')
        service_processes.append(httpd)
        httpd.start()

        master_pm = MasterPMClient(devices_addr, service_processes, logger)
        threading.Thread(target=master_pm.run).start()
        threading.Thread(target=master_pm.manage_master).start()

        # use this to kill all sub processes when it is killed by hand
        signal.signal(signal.SIGTERM, signal_term_handler)
        while True:
            for p in service_processes:
                if not p.is_alive():
                    exit()
            time.sleep(2)
    except:
        [p.terminate() for p in service_processes]
        [p.join(timeout=0.1) for p in service_processes]
        os._exit(-1)


def signal_term_handler(signal, frame):
    exit()
