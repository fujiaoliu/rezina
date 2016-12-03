#!/usr/bin/env python


import unittest
import os
import signal
import time


from . import Master


class TestMaster(unittest.TestCase):

    def setUp(self):
        self.tm = Master()

    def tearDown(self):
        self.tm.clear()

    def test_double_start(self):
        assert 0 == self.tm.start()
        time.sleep(5)
        assert 0 != self.tm.start()
        self.tm.create_client()
        time.sleep(5)
        self.tm.stop()
        time.sleep(5)
        assert self.tm.is_alive() is False

    def test_master_info(self):
        assert 0 == self.tm.start()
        time.sleep(10)
        self.tm.create_client()
        names = self.tm.get_names()
        time.sleep(3)
        expect = ['WebServer', 'DBService', 'MoniterService', 'LogService', 'CommandForworder']
        assert set(expect) == set(names)
        assert self.tm.stop() == []
        time.sleep(5)
        assert self.tm.is_alive() is False

    def test_kill_service_by_hand(self):
        assert 0 == self.tm.start()
        time.sleep(5)
        self.tm.create_client()
        time.sleep(3)
        pids = self.tm.get_service_pid()
        time.sleep(5)
        os.kill(pids[0], signal.SIGTERM)
        time.sleep(3)
        assert self.tm.is_alive() is False

    def test_kill_master_by_hand(self):
        assert 0 == self.tm.start()
        time.sleep(5)
        self.tm.create_client()
        time.sleep(3)
        pids = self.tm.get_master_pid()
        os.kill(pids[0], signal.SIGTERM)
        time.sleep(3)
        assert self.tm.is_alive() is False
