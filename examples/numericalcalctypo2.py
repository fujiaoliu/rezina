#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rezina.utils.network import get_ip
from rezina import TypologyBuilder
from mysql import Mysql

from numericalcalc import get_item, add_one, multiplied_by_two, discard_some_item

ip = get_ip()
tb = TypologyBuilder(ip, 12345, 'numcalc_typo2')
tb.add_hydrant(get_item, args=(50,))
tb.add_notch(add_one, 10, 5)
tb.add_notch(multiplied_by_two, 5, 10)
tb.add_notch(discard_some_item, 2, 2)
tb.add_bocca(Mysql, kwargs={'host': 'localhost',
                            'port': 3306,
                            'user': 'root',
                            'passwd': '123456',
                            'charset': 'utf8',
                            'db': 'test',
                            'table': 'numcalc'})

if __name__ == "__main__":
    tb.restart(interval=10)
