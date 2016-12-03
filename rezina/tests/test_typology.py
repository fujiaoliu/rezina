#!/usr/bin/env python


import unittest
import subprocess
import time
import os
import signal
import shutil

from . import Master, Worker, Typology


class TestTypology(unittest.TestCase):

    def setUp(self):
        self.output_dir = None
        self.master = Master()
        self.worker = Worker()
        if self.master.is_alive():
            self.master.stop()
        time.sleep(5)
        self.master.start()
        if self.worker.is_alive():
            self.worker.stop()
        time.sleep(5)
        self.worker.start()

    def tearDown(self):
        self.worker.stop()
        time.sleep(3)
        self.master.create_client()
        self.master.stop()
        time.sleep(3)
        self.master.clear()
        if self.output_dir:
            shutil.rmtree(self.output_dir)

    def test_tb(self):
        typo = Typology('tb.py', 'typo_file')
        try:
            os.mkdir(typo.output_dir)
        except:
            pass
        self.output_dir = typo.output_dir
        assert typo.run() is True
        time.sleep(18)
        typo.create_client()
        time.sleep(5)
        typos = typo.get_typo()
        time.sleep(3)
        assert typo.typo_name in typos
        assert 'running' == typos[typo.typo_name]
        procs = typo.get_typo_from_worker()
        assert len(procs) == 9
        time.sleep(20)
        typo.kill_typo()
        time.sleep(20)
        assert typo.get_typo() == {}
        proc = typo.get_typo_from_worker()
        assert len(proc) == 0
        output_file = '%s/%s' % (typo.output_dir, typo.typo_name)
        output = open(output_file).readlines()
        assert len(output) >= 30

    def test_tb1(self):
        typo = Typology('tb1.py', 'typo_null')
        assert typo.normal_run() == 0
        time.sleep(20)
        typo.create_client()
        time.sleep(3)
        typos = typo.get_typo()
        time.sleep(5)
        assert typo.typo_name in typos
        assert 'running' == typos[typo.typo_name]
        procs = typo.get_typo_from_worker()
        assert len(procs) == 9

        typo.stop()
        time.sleep(20)
        proc = typo.get_typo_from_worker()
        assert len(proc) == 0
        typos = typo.get_typo()
        assert typo.typo_name in typos
        assert 'stoped' == typos[typo.typo_name]

        typo.start()
        time.sleep(20)
        typos = typo.get_typo()
        time.sleep(3)
        assert typo.typo_name in typos
        assert 'running' == typos[typo.typo_name]
        procs = typo.get_typo_from_worker()
        assert len(procs) == 9

        typo.restart()
        time.sleep(20)
        typos = typo.get_typo()
        assert typo.typo_name in typos
        assert 'running' == typos[typo.typo_name]
        procs = typo.get_typo_from_worker()
        assert len(procs) == 9

        typo.remove()
        time.sleep(20)
        typos = typo.get_typo()
        assert typo.get_typo() == {}
        proc = typo.get_typo_from_worker()
        assert len(proc) == 0

    def test_tb1_failover(self):
        typo = Typology('tb1.py', 'typo_null')
        assert typo.normal_run() == 0
        time.sleep(20)
        typo.create_client()
        time.sleep(5)
        typos = typo.get_typo()
        assert typo.typo_name in typos
        assert 'running' == typos[typo.typo_name]
        procs = typo.get_typo_from_worker()
        assert len(procs) == 9

        comp_pid = broker_pid = None
        for p in reversed(procs):
            typo_name, comp_name, idx = p.split('::')
            pid = typo_name.split('#')[0]
            if comp_name == 'Broker':
                broker_pid = int(pid)
            else:
                comp_pid = int(pid)
            if comp_pid and broker_pid:
                break
        os.kill(comp_pid, signal.SIGTERM)
        time.sleep(20)
        typos = typo.get_typo()
        assert typo.typo_name in typos
        assert 'running' == typos[typo.typo_name]
        procs = typo.get_typo_from_worker()
        assert len(procs) == 9

        os.kill(broker_pid, signal.SIGTERM)
        time.sleep(20)
        assert typo.typo_name in typos
        assert 'running' == typos[typo.typo_name]
        procs = typo.get_typo_from_worker()
        assert len(procs) == 9

        typo.remove()
        time.sleep(20)
        typos = typo.get_typo()
        assert typo.get_typo() == {}
        proc = typo.get_typo_from_worker()
        assert len(proc) == 0
