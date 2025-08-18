import os
import shutil
import compiletools.testhelper as uth
import compiletools.utils
import compiletools.cake

# Although this is virtually identical to the test_cake.py, we can't merge
# the tests due to memoized results.


class TestSerialiseTests:
    def test_serialisetests(self):
        # This test is to ensure that --serialise-tests actually does so
        
        with uth.TempDirContextWithChange() as tmpdir:
            # Copy the serialise_tests test files to the temp directory and compile
            # using ct-cake
            tmpserialisetests = os.path.join(tmpdir, "serialise_tests")
            shutil.copytree(os.path.join(uth.samplesdir(), "serialise_tests"), tmpserialisetests)
            
            with uth.DirectoryContext(tmpserialisetests):
                temp_config_name = uth.create_temp_config(tmpserialisetests)
                argv = [
                    "--exemarkers=main",
                    "--testmarkers=gtest.hpp",
                    "--CTCACHE=None",
                    "--quiet",
                    "--auto",
                    "--serialise-tests",
                    "--config=" + temp_config_name,
                ]

                with uth.ParserContext():
                    compiletools.cake.main(argv)

    def teardown_method(self):
        uth.reset()


