from __future__ import print_function
from __future__ import unicode_literals

import filecmp
import os
import shutil
import sys
import tempfile
import configargparse
import unittest

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload

import ct.unittesthelper as uth
import ct.wrappedos
from ct.hunter import HeaderTree
from ct.hunter import HeaderDependencies


def callprocess(headerobj, filenames):
    result = set()
    for filename in filenames:
        realpath = ct.wrappedos.realpath(filename)
        result |= headerobj.process(realpath)
    return result


def _reload_hunter(xdg_cache_home):
    """ Set the XDG_CACHE_HOME environment variable to xdg_cache_home
        and reload the ct.hunter module
    """
    os.environ['XDG_CACHE_HOME'] = xdg_cache_home
    reload(ct.hunter)


def _generatecache(tempdir, name, realpaths, extraargs=None):
    if extraargs is None:
        extraargs = []
    argv = [
        'ct-test',
        '--variant',
        'debug',
        '--CPPFLAGS=-std=c++1z',
        '--include',
        uth.ctdir()] + extraargs + realpaths
    cachename = os.path.join(tempdir, name)
    _reload_hunter(cachename)

    cap = configargparse.getArgumentParser()
    ct.hunter.DependenciesBase.add_arguments(cap)
    args = ct.utils.parseargs(cap, argv)
    if name == 'ht':
        headerobj = HeaderTree(args)
    else:
        headerobj = HeaderDependencies(args)
    return cachename, callprocess(headerobj, realpaths)


