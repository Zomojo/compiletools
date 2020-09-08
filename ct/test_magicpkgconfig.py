import unittest
import os
import shutil
import tempfile
import configargparse
import ct.unittesthelper as uth
import ct.utils
import ct.cake

# Although this is virtually identical to the test_cake.py, we can't merge
# the tests due to memoized results.


class TestMagicPKGCONFIG(unittest.TestCase):
    def setUp(self):
        try:
            if self._tmpdir is not None:
                shutil.rmtree(self._tmpdir, ignore_errors=True)
        except AttributeError:
            pass
        self._tmpdir = tempfile.mkdtemp()

    def _verify_one_exe_per_main(self, relativepaths):
        actual_exes = set()
        for root, dirs, files in os.walk(self._tmpdir):
            for ff in files:
                if ct.utils.isexecutable(os.path.join(root, ff)):
                    actual_exes.add(ff)

        expected_exes = {
            os.path.splitext(os.path.split(filename)[1])[0]
            for filename in relativepaths
            if ct.utils.issource(filename)
        }
        self.assertSetEqual(expected_exes, actual_exes)

    def test_magicpkgconfig(self):
        # This test is to ensure that the //#PKG-CONFIG magic flag 
        # correctly acquires extra cflags and libs

        origdir = os.getcwd()

        # Copy the magicpkgconfig test files to the temp directory and compile
        # using ct-cake
        tmpmagicpkgconfig = os.path.join(self._tmpdir, "magicpkgconfig")
        shutil.copytree(os.path.join(uth.samplesdir(), "magicpkgconfig"), tmpmagicpkgconfig)
        os.chdir(tmpmagicpkgconfig)

        temp_config_name = ct.unittesthelper.create_temp_config(tmpmagicpkgconfig)
        argv = [
            "--exemarkers=main",
            "--testmarkers=gtest.hpp",
            "--CTCACHE=None",
            "--quiet",
            "--auto",
            "--config=" + temp_config_name,
        ]

        uth.reset()
        ct.cake.main(argv)

        relativepaths = ["magicpkgconfig/main.cpp"]
        self._verify_one_exe_per_main(relativepaths)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_cmdline_pkgconfig(self):
        # This test is to ensure that the "--pkg-config zlib" flag 
        # correctly acquires extra cflags and libs

        origdir = os.getcwd()

        # Copy the pkgconfig test files to the temp directory and compile
        # using ct-cake
        tmppkgconfig = os.path.join(self._tmpdir, "pkgconfig")
        shutil.copytree(os.path.join(uth.samplesdir(), "pkgconfig"), tmppkgconfig)
        os.chdir(tmppkgconfig)

        temp_config_name = ct.unittesthelper.create_temp_config(tmppkgconfig)
        argv = [
            "--exemarkers=main",
            "--testmarkers=gtest.hpp",
            "--CTCACHE=None",
            "--quiet",
            "--auto",
            "--pkg-config=zlib",
            "--config=" + temp_config_name,
        ]

        uth.reset()
        ct.cake.main(argv)

        relativepaths = ["pkgconfig/main.cpp"]
        self._verify_one_exe_per_main(relativepaths)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
