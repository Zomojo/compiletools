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

    @unittest.skip("REMOVE THIS SKIP.  JUST WHILE REFACTORING")
    def test_samples(self):
        expectedexes = {
            './samples/simple/helloworld_c.c',
            './samples/simple/helloworld_cpp.cpp',
            './samples/dottypaths/dottypaths.cpp',
            './samples/lotsofmagic/lotsofmagic.cpp'}
        expectedtests = {
            './samples/cross_platform/test_source.cpp',
            './samples/factory/test_factory.cpp',
            './samples/numbers/test_direct_include.cpp',
            './samples/numbers/test_library.cpp',
            './samples/simple/test_cflags.c'}

        config_files = ct.configutils.config_files_from_variant(exedir=uth.cakedir())
        print("Using config_files=")
        print(config_files)
        cap = configargparse.getArgumentParser(
            description='TestFindTargetsModule',
            formatter_class=configargparse.DefaultsRawFormatter,
            default_config_files=config_files,
            args_for_setting_config_path=["-c","--config"],
            ignore_unknown_config_file_keys=True)
        ct.findtargets.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv=['--shorten'])
        findtargets = ct.findtargets.FindTargets(args)
        executabletargets, testtargets = findtargets(path=uth.cakedir())
        self.assertSetEqual(expectedexes, set(executabletargets))
        self.assertSetEqual(expectedtests, set(testtargets))

    def tearDown(self):
        uth.delete_existing_parsers()