class TestHunterModule(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def _ht_hd_tester(self, filename, extraargs=None):
        """ For a given filename call HeaderTree.process() and HeaderDependencies.process """
        if extraargs is None:
            extraargs = []
        realpath = ct.wrappedos.realpath(filename)
        argv = ['ct-test', realpath] + extraargs

        cap = configargparse.getArgumentParser()
        ct.hunter.DependenciesBase.add_arguments(cap)
        args = ct.utils.parseargs(cap, argv)
        ht = ct.hunter.HeaderTree(args)
        hd = ct.hunter.HeaderDependencies(args)
        htresult = ht.process(realpath)
        hdresult = hd.process(realpath)
        self.assertSetEqual(htresult, hdresult)

    def test_ht_and_hd_generate_same_results(self):
        filenames = [
            'samples/factory/test_factory.cpp',
            'samples/numbers/test_direct_include.cpp',
            'samples/dottypaths/dottypaths.cpp']
        for filename in filenames:
            self._ht_hd_tester(filename)

    def test_ht_and_hd_generate_same_results_preprocess(self):
        filenames = [
            'samples/factory/test_factory.cpp',
            'samples/numbers/test_direct_include.cpp',
            'samples/dottypaths/dottypaths.cpp']
        for filename in filenames:
            self._ht_hd_tester(filename, ["--preprocess"])

    def test_ht_and_hd_generate_same_results_nodirectread(self):
        filenames = [
            'samples/factory/test_factory.cpp',
            'samples/numbers/test_direct_include.cpp',
            'samples/dottypaths/dottypaths.cpp']
        for filename in filenames:
            self._ht_hd_tester(filename, ["--no-directread"])

    def test_hunter_follows_source_files_from_header(self):
        argv = [
            'ct-test',
            '--variant',
            'debug',
            '--CPPFLAGS=-std=c++1z',
            '--include',
            uth.ctdir()]
        cap = configargparse.getArgumentParser()
        ct.hunter.Hunter.add_arguments(cap)
        args = ct.utils.parseargs(cap, argv)
        ht = ct.hunter.Hunter(args)

        relativepath = 'factory/widget_factory.hpp'
        realpath = os.path.join(uth.samplesdir(), relativepath)
        filesfromheader = ht.required_source_files(realpath)
        filesfromsource = ht.required_source_files(
            ct.utils.implied_source(realpath))
        self.assertSetEqual(filesfromheader, filesfromsource)

    @staticmethod
    def _hunter_is_not_order_dependent(precall):
        samplesdir = uth.samplesdir()
        relativepaths = [
            'factory/test_factory.cpp',
            'numbers/test_direct_include.cpp',
            'simple/helloworld_c.c',
            'simple/helloworld_cpp.cpp',
            'simple/test_cflags.c']
        bulkpaths = [os.path.join(samplesdir, filename)
                     for filename in relativepaths]
        argv = [
            'ct-test',
            '--variant',
            'debug',
            '--CPPFLAGS=-std=c++1z',
            '--include',
            uth.ctdir(),
            '--filename'] + bulkpaths
        cap = configargparse.getArgumentParser()
        ct.hunter.Hunter.add_arguments(cap)
        args = ct.utils.parseargs(cap, argv)
        hntr = ct.hunter.Hunter(args)

        realpath = os.path.join(samplesdir, 'dottypaths/dottypaths.cpp')
        if precall:
            result = hntr.required_source_files(realpath)
            return result
        else:
            for filename in bulkpaths:
                discard = hntr.required_source_files(filename)
            result = hntr.required_source_files(realpath)
            return result

    def test_hunter_is_not_order_dependent(self):
        try:
            origcache = os.environ['XDG_CACHE_HOME']
        except KeyError:
            origcache = os.path.expanduser('~/.cache')

        tempdir = tempfile.mkdtemp()
        _reload_hunter(tempdir)

        result2 = self._hunter_is_not_order_dependent(True)
        result1 = self._hunter_is_not_order_dependent(False)
        result3 = self._hunter_is_not_order_dependent(False)
        result4 = self._hunter_is_not_order_dependent(True)

        self.assertSetEqual(result1, result2)
        self.assertSetEqual(result3, result2)
        self.assertSetEqual(result4, result2)

        # Cleanup
        shutil.rmtree(tempdir)
        _reload_hunter(origcache)

    def _ht_and_hd_generate_same_results_ex(self, extraargs=None):
        """ Test that HeaderTree and HeaderDependencies give the same results.
            Rather than polluting the real ct cache, use temporary cache
            directories.
        """
        if extraargs is None:
            extraargs = []
        try:
            origcache = os.environ['XDG_CACHE_HOME']
        except KeyError:
            origcache = os.path.expanduser('~/.cache')

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

        htcache, htresults = _generatecache(
            tempdir, 'ht', realpaths, extraargs)
        hdcache, hdresults = _generatecache(
            tempdir, 'hd', realpaths, extraargs)

        # Check the returned python sets are the same regardless of methodology
        # used to create
        self.assertSetEqual(htresults, hdresults)

        # Check the on-disk caches are the same
        comparator = filecmp.dircmp(htcache, hdcache)
        self.assertEqual(len(comparator.diff_files), 0)

        # Cleanup
        shutil.rmtree(tempdir)
        _reload_hunter(origcache)

    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "test_ht_and_hd_generate_same_results relies on XDG_CACHE_HOME")
    def test_ht_and_hd_generate_same_results_ex(self):
        self._ht_and_hd_generate_same_results_ex()

    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "test_ht_and_hd_generate_same_results relies on XDG_CACHE_HOME")
    def test_ht_and_hd_generate_same_results_ex_preprocess(self):
        self._ht_and_hd_generate_same_results_ex(["--preprocess"])

    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "test_ht_and_hd_generate_same_results relies on XDG_CACHE_HOME")
    def test_ht_and_hd_generate_same_results_ex_nodirectread(self):
        self._ht_and_hd_generate_same_results_ex(["--no-directread"])

    def test_parsing_CFLAGS(self):
        relativepath = 'simple/test_cflags.c'
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        argv = ['ct-test', realpath]
        cap = configargparse.getArgumentParser()
        ct.hunter.Hunter.add_arguments(cap)
        args = ct.utils.parseargs(cap, argv)
        hunter = ct.hunter.Hunter(args)
        hunter.required_files(realpath)
        self.assertSetEqual(
            hunter.parse_magic_flags(realpath).get('CFLAGS'),
            {'-std=gnu99'})

    def tearDown(self):
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()
