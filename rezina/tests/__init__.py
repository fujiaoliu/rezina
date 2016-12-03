#!/usr/bin/env python


import subprocess
import time
import os
import shutil
import signal
import sys
import multiprocessing

from rezina.service.database import DBClient
from rezina.service.manager import ProcessManager
from rezina.utils.timeout import timeout
from rezina.utils.model import Model

from rezina.tests.workerspace.tb import run

cwd = os.path.abspath(os.path.dirname(__file__))
log_dir = '%s/log' % (cwd)
workerspace_dir = '%s/workerspace' % (cwd)
output_dir = '%s/output' % (cwd)


class Master(object):
    def __init__(self):
        self.dbc = DBClient('tcp://127.0.0.1:12345')
        if self.is_alive():
            self.create_client()
            self.stop()
        self.clear()

    def clear(self):
        if os.path.exists(log_dir):
            shutil.rmtree(log_dir)
        db_dir = os.path.join(os.path.expanduser('~'), '.rezina', '.db')
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir)

    def create_client(self):
        self.pm = ProcessManager(self.dbc.get())
        self.model = Model(self.dbc, self.pm)

    def start(self):
        cmd = 'rezina-cli runmaster -H 127.0.0.1 -P 12345 -R -D -L %s -W %s' % (log_dir, workerspace_dir)
        print(cmd)
        return subprocess.call(cmd, shell=True)

    def get_names(self):
        time.sleep(0.5)
        data = self.model.get_master_status()['master']
        return [m['name'] for m in data]

    def get_service_pid(self):
        time.sleep(0.5)
        data = self.model.get_master_status()['master']
        return [int(m['pid']) for m in data]

    def stop(self):
        self.pm.kill_master()
        time.sleep(2)
        return get_pids('runmaster')

    def is_alive(self):
        with timeout(2):
            data = self.dbc.get()
            return data is not None

    def get_master_pid(self):
        return list(set(get_pids('runmaster')) - set(self.get_service_pid()))


class Worker(object):

    def __init__(self):
        self.dbc = DBClient('tcp://127.0.0.1:12345')
        self.hasclient = False

    def start(self):
        cmd = 'rezina-cli runworker -H 127.0.0.1 -P 12345 -D -WIP 127.0.0.1'
        return subprocess.call(cmd, shell=True)

    def is_known_by_master(self):
        data = self.dbc.get_worker_status()['status'].keys()
        return '127.0.0.1' in data

    def is_alive(self):
        return len(get_pids('runworker')) > 0

    def stop(self):
        self.pm = ProcessManager(self.dbc.get())
        self.pm.kill_workers()


class Typology(object):
    def __init__(self, f_name, typo_name):
        self.f_name = f_name
        self.workerspace_dir = workerspace_dir
        self.typo_name = typo_name
        self.output_dir = output_dir
        self.t_file = '%s/%s' % (self.workerspace_dir, self.f_name)

    def create_client(self):
        self.dbc = DBClient('tcp://127.0.0.1:12345')
        self.pm = ProcessManager(self.dbc.get())
        self.model = Model(self.dbc, self.pm)

    def run(self):
        self.p = multiprocessing.Process(target=run)
        self.p.start()
        return self.p.is_alive()

    def normal_run(self):
        return subprocess.call([sys.executable, self.t_file])

    def get_typo(self):
        typos = self.model.get_typology_status()
        return {t['name']: t['status'] for t in typos}

    def get_typo_from_worker(self):
        return self.dbc.get_worker_status()['status']['127.0.0.1']['processes']

    def start(self):
        self.pm.start(self.typo_name)

    def stop(self):
        self.pm.stop(self.typo_name)

    def restart(self):
        self.pm.restart(self.typo_name)

    def remove(self):
        self.pm.remove(self.typo_name)

    def kill_typo(self):
        self.p.terminate()


def get_pids(name):
    cmd = "ps aux | grep %s | grep -v grep| awk {'print $2'}" % (name,)
    pids = subprocess.check_output(cmd, shell=True).strip().split()
    return [int(pid) for pid in pids]
