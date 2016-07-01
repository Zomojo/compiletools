from __future__ import print_function
import unittest
import os
import tempfile
import subprocess
import shutil
import ct.unittesthelper as uth
import ct.makefile


class TestMakefile(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def test_makefile(self):
        ctdir = os.path.dirname(os.path.realpath(__file__))
        cakedir = os.path.realpath(os.path.join(ctdir, ".."))
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        relativepaths = [
            'samples/numbers/test_direct_include.cpp',
            'samples/factory/test_factory.cpp',
            'samples/simple/helloworld_c.c',
            'samples/simple/helloworld_cpp.cpp',
            'samples/dottypaths/dottypaths.cpp']
        realpaths = [os.path.join(cakedir, filename)
                     for filename in relativepaths]
        ct.makefile.main(
            ['ct-test-makefile', '--CXXFLAGS=-std=c++1z'] + realpaths)

        cmd = ['make']
        subprocess.check_output(cmd, universal_newlines=True)

        # Check that an executable got built for each cpp
        actual_exes = set() 
        for root, dirs, files in os.walk(tempdir):
            for ff in files:
                if uth.is_executable(os.path.join(root,ff)):
                    actual_exes.add(ff)

        expected_exes = {os.path.splitext(os.path.split(filename)[1])[0] for filename in relativepaths}
        self.assertSetEqual(expected_exes,actual_exes)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(tempdir)

    def tearDown(self):
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()
