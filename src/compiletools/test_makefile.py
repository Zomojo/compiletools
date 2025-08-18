import os
import shutil
import subprocess
import tempfile
import filecmp
import configargparse

import compiletools.utils
import compiletools.makefile
import compiletools.testhelper as uth

class TestMakefile:
    def setup_method(self):
        uth.reset()

    def _create_makefile_and_make(self, tempdir):
        origdir = uth.ctdir()
        print("origdir=" + origdir)
        print(tempdir)
        samplesdir = uth.samplesdir()
        print("samplesdir=" + samplesdir)
        
        with uth.DirectoryContext(tempdir):
            with uth.TempConfigContext(tempdir=tempdir) as temp_config_name:
                relativepaths = [
                    "numbers/test_direct_include.cpp",
                    "factory/test_factory.cpp",
                    "simple/helloworld_c.c",
                    "simple/helloworld_cpp.cpp",
                    "dottypaths/dottypaths.cpp",
                ]
                realpaths = [os.path.join(samplesdir, filename) for filename in relativepaths]
                with uth.ParserContext():  # Clear any existing parsers before calling main()
                    compiletools.makefile.main(["--config=" + temp_config_name] + realpaths)

                filelist = os.listdir(".")
                makefilename = [ff for ff in filelist if ff.startswith("Makefile")]
                cmd = ["make", "-f"] + makefilename
                subprocess.check_output(cmd, universal_newlines=True)

                # Check that an executable got built for each cpp
                actual_exes = set()
                for root, dirs, files in os.walk(tempdir):
                    for ff in files:
                        if compiletools.utils.isexecutable(os.path.join(root, ff)):
                            actual_exes.add(ff)
                            print(root + " " + ff)

                expected_exes = {
                    os.path.splitext(os.path.split(filename)[1])[0]
                    for filename in relativepaths
                }
                assert expected_exes == actual_exes

    def test_makefile(self):
        with uth.TempDirContextNoChange() as tempdir1:
            self._create_makefile_and_make(tempdir1)

            # Verify that the Makefiles and build products are identical between the two runs
            with uth.TempDirContextNoChange() as tempdir2:
                self._create_makefile_and_make(tempdir2)

                # Only check the bin directory as the config file has a unique name
                comparator = filecmp.dircmp(
                    os.path.join(tempdir1, "bin"), os.path.join(tempdir2, "bin")
                )
                # print(comparator.diff_files)
                assert len(comparator.diff_files) == 0

    def test_static_library(self):
        _test_library("--static")

    def test_dynamic_library(self):
        _test_library("--dynamic")

    def teardown_method(self):
        uth.reset()


def _test_library(static_dynamic):
    """ Manually specify what files to turn into the static (or dynamic)
        library and test linkage
    """
    samplesdir = uth.samplesdir()
    
    with uth.TempDirContextWithChange() as tempdir:
        with uth.TempConfigContext(tempdir=tempdir) as temp_config_name:
            exerelativepath = "numbers/test_library.cpp"
            librelativepaths = [
                "numbers/get_numbers.cpp",
                "numbers/get_int.cpp",
                "numbers/get_double.cpp",
            ]
            exerealpath = os.path.join(samplesdir, exerelativepath)
            librealpaths = [os.path.join(samplesdir, filename) for filename in librelativepaths]
            argv = ["--config=" + temp_config_name, exerealpath, static_dynamic] + librealpaths
            compiletools.makefile.main(argv)

            # Figure out the name of the makefile and run make
            filelist = os.listdir(".")
            makefilename = [ff for ff in filelist if ff.startswith("Makefile")]
            cmd = ["make", "-f"] + makefilename
            subprocess.check_output(cmd, universal_newlines=True)


