#!/usr/bin/env python


import unittest
import socket

from rezina.utils.network import get_port, get_ip


class TestNetwork(unittest.TestCase):

    def test_get_ip(self):
        ip = get_ip()
        is_valid = True
        try:
            socket.inet_aton(ip)
        except socket.error:
            is_valid = False
        self.assertTrue(is_valid)

    def test_get_port(self):
        result = get_port(12345, 54321, 20)
        assert type(result) == int
        assert result > 12345
        assert result < 54321


if __name__ == "__main__":
    unittest.main()
