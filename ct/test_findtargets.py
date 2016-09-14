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
        uth.reset()

    def test_samples(self):
        relativeexpectedexes = {
            'simple/helloworld_c.c',
            'simple/helloworld_cpp.cpp',
            'dottypaths/dottypaths.cpp',
            'lotsofmagic/lotsofmagic.cpp',
            'magicsourceinheader/main.cpp'}
        relativeexpectedtests = {
            'cross_platform/test_source.cpp',
            'factory/test_factory.cpp',
            'numbers/test_direct_include.cpp',
            'numbers/test_library.cpp',
            'simple/test_cflags.c'}

        expectedexes = { os.path.realpath(os.path.join(uth.samplesdir(),exe)) for exe in relativeexpectedexes }
        expectedtests = { os.path.realpath(os.path.join(uth.samplesdir(),tt)) for tt in relativeexpectedtests }
        config_files = ct.configutils.config_files_from_variant(exedir=uth.cakedir())
        cap = configargparse.getArgumentParser(
            description='TestFindTargetsModule',
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            default_config_files=config_files,
            args_for_setting_config_path=["-c","--config"],
            ignore_unknown_config_file_keys=True)
        ct.findtargets.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv=['--shorten'])
        findtargets = ct.findtargets.FindTargets(args,exedir=uth.cakedir())
        executabletargets, testtargets = findtargets(path=uth.cakedir())
        self.assertSetEqual(expectedexes, set(executabletargets))
        self.assertSetEqual(expectedtests, set(testtargets))

    def tearDown(self):
        uth.reset()
