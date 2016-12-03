#!/usr/bin/env python

import os

from rezina import TypologyBuilder
from rezina.backends import PlainFile

from rezina.tests.workerspace import computenum


cwd = os.path.abspath(os.path.dirname(__file__))
output_dir = '%s/output' % (os.path.dirname(cwd))


def run():
    tb = TypologyBuilder('127.0.0.1', 12345, 'typo_file')
    tb.add_hydrant(computenum.get_nums, args=(10,))
    tb.add_notch(computenum.cacl_pow, 2, 2)
    tb.add_notch(computenum.add_one, 2, 2)
    tb.add_bocca(PlainFile, args=('%s/typo_file' % (output_dir), "w"),
                 persistent_mode="stream")
    tb.restart(interval=5)
