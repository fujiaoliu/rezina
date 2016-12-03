#!/usr/bin/env python


import unittest
import subprocess
import time

from . import Master, Worker


class TestWorker(unittest.TestCase):

    def setUp(self):
        self.master = Master()
        self.worker = Worker()

    def tearDown(self):
        self.master.clear()

    def test_start_without_master(self):
        assert self.worker.start() != 0

    def test_worker_with_master(self):
        assert 0 == self.master.start()
        time.sleep(3)
        self.master.create_client()
        assert self.worker.start() == 0
        time.sleep(3)
        assert self.worker.is_known_by_master() is True
        assert self.worker.is_alive() is True
        # start failed when worker is already running
        assert self.worker.start() != 0
        self.worker.stop()
        time.sleep(8)
        assert self.worker.is_alive() is False
        self.master.stop()
        time.sleep(5)
        assert self.master.is_alive() is False
