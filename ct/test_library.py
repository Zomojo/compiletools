from __future__ import print_function
from __future__ import unicode_literals

import unittest
import os
import shutil
import tempfile
import configargparse
import ct.unittesthelper as uth
import ct.cake


class TestLibrary(unittest.TestCase):
    def setUp(self):
        pass

    def test_build_and_link_static_library(self):
        # Setup
        origdir = os.getcwd()
        self._tmpdir = tempfile.mkdtemp()

        # Mimic the build.sh and create the library in a 'mylib' subdirectory
        mylibdir = os.path.join(self._tmpdir,'mylib')
        try:
            os.mkdir(mylibdir)
        except OSError:
            pass

        temp_config_name = ct.unittesthelper.create_temp_config(self._tmpdir)
        samplesdir = uth.samplesdir()
        relativepaths = ['library/mylib/get_numbers.cpp']
        realpaths = [os.path.join(samplesdir, filename)
                     for filename in relativepaths]
        argv = ['--config='+temp_config_name, '--static'] + realpaths
        os.chdir(mylibdir)
        uth.reset()
        ct.cake.main(argv)
        
        relativepaths = ['library/main.cpp']
        realpaths = [os.path.join(samplesdir, filename)
                     for filename in relativepaths]
        argv = ['--config='+temp_config_name] + realpaths
        os.chdir(self._tmpdir)
        uth.reset()
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
