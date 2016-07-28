from __future__ import print_function
from __future__ import unicode_literals

import os
import unittest
import configargparse

import ct.unittesthelper as uth
import ct.findtargets


class TestFindTargetsModule(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def test_samples(self):
        expectedexes = [
            './samples/simple/helloworld_c.c',
            './samples/simple/helloworld_cpp.cpp',
            './samples/dottypaths/dottypaths.cpp']
        expectedtests = [
            './samples/cross_platform/test_source.cpp',
            './samples/factory/test_factory.cpp',
            './samples/numbers/test_direct_include.cpp',
            './samples/numbers/test_library.cpp',
            './samples/simple/test_cflags.c']

        argv = ['ct-test', '-c', 'ct.conf.d/ct.conf']
        cap = configargparse.getArgumentParser()
        cap.add(
            "-c",
            "--config",
            is_config_file=True,
            help="Manually specify the config file path if you want to override the variant default")
        ct.findtargets.add_arguments(cap)
        args = ct.utils.parseargs(cap, argv)
        print(args.exemarkers)
        findtargets = ct.findtargets.FindTargets(args)
        executabletargets, testtargets = findtargets()
        self.assertListEqual(expectedexes, executabletargets)
        self.assertListEqual(expectedtests, testtargets)

    def tearDown(self):
        uth.delete_existing_parsers()
