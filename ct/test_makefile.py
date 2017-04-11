from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import subprocess
import tempfile
import filecmp
import unittest
import configargparse

import ct.utils
import ct.makefile
import ct.unittesthelper as uth

# The memoizing of directories is really messsing about with tests.
# The current workaround is to simply use the same temp directory
_moduletmpdir = None


class TestMakefile(unittest.TestCase):

    def setUp(self):
        uth.reset()
        global _moduletmpdir
        if not _moduletmpdir:
            _moduletmpdir = tempfile.mkdtemp()
        try:
            os.mkdir(_moduletmpdir)
        except OSError:
            pass
        cap = configargparse.getArgumentParser(
            description='Configargparser in test code',
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            args_for_setting_config_path=["-c","--config"],
            ignore_unknown_config_file_keys=False)

    def _create_makefile_and_make(self, tempdir):
        origdir = uth.ctdir()
        print("origdir="+origdir)
        print(tempdir)
        samplesdir = uth.samplesdir()
        print("samplesdir="+samplesdir)
        os.chdir(tempdir)
        temp_config_name = ct.unittesthelper.create_temp_config(tempdir)
        relativepaths = [
            'numbers/test_direct_include.cpp',
            'factory/test_factory.cpp',
            'simple/helloworld_c.c',
            'simple/helloworld_cpp.cpp',
            'dottypaths/dottypaths.cpp']
        realpaths = [os.path.join(samplesdir, filename)
                     for filename in relativepaths]
        ct.makefile.main(
            ['--config='+temp_config_name] + realpaths)

        filelist = os.listdir('.')
        makefilename = [ff for ff in filelist if ff.startswith('Makefile')]
        cmd = ['make', '-f'] + makefilename
        subprocess.check_output(cmd, universal_newlines=True)

        # Check that an executable got built for each cpp
        actual_exes = set()
        for root, dirs, files in os.walk(tempdir):
            for ff in files:
                if ct.utils.isexecutable(os.path.join(root, ff)):
                    actual_exes.add(ff)
                    print(root + " " + ff)

        expected_exes = {
            os.path.splitext(
                os.path.split(filename)[1])[0] for filename in relativepaths}
        self.assertSetEqual(expected_exes, actual_exes)
        os.chdir(origdir)

    def test_makefile(self):
        #tempdir1 = _moduletmpdir
        tempdir1 = tempfile.mkdtemp()
        self._create_makefile_and_make(tempdir1)

        # Verify that the Makefiles and build products are identical between the two runs
        tempdir2 = tempfile.mkdtemp()
        self._create_makefile_and_make(tempdir2)

        # Only check the bin directory as the config file has a unique name
        comparator = filecmp.dircmp(os.path.join(tempdir1,'bin'), os.path.join(tempdir2,'bin'))
        print(comparator.diff_files)
        self.assertEqual(len(comparator.diff_files), 0)

        # Cleanup
        #shutil.rmtree(tempdir1, ignore_errors=True)
        # shutil.rmtree(tempdir2)

    def test_static_library(self):
        _test_library("--static")

    def test_dynamic_library(self):
        _test_library("--dynamic")

    def tearDown(self):
        shutil.rmtree(_moduletmpdir, ignore_errors=True)
        uth.reset()


def _test_library(static_dynamic):
    """ Manually specify what files to turn into the static (or dynamic)
        library and test linkage
    """
    samplesdir = uth.samplesdir()
    origdir = uth.ctdir()
    tempdir = _moduletmpdir
    # tempdir = tempfile.mkdtemp()
    os.chdir(tempdir)
    temp_config_name = ct.unittesthelper.create_temp_config(tempdir)

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
    argv = [
        '--config='+temp_config_name,
        exerealpath,
        static_dynamic] + librealpaths
    ct.makefile.main(argv)

    # Figure out the name of the makefile and run make
    filelist = os.listdir('.')
    makefilename = [ff for ff in filelist if ff.startswith('Makefile')]
    cmd = ['make', '-f'] + makefilename
    subprocess.check_output(cmd, universal_newlines=True)

    # Cleanup
    os.chdir(origdir)
    shutil.rmtree(tempdir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
