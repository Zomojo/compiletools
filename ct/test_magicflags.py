from __future__ import print_function
from __future__ import unicode_literals

import os
import unittest
import configargparse

import ct.unittesthelper as uth
import ct.headerdeps
import ct.magicflags


class TestHeaderDepsModule(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def _createmagicparser(self, extraargs=None):
        if not extraargs:
            extraargs = []
        argv = extraargs
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        ct.magicflags.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        headerdeps = ct.headerdeps.create(args)
        return ct.magicflags.create(args, headerdeps)

    def test_parsing_CFLAGS(self):
        relativepath = 'simple/test_cflags.c'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser()
        #magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            magicparser.parse(realpath).get('CFLAGS'),
            {'-std=gnu99'})

    def test_SOURCE_direct(self):
        relativepath = 'cross_platform/cross_platform.cpp'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser()        
        #magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            magicparser.parse(realpath).get('SOURCE'),
            {'cross_platform_lin.cpp', 'cross_platform_win.cpp'})
        
    def test_SOURCE_cpp(self):
        relativepath = 'cross_platform/cross_platform.cpp'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(['--magic','cpp'])        
        #magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            magicparser.parse(realpath).get('SOURCE'),
            {'cross_platform_lin.cpp'})

    def test_lotsofmagic(self):
        relativepath = 'lotsofmagic/lotsofmagic.cpp'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(['--magic','cpp'])        

        expected = {'LDFLAGS': {'-lm'}, 'F1': {'1'}, 'LINKFLAGS': {'-lpcap'}, 'F2': {'2'}, 'F3': {'3'}}
        self.assertEqual(magicparser.parse(realpath), expected)

    def tearDown(self):
        uth.delete_existing_parsers()
