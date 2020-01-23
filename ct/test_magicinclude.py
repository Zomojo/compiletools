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


class TestMagicInclude(unittest.TestCase):
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

    def test_magicinclude(self):
        # This test is to ensure that the //#INCLUDE magic flag
        # works to pick up subdir/important.hpp
        # and that the --include=subdir2 subdir3
        # works to pick up subdir2/important2.hpp and subdir3/important3.hpp

        origdir = os.getcwd()

        # Copy the magicinclude test files to the temp directory and compile
        # using cake
        tmpmagicinclude = os.path.join(self._tmpdir, "magicinclude")
        shutil.copytree(os.path.join(uth.samplesdir(), "magicinclude"), tmpmagicinclude)
        os.chdir(tmpmagicinclude)

        temp_config_name = ct.unittesthelper.create_temp_config(tmpmagicinclude)
        argv = [
            "--exemarkers=main",
            "--testmarkers=unittest.hpp",
            "--CTCACHE=None",
            "--quiet",
            "--include=subdir2",
            "--include=subdir3",
            "--auto",
            "--config=" + temp_config_name,
        ]

        uth.reset()
        ct.cake.main(argv)

        relativepaths = ["magicinclude/main.cpp"]
        self._verify_one_exe_per_main(relativepaths)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
