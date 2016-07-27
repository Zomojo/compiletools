from __future__ import print_function
from __future__ import unicode_literals

import unittest
import os
import configargparse

import ct.unittesthelper as uth
import ct.headerdeps
import ct.magicflags


class TestHeaderDepsModule(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def test_parsing_CFLAGS(self):
        relativepath = 'simple/test_cflags.c'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        argv = ['ct-test', realpath]
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        ct.magicflags.add_arguments(cap)
        args = ct.utils.parseargs(cap, argv)
        headerdeps = ct.headerdeps.create(args)
        magicflags = ct.magicflags.create(args, headerdeps)
        self.assertSetEqual(
            magicflags.parse(realpath).get('CFLAGS'),
            {'-std=gnu99'})

    def tearDown(self):
        uth.delete_existing_parsers()
