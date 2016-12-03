#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import time
import threading
import inspect


def get_item(num):
    return [{'item': x} for x in range(num)]


def add_one(item):
    time.sleep(0.2)
    item['addone'] = item['item'] + 1
    return item


def multiplied_by_two(item):
    time.sleep(0.8)
    item['multiplied'] = item['addone'] * 2
    return item


def discard_some_item(item):
    if item['multiplied'] % 10 != 0:
        return item


if __name__ == '__main__':
    for item in get_item(50):
        item1 = add_one(item)
        item2 = multiplied_by_two(item1)
        item3 = discard_some_item(item2)
        if item3:
            print(item3)
