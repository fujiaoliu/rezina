#!/usr/bin/env python

import unittest
import os
import sys

from rezina.utils.udfutil import UDFUtil
from rezina.tests.workerspace import udf


cwd = os.path.abspath(os.path.dirname(__file__))
workerspace_dir = '%s/workerspace' % (cwd)
sys.path.insert(0, cwd)


class TestAddrServer(unittest.TestCase):

    def setUp(self):
        self.impt = UDFUtil()

    def test_import_udf_func(self):
        foo = self.impt.import_udf(*self.impt.get_obj_imp_tup(udf.my_pow))
        self.assertEqual(9, foo(3))

    def test_import_udf_method(self):
        bar = self.impt.import_udf(*self.impt.get_obj_imp_tup(
             udf.UserClass().bar))
        self.assertEqual(27, bar(3))

    def test_udf_tree(self):
        result = self.impt.get_udfs_tree('udf')
        self.assertIn('my_pow', result['functions'])
        self.assertIn('UserClass', result['classes'])
        self.assertIn('foo', result['classes']['UserClass'])

    def test_list_all_modules(self):
        result = self.impt.list_all_modules('workerspace')
        self.assertIn('workerspace.tb', result)
        self.assertIn('workerspace.udf', result)
        self.assertIn('workerspace.computenum', result)

    def tearDown(self):
        del self.impt

if __name__ == "__main__":
    unittest.main()
