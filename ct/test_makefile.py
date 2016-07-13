from __future__ import print_function
import unittest
import os
import tempfile
import subprocess
import shutil
import ct.unittesthelper as uth
import ct.makefile

# The memoizing of directories is really messsing about with tests.
# The current workaround is to simply use the same temp directory
_moduletmpdir = None


class TestMakefile(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()
        global _moduletmpdir
        if not _moduletmpdir:
            _moduletmpdir = tempfile.mkdtemp()
        try:
            os.mkdir(_moduletmpdir)
        except OSError:
            pass

    def _create_makefile_and_make(self, tempdir):
        uth.delete_existing_parsers()
        samplesdir = uth.samplesdir()
        origdir = uth.ctdir()
        #origdir = os.getcwd()
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
        os.chdir(origdir)

    def test_makefile(self):
        tempdir1 = _moduletmpdir
        #tempdir1 = tempfile.mkdtemp()
        self._create_makefile_and_make(
            tempdir1)

        # Verify that the Makefiles and build products are identical between the two runs
        # This doesn't work because the Namer uses the wrappedos functions that cache
        # results.  The caching then doesn't see the current working directory has
        # changed. This is only a problem in testland so I'm putting it onto the long term
        # TODO list rather than fixing it now.
        #tempdir2 = tempfile.mkdtemp()
        # self._create_makefile_and_make(samplesdir,tempdir2)
        #comparator = filecmp.dircmp(tempdir1, tempdir2)
        #self.assertEqual(len(comparator.diff_files), 0)

        # Cleanup
        shutil.rmtree(tempdir1, ignore_errors=True)
        # shutil.rmtree(tempdir2)

    def _test_library(self, static_dynamic):
        """ Manually specify what files to turn into the static (or dynamic)
            library and test linkage
        """
        samplesdir = uth.samplesdir()
        origdir = uth.ctdir()
        tempdir = _moduletmpdir
        #tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        exerelativepath = 'numbers/test_library.cpp'
        librelativepaths = [
            'numbers/get_numbers.cpp',
            'numbers/get_int.cpp',
            'numbers/get_double.cpp']
        exerealpath = os.path.join(samplesdir, exerelativepath)
        librealpaths = [
            os.path.join(
                samplesdir,
                filename) for filename in librelativepaths]
        argv = ['ct-test', static_dynamic] + \
            librealpaths + ['--filename', exerealpath]
        ct.makefile.main(argv)

        cmd = ['make']
        subprocess.check_output(cmd, universal_newlines=True)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)

    def test_static_library(self):
        self._test_library("--static")

    def test_dynamic_library(self):
        self._test_library("--dynamic")

    def tearDown(self):
        shutil.rmtree(_moduletmpdir, ignore_errors=True)
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()