#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rezina.utils.network import get_ip
from rezina import TypologyBuilder
from mysql import Mysql

import cityweather

ip = get_ip()
tb = TypologyBuilder(ip, 12345, 'weather_typo1')
tb.add_hydrant(cityweather.get_cities)
tb.add_notch(cityweather.get_city_weather, 1, 10)
tb.add_notch(cityweather.one_word_conditions_for_city, 1, 1)
tb.add_bocca(Mysql, kwargs={'host': 'localhost',
                            'port': 3306,
                            'user': 'root',
                            'passwd': '123456',
                            'charset': 'utf8',
                            'db': 'test',
                            'table': 'weather'})

if __name__ == "__main__":
    tb.restart(interval=10)
