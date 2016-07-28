from __future__ import print_function
from __future__ import unicode_literals

import os
import unittest
import configargparse

import ct.unittesthelper as uth
import ct.utils
import ct.findtargets


class TestFindTargetsModule(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def test_samples(self):
        expectedexes = {
            './samples/simple/helloworld_c.c',
            './samples/simple/helloworld_cpp.cpp',
            './samples/dottypaths/dottypaths.cpp'}
        expectedtests = {
            './samples/cross_platform/test_source.cpp',
            './samples/factory/test_factory.cpp',
            './samples/numbers/test_direct_include.cpp',
            './samples/numbers/test_library.cpp',
            './samples/simple/test_cflags.c'}

        config_files = ct.utils.config_files_from_variant(exedir=".")
        cap = configargparse.getArgumentParser(
            description='Find the source files that are executable targets and tests',
            formatter_class=configargparse.DefaultsRawFormatter,
            default_config_files=config_files,
            ignore_unknown_config_file_keys=True)
        cap.add(
            "-c",
            "--config",
            is_config_file=True,
            help="Manually specify the config file path if you want to override the variant default")
        ct.findtargets.add_arguments(cap)
        args = ct.utils.parseargs(cap, argv=['-vvv'])
        findtargets = ct.findtargets.FindTargets(args)
        executabletargets, testtargets = findtargets()
        self.assertSetEqual(expectedexes, set(executabletargets))
        self.assertSetEqual(expectedtests, set(testtargets))

    def tearDown(self):
        uth.delete_existing_parsers()
