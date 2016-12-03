#!/usr/bin/env python
# -*- coding: utf-8 -*-

from rezina.utils.network import get_ip
from rezina import TypologyBuilder
from rezina.backends import Stdout

from cityweather import get_cities, get_city_weather, one_word_conditions_for_city

ip = get_ip()
tb = TypologyBuilder(ip, 12345, 'weather_typo2')
tb.add_hydrant(get_cities).add_notch(get_city_weather, 1, 10)
tb.add_notch(one_word_conditions_for_city, 1, 1)
tb.add_bocca(Stdout, persistent_mode='stream')

if __name__ == "__main__":
    tb.restart(interval=10)
