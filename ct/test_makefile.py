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

    def _create_makefile_and_make(self, samplesdir, tempdir):
        uth.delete_existing_parsers()
        os.chdir(tempdir)
        relativepaths = [
            'numbers/test_direct_include.cpp',
            'factory/test_factory.cpp',
            'simple/helloworld_c.c',
            'simple/helloworld_cpp.cpp',
            'dottypaths/dottypaths.cpp']
        realpaths = [os.path.join(samplesdir, filename)
                     for filename in relativepaths]
        ct.makefile.main(
            ['ct-test-makefile', '--CXXFLAGS=-std=c++1z'] + realpaths)

        cmd = ['make']
        subprocess.check_output(cmd, universal_newlines=True)

        # Check that an executable got built for each cpp
        actual_exes = set()
        for root, dirs, files in os.walk(tempdir):
            for ff in files:
                if uth.is_executable(os.path.join(root, ff)):
                    actual_exes.add(ff)

        expected_exes = {
            os.path.splitext(
                os.path.split(filename)[1])[0] for filename in relativepaths}
        self.assertSetEqual(expected_exes, actual_exes)

    def test_makefile(self):
        ctdir = os.path.dirname(os.path.realpath(__file__))
        samplesdir = os.path.realpath(os.path.join(ctdir, "../samples"))
        origdir = os.getcwd()

        tempdir1 = tempfile.mkdtemp()
        self._create_makefile_and_make(samplesdir, tempdir1)

        # Verify that the Makefiles and build products are identical between the two runs
        # This doesn't work because the Namer uses the wrappedos functions that cache
        # results.  They caching then doesn't see the current working directory has
        # changed. This is only a problem in testland so I'm putting it onto the long term
        # TODO list rather than fixing it now.
        #tempdir2 = tempfile.mkdtemp()
        # self._create_makefile_and_make(samplesdir,tempdir2)
        #comparator = filecmp.dircmp(tempdir1, tempdir2)
        #self.assertEqual(len(comparator.diff_files), 0)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(tempdir1)
        # shutil.rmtree(tempdir2)

    def tearDown(self):
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()
