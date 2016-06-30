from __future__ import print_function
import unittest
import os
import sys
import tempfile
import shutil
import filecmp
try:
    reload
except NameError:
    from importlib import reload

import ct.unittesthelper as uth
import ct.wrappedos
from ct.hunter import HeaderTree
from ct.hunter import HeaderDependencies


def call_process(headerobj, filenames):
    result = set()
    for filename in filenames:
        realpath = ct.wrappedos.realpath(filename)
        result |= headerobj.process(realpath)
    return result


class TestHunterModule(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def test_implied_source_nonexistent_file(self):
        self.assertIsNone(ct.hunter.implied_source('nonexistent_file.hpp'))

    def test_implied_source(self):
        filename = 'samples/dottypaths/d2/d2.hpp'
        basename = os.path.splitext(filename)[0]
        expected = os.path.join(os.getcwd(),basename + '.cpp')
        result = ct.hunter.implied_source(filename)
        self.assertEqual(expected,result)

    def _ht_hd_tester(self, filename, extra_args=[]):
        """ For a given filename call HeaderTree.process() and HeaderDependencies.process """
        realpath = ct.wrappedos.realpath(filename)
        argv = ['ct-test',realpath] + extra_args
        ht = ct.hunter.HeaderTree(argv)
        hd = ct.hunter.HeaderDependencies(argv)
        htresult = ht.process(realpath)
        hdresult = hd.process(realpath)
        self.assertSetEqual(htresult,hdresult)

    def test_ht_and_hd_generate_same_results(self):
        filenames = ['samples/factory/test_factory.cpp', 'samples/numbers/test_direct_include.cpp']
        for filename in filenames:
            self._ht_hd_tester(filename)

    def test_ht_and_hd_generate_same_results_preprocess(self):
        filenames = ['samples/factory/test_factory.cpp', 'samples/numbers/test_direct_include.cpp']
        for filename in filenames:
            self._ht_hd_tester(filename, ["--preprocess"])

    def test_ht_and_hd_generate_same_results_nodirectread(self):
        filenames = ['samples/factory/test_factory.cpp', 'samples/numbers/test_direct_include.cpp']
        for filename in filenames:
            self._ht_hd_tester(filename, ["--no-directread"])

    def _ht_and_hd_generate_same_results_ex(self, extra_args=[]):
        """ Test that HeaderTree and HeaderDependencies give the same results.
            Rather than polluting the real ct cache, use temporary cache 
            directories.
        """
        try:
            origcache = os.environ['XDG_CACHE_HOME']
        except KeyError:
            origcache = os.path.expanduser('~/.cache')
        
        tempdir = tempfile.mkdtemp()
        filenames = ['samples/factory/test_factory.cpp', 'samples/numbers/test_direct_include.cpp']
        argv = ['ct-test','--variant','debug','--CPPFLAGS=-std=c++1z'] + extra_args + filenames
        # The following paragraphs are cut-n-paste  because my current level of
        # python prowess was insufficient in the attempt to move it to a function.
        # It is the reload that defeats me.
        htcache = os.path.join(tempdir,'ht')        
        os.environ['XDG_CACHE_HOME'] = htcache
        reload(ct.hunter)
        from ct.hunter import HeaderTree
        headerobj = HeaderTree(argv)
        htresults = call_process(headerobj, filenames)

        hdcache = os.path.join(tempdir,'hd')
        os.environ['XDG_CACHE_HOME'] = hdcache
        #print("XDG_CACHE_HOME: " + os.environ['XDG_CACHE_HOME'])
        reload(ct.hunter)
        from ct.hunter import HeaderDependencies
        headerobj = HeaderDependencies(argv)
        hdresults = call_process(headerobj, filenames)

        # Check the returned python sets are the same regardless of methodology used to create
        self.assertSetEqual(htresults,hdresults)

        # Check the on-disk caches are the same
        comparator = filecmp.dircmp(htcache,hdcache)
        self.assertEqual(len(comparator.diff_files),0)

        # Cleanup
        shutil.rmtree(tempdir)
        os.environ['XDG_CACHE_HOME'] = origcache


    @unittest.skipUnless(sys.platform.startswith("linux"),"test_ht_and_hd_generate_same_results relies on XDG_CACHE_HOME")
    def test_ht_and_hd_generate_same_results_ex(self):
        self._ht_and_hd_generate_same_results_ex()

    @unittest.skipUnless(sys.platform.startswith("linux"),"test_ht_and_hd_generate_same_results relies on XDG_CACHE_HOME")
    def test_ht_and_hd_generate_same_results_ex_preprocess(self):
        self._ht_and_hd_generate_same_results_ex(["--preprocess"])

    @unittest.skipUnless(sys.platform.startswith("linux"),"test_ht_and_hd_generate_same_results relies on XDG_CACHE_HOME")
    def test_ht_and_hd_generate_same_results_ex_nodirectread(self):
        self._ht_and_hd_generate_same_results_ex(["--no-directread"])

    def tearDown(self):
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()
