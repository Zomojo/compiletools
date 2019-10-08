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
        # Copy the sample source files into the test build location
        mylibdir = os.path.join(self._tmpdir, "mylib")
        shutil.copytree(os.path.join(uth.samplesdir(), "library/mylib"), mylibdir)

        # Build the library
        temp_config_name = uth.create_temp_config(self._tmpdir)
        uth.create_temp_ct_conf(self._tmpdir, defaultvariant=temp_config_name[:-5])
        argv = [
            "--exemarkers=main",
            "--testmarkers=unittest.hpp",
            "--config=" + temp_config_name,
            "--CTCACHE=None",
            "--static",
            os.path.join(self._tmpdir, "mylib/get_numbers.cpp"),
        ]
        os.chdir(mylibdir)
        uth.reset()
        ct.cake.main(argv)

        # Copy the main that will link to the library into the test build location
        relativepaths = ["library/main.cpp"]
        realpaths = [
            os.path.join(uth.samplesdir(), filename) for filename in relativepaths
        ]
        for ff in realpaths:
            shutil.copy2(ff, self._tmpdir)

        # Build the exe, linking agains the library
        argv = ["--config=" + temp_config_name, "--CTCACHE=None"] + realpaths
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
            os.path.splitext(os.path.split(filename)[1])[0]
            for filename in relativepaths
        }
        self.assertSetEqual(expected_exes, actual_exes)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
