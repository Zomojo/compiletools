import unittest
import os
import os.path
import time
import shutil
import tempfile
import configargparse

# import pdb

import ct.unittesthelper as uth
import ct.cake


def _touch(fname):
    """ Update the modification time of the given file """
    with open(fname, "a"):
        os.utime(fname, None)


class TestCake(unittest.TestCase):
    def setUp(self):
        self._tmpdir = None
        self._config_name = None

    def _create_argv(self, cache_home="None"):
        assert self._config_name is not None
        return [
            "--exemarkers=main",
            "--testmarkers=unittest.hpp",
            "--auto",
            "--config=" + self._config_name,
            "--CTCACHE=" + cache_home,
        ]

    def _call_ct_cake(self, extraargv=[], cache_home="None"):
        assert cache_home is not None  # Note object None is not string 'None'
        uth.reset()
        ct.cake.main(self._create_argv(cache_home) + extraargv)

    def _setup_and_chdir_temp_dir(self):
        """ Returns the original working directory so you can chdir back to that at the end """
        origdir = os.getcwd()
        self._tmpdir = tempfile.mkdtemp()
        os.chdir(self._tmpdir)

        return origdir

    def test_no_git_root(self):
        origdir = self._setup_and_chdir_temp_dir()

        # Copy a known cpp file to a non-git directory and compile using cake
        relativepaths = ["simple/helloworld_cpp.cpp"]
        realpaths = [
            os.path.join(uth.samplesdir(), filename) for filename in relativepaths
        ]
        for ff in realpaths:
            shutil.copy2(ff, self._tmpdir)

        self._config_name = uth.create_temp_config(self._tmpdir)
        uth.create_temp_ct_conf(
            tempdir=self._tmpdir,
            defaultvariant=os.path.basename(self._config_name)[:-5],
        )
        self._call_ct_cake()

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

    def _create_deeper_cpp(self):
        data = """
        #include "deeper.hpp"

        int deeper_func(const int value)
        {
            return 42;
        }

        """

        with open("deeper.cpp", "w") as output:
            output.write(data)

    def _create_deeper_hpp(self):
        data = """
        int deeper_func(const int value);

        """

        with open("deeper.hpp", "w") as output:
            output.write(data)

    def _create_extra_cpp(self):
        extracpp = """
        #include "extra.hpp"

        int extra_func(const int value)
        {
            return 24;
        }

        """

        with open("extra.cpp", "w") as output:
            output.write(extracpp)

    def _create_extra_hpp(self):
        extrahpp = """
        int extra_func(const int value);

        """

        with open("extra.hpp", "w") as output:
            output.write(extrahpp)

    def _inject_deeper_hpp_into_extra_hpp(self):
        data = []
        with open("extra.hpp", "r") as infile:
            data = ['#include "deeper.hpp"'] + infile.readlines()

        with open("extra.hpp", "w") as outfile:
            outfile.writelines(data)

    def _create_main_cpp(self):
        # Write main.cpp
        maincpp = """
        #include "extra.hpp"
        
        int main(int argc, char* argv[])
        {
            return extra_func(42);
        }

        """

        with open("main.cpp", "w") as output:
            output.write(maincpp)

    def _create_recompile_test_files(self, deeper_is_included=False):
        """ Create a simple C++ program containing a main.cpp, extra.hpp, 
            extra.cpp, and extra.hpp in turn includes deeper.hpp which has an 
            associated deeper.cpp.
            This will allow us to test that editing any of those files 
            triggers a recompile.
        """
        origdir = self._setup_and_chdir_temp_dir()

        self._create_main_cpp()
        self._create_extra_hpp()
        self._create_extra_cpp()
        self._create_deeper_hpp()
        self._create_deeper_cpp()

        os.chdir(origdir)

    def _grab_timestamps(self, deeper_is_included=False):
        """ There are 8 files we want timestamps for.  
            main.cpp, extra.hpp, extra.cpp, deeper.hpp, deeper.cpp, deeper.o, main.o, extra.o 
            and the executable called "main".

            This must be called inside the directory where main.cpp lives.
        """

        # Create a namer so that we get the names of the object files correct
        cap = configargparse.getArgumentParser()
        args = ct.apptools.parseargs(cap, self._create_argv(), verbose=0)
        nmr = ct.namer.Namer(args)

        # These are the basic filenames
        fnames = [
            os.path.realpath("main.cpp"),
            os.path.realpath("extra.hpp"),
            os.path.realpath("extra.cpp"),
        ]

        if deeper_is_included:
            fnames.append(os.path.realpath("deeper.hpp"))
            fnames.append(os.path.realpath("deeper.cpp"))

        # Add in the object filenames (only cpp have object files)
        for fname in [name for name in fnames if "cpp" in name]:
            fnames.append(nmr.object_pathname(fname))

        # Add the executable name
        fnames.append(nmr.executable_pathname("main.cpp"))

        timestamps = {}
        for fname in fnames:
            timestamps[fname] = os.path.getmtime(fname)

        return timestamps

    def _verify_timestamps(self, expected_changes, prets, postts):
        """ Pass in the list of files that are expected to have newer 
            timestamps, the pre compiling timestamps and the 
            post compiling timestamps 
        """
        for fname in prets:
            # Due to the name munging it is slightly convoluted to
            # figure out if the filename is in the expected changes list
            expected_to_change = False
            for ec in expected_changes:
                # make sure the mangled name ends in exactly something like "main.o"
                if fname.endswith(ec):
                    expected_to_change = True

            if expected_to_change:
                self.assertGreater(postts[fname], prets[fname])
            else:
                print("verify " + fname)
                self.assertAlmostEqual(postts[fname], prets[fname])

    def _compile_edit_compile(
        self, files_to_edit, expected_changes, deeper_is_included=False
    ):
        """ Test that the compile, edit, compile cycle works as you expect """
        # print(self._tmpdir)
        origdir = os.getcwd()
        self._create_recompile_test_files(deeper_is_included)
        os.chdir(self._tmpdir)

        # Do an initial build
        self._config_name = uth.create_temp_config(self._tmpdir)
        uth.create_temp_ct_conf(
            tempdir=self._tmpdir,
            defaultvariant=os.path.basename(self._config_name)[:-5],
        )
        self._call_ct_cake(extraargv=[])

        # Grab the timestamps on the build products so that later we can test that only the expected ones changed
        # deeper_is_included must be false at this point becuase the option to inject it comes later/ver
        prets = self._grab_timestamps(deeper_is_included=False)

        # Edit the files for this test
        if deeper_is_included:
            self._inject_deeper_hpp_into_extra_hpp()

        for fname in files_to_edit:
            _touch(fname)

        # Rebuild
        self._call_ct_cake(extraargv=[])

        # Grab the timestamps on the build products for comparison
        postts = self._grab_timestamps(deeper_is_included)

        # Check that only the expected timestamps have changed
        self._verify_timestamps(expected_changes, prets, postts)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_source_edit_recompiles(self):
        """ Make sure that when the source file is altered that a rebuild occurs """
        self._compile_edit_compile(["main.cpp"], ["main.cpp", "main.o", "main"])

    def test_header_edit_recompiles(self):
        """ Make sure that when a header file is altered that a rebuild occurs """
        self._compile_edit_compile(
            ["extra.hpp"], ["extra.hpp", "extra.o", "main.o", "main"]
        )
        pass

    def test_dependent_source_edit_recompiles(self):
        """ Make sure that when an implied source file is altered that a rebuild occurs """
        self._compile_edit_compile(["extra.cpp"], ["extra.cpp", "extra.o", "main"])
        pass

    def test_deeper_include_edit_recompiles(self):
        """ Make sure that when a deeper include file is put into extra.hpp that a rebuild occurs """
        self._compile_edit_compile(
            ["extra.hpp"],
            ["extra.hpp", "deeper.hpp", "deeper.o", "extra.o", "main.o", "main"],
            deeper_is_included=True,
        )
        pass

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
