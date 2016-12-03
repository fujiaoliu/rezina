#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------

from __future__ import print_function

import sys

color_map = {'gray': '\033[90m',
             'red': '\033[91m',
             'green': '\033[92m',
             'yellow': '\033[93m',
             'blue': '\033[94m',
             'violet': '\033[95m',
             'beige': '\033[96m',
             'white': '\033[97m',
             'end': '\033[0m',
             'bold': '\033[1m'}


def color(s, txt_color='red', bold=False):
    if not sys.stdout.isatty():
        return s
    color_s = color_map[txt_color.lower()] + s + color_map['end']
    if bold:
        color_s = color_map['bold'] + color_s
    return color_s


def colorful_print(mess, txt_color='red', bold=False, **kwargs):
    print(color(mess, txt_color, bold), **kwargs)


if __name__ == "__main__":
    for c in color_map.keys():
        colorful_print('test', c, False, end=' ')
        colorful_print('test', c, True)
