import os
import shutil
import tempfile
import configargparse
import compiletools.unittesthelper as uth
import compiletools.utils
import compiletools.cake

# Although this is virtually identical to the test_cake.py, we can't merge
# the tests due to memoized results.


class TestSerialiseTests:
    def setup_method(self):
        try:
            if self._tmpdir is not None:
                shutil.rmtree(self._tmpdir, ignore_errors=True)
        except AttributeError:
            pass
        self._tmpdir = tempfile.mkdtemp()

    def test_serialisetests(self):
        # This test is to ensure that --serialise-tests actually does so
        origdir = os.getcwd()

        # Copy the serialise_tests test files to the temp directory and compile
        # using ct-cake
        tmpserialisetests = os.path.join(self._tmpdir, "serialise_tests")
        shutil.copytree(os.path.join(uth.samplesdir(), "serialise_tests"), tmpserialisetests)
        os.chdir(tmpserialisetests)

        temp_config_name = compiletools.unittesthelper.create_temp_config(tmpserialisetests)
        argv = [
            "--exemarkers=main",
            "--testmarkers=gtest.hpp",
            "--CTCACHE=None",
            "--quiet",
            "--auto",
            "--serialise-tests",
            "--config=" + temp_config_name,
        ]

        uth.reset()
        compiletools.cake.main(argv)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def teardown_method(self):
        uth.reset()


