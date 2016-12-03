#!/usr/bin/env python

from rezina import TypologyBuilder
from rezina.backends import Null

from rezina.tests.workerspace import computenum

tb = TypologyBuilder('127.0.0.1', 12345, 'typo_null')
tb.add_hydrant(computenum.get_nums, args=(10,))
tb.add_notch(computenum.cacl_pow, 2, 2)
tb.add_notch(computenum.add_one, 2, 2)
tb.add_bocca(Null, persistent_mode="stream")

if __name__ == "__main__":
    tb.restart(interval=5)
