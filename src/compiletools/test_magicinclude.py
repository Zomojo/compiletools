import os
import shutil
import tempfile
import configargparse
import compiletools.unittesthelper as uth
import compiletools.utils
import compiletools.cake
import compiletools.test_base as tb

# Although this is virtually identical to the test_cake.py, we can't merge
# the tests due to memoized results.


class TestMagicInclude(tb.BaseCompileToolsTestCase):


    def test_magicinclude(self):
        # This test is to ensure that the //#INCLUDE magic flag
        # works to pick up subdir/important.hpp
        # and that the --include=subdir2 subdir3
        # works to pick up subdir2/important2.hpp and subdir3/important3.hpp

        with uth.CompileToolsTestContext() as (tmpdir, config_path):
            # Copy the magicinclude test files to the temp directory and compile
            # using cake
            tmpmagicinclude = os.path.join(tmpdir, "magicinclude")
            shutil.copytree(os.path.join(uth.samplesdir(), "magicinclude"), tmpmagicinclude)
            
            with uth.DirectoryContext(tmpmagicinclude):
                argv = [
                    "--exemarkers=main",
                    "--testmarkers=unittest.hpp",
                    "--CTCACHE=None",
                    "--quiet",
                    "--include=subdir2",
                    "--prepend-INCLUDE=subdir3",
                    "--auto",
                    "--config=" + config_path,
                ]

                compiletools.cake.main(argv)

            relativepaths = ["magicinclude/main.cpp"]
            self._verify_one_exe_per_main(relativepaths, search_dir=tmpdir)

    def test_magicinclude_append(self):
        # This test is to ensure that the //#INCLUDE magic flag
        # works to pick up subdir/important.hpp        
        # and that the --append-include=subdir2 subdir3   (note the "append")
        # works to pick up subdir2/important2.hpp and subdir3/important3.hpp

        with uth.CompileToolsTestContext() as (tmpdir, config_path):
            # Copy the magicinclude test files to the temp directory and compile
            # using cake
            tmpmagicinclude = os.path.join(tmpdir, "magicinclude")
            shutil.copytree(os.path.join(uth.samplesdir(), "magicinclude"), tmpmagicinclude)
            
            with uth.DirectoryContext(tmpmagicinclude):
                argv = [
                    "--exemarkers=main",
                    "--testmarkers=unittest.hpp",
                    "--CTCACHE=None",
                    "--quiet",
                    "--append-INCLUDE=subdir2",
                    "--append-INCLUDE=subdir3",
                    "--auto",
                    "--config=" + config_path,
                ]

                compiletools.cake.main(argv)

            relativepaths = ["magicinclude/main.cpp"]
            self._verify_one_exe_per_main(relativepaths, search_dir=tmpdir)




