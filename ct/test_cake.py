from __future__ import print_function
from __future__ import unicode_literals

import unittest
import os
import shutil
import tempfile
import ct.unittesthelper as uth
import ct.cake


class TestCake(unittest.TestCase):
    def setUp(self):
        uth.reset()
    
    def test_no_git_root(self):
        # Setup
        origdir = os.getcwd()
        self._tmpdir = tempfile.mkdtemp()
        try:
            os.mkdir(self._tmpdir)
        except OSError:
            pass
        print(self._tmpdir)
        os.chdir(self._tmpdir)

        # Copy a known cpp file to a non-git directory and compile using cake
        relativepaths = ['simple/helloworld_cpp.cpp']
        realpaths = [os.path.join(uth.samplesdir(), filename)
                     for filename in relativepaths]
        for ff in realpaths:
            shutil.copy2(ff, self._tmpdir)

        argv = ['--exemarkers=main','--testmarkers=unittest.hpp','--auto','--CXXFLAGS=-std=c++11 -fPIC']
        ct.cake.main(argv)
        
        # Check that an executable got built for each cpp
        actual_exes = set()
        for root, dirs, files in os.walk(self._tmpdir):
            for ff in files:
                if ct.utils.isexecutable(os.path.join(root, ff)):
                    actual_exes.add(ff)

        expected_exes = {
            os.path.splitext(
                os.path.split(filename)[1])[0] for filename in relativepaths}
        self.assertSetEqual(expected_exes, actual_exes)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)
    
    def tearDown(self):
        uth.reset()


if __name__ == '__main__':
    unittest.main()
