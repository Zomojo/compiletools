from __future__ import print_function
from __future__ import unicode_literals

import unittest
import os
import shutil
import tempfile
import configargparse
import ct.unittesthelper as uth
import ct.cake
import ct.utils

# Although this is virtually identical to the test_cake.py, we can't merge the tests due to memoized results.
class TestMovingHeaders(unittest.TestCase):
    def setUp(self):
        try: 
            if self._tmpdir is not None:
                shutil.rmtree(self._tmpdir, ignore_errors=True)
        except AttributeError:
            pass
        self._tmpdir = tempfile.mkdtemp()
        uth.reset()
        cap = configargparse.getArgumentParser(
        description='Configargparser in test code',
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        args_for_setting_config_path=["-c","--config"],
        ignore_unknown_config_file_keys=False)
        #ct.cake.Cake.add_arguments(cap)
        #ct.cake.Cake.registercallback()
    
    def _verify_one_exe_per_main(self, relativepaths):
        actual_exes = set()
        for root, dirs, files in os.walk(self._tmpdir):
            for ff in files:
                if ct.utils.isexecutable(os.path.join(root, ff)):
                    actual_exes.add(ff)

        expected_exes = {
            os.path.splitext(
                os.path.split(filename)[1])[0] for filename in relativepaths if ct.utils.issource(filename)}
        self.assertSetEqual(expected_exes, actual_exes)

   
    def test_moving_headers(self):
        # The concept of this test is to check that ct-cake copes with header files being changed directory

        # Setup
        self.setUp()
        origdir = os.getcwd()
        os.mkdir(os.path.join(self._tmpdir,'subdir'))

        # Copy the movingheaders test files to the temp directory and compile using cake
        relativepaths = ['movingheaders/main.cpp', 'movingheaders/someheader.hpp']
        realpaths = [os.path.join(uth.samplesdir(), filename) for filename in relativepaths]        
        for ff in realpaths:
            shutil.copy2(ff, self._tmpdir)

        os.chdir(self._tmpdir)
        temp_config_name = ct.unittesthelper.create_temp_config(self._tmpdir)
        argv = ['--exemarkers=main','--testmarkers=unittest.hpp', '--quiet', '--auto','--include=subdir','--config='+temp_config_name ]
        ct.cake.main(argv)
        
        self._verify_one_exe_per_main(relativepaths)


        # Now move the header file to "subdir"  since it is already included in the path, all should be well
        os.rename(os.path.join(self._tmpdir, 'someheader.hpp'), os.path.join(self._tmpdir, 'subdir/someheader.hpp'));
        shutil.rmtree(os.path.join(self._tmpdir, 'bin'), ignore_errors=True);
        ct.cake.main(argv)
        
        self._verify_one_exe_per_main(relativepaths)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        
    def tearDown(self):
        uth.reset()


if __name__ == '__main__':
    unittest.main()
