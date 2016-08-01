from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import sys
import tempfile
import unittest
import filecmp
import configargparse
try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload

import ct.dirnamer
import ct.headerdeps
import ct.unittesthelper as uth


def _reload_headerdeps(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the ct.hunter module
    """
    os.environ['CTCACHE'] = cache_home
    reload(ct.headerdeps)


def _callprocess(headerobj, filenames):
    result = set()
    for filename in filenames:
        realpath = ct.wrappedos.realpath(filename)
        result |= headerobj.process(realpath)
    return result


def _generatecache(tempdir, name, realpaths, extraargs=None):
    if extraargs is None:
        extraargs = []
    argv = [
        '--headerdeps',
        name,
        '--variant',
        'debug',
        '--CPPFLAGS=-std=c++1z',
        '--include',
        uth.ctdir()] + extraargs
    cachename = os.path.join(tempdir, name)
    _reload_headerdeps(cachename)

    cap = configargparse.getArgumentParser()
    ct.headerdeps.add_arguments(cap)
    args = ct.utils.parseargs(cap, argv)
    headerdeps = ct.headerdeps.create(args)

    return cachename, _callprocess(headerdeps, realpaths)


class TestHeaderDepsModule(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def _direct_cpp_tester(self, filename, extraargs=None):
        """ For a given filename call HeaderTree.process() and HeaderDependencies.process """
        if extraargs is None:
            extraargs = []
        realpath = ct.wrappedos.realpath(filename)
        argv = extraargs

        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        # TODO create argsdirect and argscpp
        argvdirect = argv + ['--headerdeps', 'direct']
        argsdirect = ct.utils.parseargs(cap, argvdirect)

        argvcpp = argv + ['--headerdeps', 'cpp']
        argscpp = ct.utils.parseargs(cap, argvcpp)

        hdirect = ct.headerdeps.create(argsdirect)
        hcpp = ct.headerdeps.create(argscpp)
        hdirectresult = hdirect.process(realpath)
        hcppresult = hcpp.process(realpath)
        self.assertSetEqual(hdirectresult, hcppresult)

    def test_direct_and_cpp_generate_same_results(self):
        filenames = [
            'samples/factory/test_factory.cpp',
            'samples/numbers/test_direct_include.cpp',
            'samples/dottypaths/dottypaths.cpp']
        for filename in filenames:
            self._direct_cpp_tester(filename)

    def _direct_and_cpp_generate_same_results_ex(self, extraargs=None):
        """ Test that HeaderTree and HeaderDependencies give the same results.
            Rather than polluting the real ct cache, use temporary cache
            directories.
        """
        if extraargs is None:
            extraargs = []

        origcache = ct.dirnamer.user_cache_dir()
        tempdir = tempfile.mkdtemp()
        samplesdir = uth.samplesdir()
        relativepaths = [
            'factory/test_factory.cpp',
            'numbers/test_direct_include.cpp',
            'simple/helloworld_c.c',
            'simple/helloworld_cpp.cpp',
            'simple/test_cflags.c']
        realpaths = [os.path.join(samplesdir, filename)
                     for filename in relativepaths]

        directcache, directresults = _generatecache(
            tempdir, 'direct', realpaths, [
                '--headerdeps', 'direct'] + extraargs)
        cppcache, cppresults = _generatecache(
            tempdir, 'cpp', realpaths, ['--headerdeps', 'cpp'] + extraargs)

        # Check the returned python sets are the same regardless of methodology
        # used to create
        self.assertSetEqual(directresults, cppresults)

        # Check the on-disk caches are the same
        comparator = filecmp.dircmp(directcache, cppcache)
        self.assertEqual(len(comparator.diff_files), 0)

        # Cleanup
        shutil.rmtree(tempdir)
        _reload_headerdeps(origcache)

    def test_direct_and_cpp_generate_same_results_ex(self):
        self._direct_and_cpp_generate_same_results_ex()

    def tearDown(self):
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()
