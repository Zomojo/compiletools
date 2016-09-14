from __future__ import print_function
from __future__ import unicode_literals

import sys
import unittest
import configargparse

import ct.unittesthelper as uth
import ct.configutils
import ct.apptools


class TestVariant(unittest.TestCase):

    def setUp(self):
        uth.reset()

    def test_extract_variant(self):
        self.assertEqual(
            "abc",
            ct.configutils.extract_variant(
                "--variant=abc".split()))
        self.assertEqual(
            "abc",
            ct.configutils.extract_variant(
                "--variant abc".split()))
        self.assertEqual(
            "abc.123",
            ct.configutils.extract_variant(
                "-a -b -x --blah --variant=abc.123 -a -b -z --blah".split()))
        self.assertEqual(
            "abc.123",
            ct.configutils.extract_variant(
                "-a -b -x --blah --variant abc.123 -a -b -cz--blah".split()))

        # Note the -c overrides the --variant
        self.assertEqual(
            "blah",
            ct.configutils.extract_variant(
                "-a -b -c blah.conf --variant abc.123 -a -b -cz--blah".split()))

    def test_extract_variant_from_ct_conf(self):
        # Should find the one in the git repo ct.conf.d/ct.conf
        variant = ct.configutils.extract_item_from_ct_conf(
            key='variant',
            user_config_dir='/var',
            system_config_dir='/var',
            exedir=uth.cakedir())
        self.assertEqual("debug", variant)

    def test_extract_variant_from_blank_argv(self):
        # Force to find the git repo ct.conf.d/ct.conf
        variant = ct.configutils.extract_variant(
            user_config_dir='/var',
            system_config_dir='/var',
            exedir=uth.cakedir(),
            verbose=3)
        self.assertEqual("gcc.debug", variant)

    def tearDown(self):
        uth.reset()

if __name__ == '__main__':
    unittest.main()
