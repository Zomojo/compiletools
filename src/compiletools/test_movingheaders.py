import os
import shutil
import compiletools.testhelper as uth
import compiletools.cake
import compiletools.utils
import compiletools.test_base

# Although this is virtually identical to the test_cake.py, we can't merge the tests due to memoized results.
class TestMovingHeaders(compiletools.test_base.BaseCompileToolsTestCase):

    def test_moving_headers(self):
        # The concept of this test is to check that ct-cake copes with header files being changed directory
        
        with uth.TempDirContextWithChange() as tmpdir:
            ctcache_path = os.path.join(tmpdir, "ctcache")
            with uth.EnvironmentContext({"CTCACHE": ctcache_path}):
                # Setup
                os.mkdir(os.path.join(tmpdir, "subdir"))

                # Copy the movingheaders test files to the temp directory and compile using cake
                relativepaths = ["movingheaders/main.cpp", "movingheaders/someheader.hpp"]
                realpaths = [
                    self._get_sample_path(filename) for filename in relativepaths
                ]
                for ff in realpaths:
                    shutil.copy2(ff, tmpdir)

                temp_config_name = uth.create_temp_config(tmpdir)
                argv = [
                    "--exemarkers=main",
                    "--testmarkers=unittest.hpp",
                    "--CTCACHE=" + ctcache_path,
                    "--quiet",
                    "--auto",
                    "--include=subdir",
                    "--config=" + temp_config_name,
                ]
                with uth.ParserContext():
                    compiletools.cake.main(argv)

                self._verify_one_exe_per_main(relativepaths, search_dir=tmpdir)

                # Now move the header file to "subdir"  since it is already included in the path, all should be well
                os.rename(
                    os.path.join(tmpdir, "someheader.hpp"),
                    os.path.join(tmpdir, "subdir/someheader.hpp"),
                )
                shutil.rmtree(os.path.join(tmpdir, "bin"), ignore_errors=True)
                with uth.ParserContext():
                    compiletools.cake.main(argv)

                self._verify_one_exe_per_main(relativepaths, search_dir=tmpdir)


