from __future__ import print_function
from __future__ import unicode_literals

import os
import unittest
import configargparse

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload

import ct.unittesthelper as uth
import ct.dirnamer
import ct.apptools
import ct.headerdeps
import ct.magicflags

def _reload_ct(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the ct.* modules
    """
    os.environ['CTCACHE'] = cache_home
    reload(ct.dirnamer)
    reload(ct.apptools)
    reload(ct.headerdeps)
    reload(ct.magicflags)


class TestMagicFlagsModule(unittest.TestCase):

    def setUp(self):
        uth.reset()
        config_files = ct.configutils.config_files_from_variant(exedir=uth.cakedir())
        cap = configargparse.getArgumentParser(
            description='TestMagicFlagsModule',
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            default_config_files=config_files,
            args_for_setting_config_path=["-c","--config"],
            ignore_unknown_config_file_keys=True)

    def _createmagicparser(self, extraargs=None, cache_home='None'):
        if not extraargs:
            extraargs = []
        argv = extraargs
        _reload_ct(cache_home)
        cap = configargparse.getArgumentParser()
        ct.apptools.add_common_arguments(cap,variant="gcc.debug")
        ct.dirnamer.add_arguments(cap)
        ct.headerdeps.add_arguments(cap)
        ct.magicflags.add_arguments(cap, variant="gcc.debug")
        args = ct.apptools.parseargs(cap, argv)
        headerdeps = ct.headerdeps.create(args)
        return ct.magicflags.create(args, headerdeps)

    def test_parsing_CFLAGS(self):
        relativepath = 'simple/test_cflags.c'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser()
        # magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            magicparser.parse(realpath).get('CFLAGS'),
            {'-std=gnu99'})

    def test_SOURCE_direct(self):
        relativepath = 'cross_platform/cross_platform.cpp'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(['--magic', 'direct'])
        # magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            magicparser.parse(realpath).get('SOURCE'),
            {os.path.join(samplesdir,'cross_platform/cross_platform_lin.cpp'), 
             os.path.join(samplesdir,'cross_platform/cross_platform_win.cpp')})

    def test_SOURCE_cpp(self):
        relativepath = 'cross_platform/cross_platform.cpp'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(['--magic', 'cpp'])
        # magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            magicparser.parse(realpath).get('SOURCE'),
            {os.path.join(samplesdir,'cross_platform/cross_platform_lin.cpp')})

    def test_lotsofmagic(self):
        relativepath = 'lotsofmagic/lotsofmagic.cpp'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(['--magic', 'cpp'])

        expected = {
            'LDFLAGS': {'-lm'},
            'F1': {'1'},
            'LINKFLAGS': {'-lpcap'},
            'F2': {'2'},
            'F3': {'3'}}
        self.assertEqual(magicparser.parse(realpath), expected)

    def test_SOURCE_in_header(self):
        relativepath = 'magicsourceinheader/main.cpp'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(['--magic', 'cpp'])
        expected = {
            'LDFLAGS': set(
                ['-lm']),
            'SOURCE': set(
                [os.path.join(samplesdir,'magicsourceinheader/include_dir/sub_dir/the_code_lin.cpp')])}
        self.assertEqual(magicparser.parse(realpath), expected)

    def tearDown(self):
        uth.reset()
