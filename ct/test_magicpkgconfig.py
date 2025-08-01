import unittest
import os
import shutil
import tempfile
import subprocess
import configargparse
import ct.unittesthelper as uth
import ct.utils
import ct.cake
import ct.magicflags
import ct.headerdeps

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

    def test_magicpkgconfig_flags_discovery(self):
        origdir = os.getcwd()
        
        # Copy the magicpkgconfig test files to the temp directory
        tmpmagicpkgconfig = os.path.join(self._tmpdir, "magicpkgconfig")
        shutil.copytree(os.path.join(uth.samplesdir(), "magicpkgconfig"), tmpmagicpkgconfig)
        os.chdir(tmpmagicpkgconfig)
        
        # Create a minimal args object for testing
        temp_config_name = ct.unittesthelper.create_temp_config(tmpmagicpkgconfig)
        
        # Use a simpler approach - create args from scratch like other tests
        class MockArgs:
            def __init__(self):
                self.config_file = temp_config_name
                self.variant = 'debug'
                self.verbose = 0
                self.quiet = True
                self.CTCACHE = 'None'
                self.magic = 'direct'
                self.headerdeps = 'direct'
                self.CPPFLAGS = ''
        
        args = MockArgs()
        
        # Create magicflags parser
        headerdeps = ct.headerdeps.create(args)
        magicparser = ct.magicflags.create(args, headerdeps)
        
        # Test the sample file that contains //#PKG-CONFIG=zlib libcrypt
        sample_file = os.path.join(tmpmagicpkgconfig, "main.cpp")
        
        # Parse the magic flags
        parsed_flags = magicparser.parse(sample_file)
        
        # Verify PKG-CONFIG flag was found
        self.assertIn("PKG-CONFIG", parsed_flags)
        pkgconfig_flags = list(parsed_flags["PKG-CONFIG"])
        self.assertEqual(len(pkgconfig_flags), 1)
        self.assertEqual(pkgconfig_flags[0], "zlib libcrypt")
        
        # Verify CXXFLAGS were extracted (should contain zlib and libcrypt cflags)
        self.assertIn("CXXFLAGS", parsed_flags)
        cxxflags = " ".join(parsed_flags["CXXFLAGS"])
        
        # Check that pkg-config results are present (basic validation)
        try:
            zlib_cflags = subprocess.run(
                ["pkg-config", "--cflags", "zlib"], 
                capture_output=True, text=True, check=True
            ).stdout.strip().replace("-I", "-isystem ")
            
            libcrypt_cflags = subprocess.run(
                ["pkg-config", "--cflags", "libcrypt"], 
                capture_output=True, text=True, check=True
            ).stdout.strip().replace("-I", "-isystem ")
            
            # Verify the parsed flags contain the expected pkg-config results
            if zlib_cflags:
                self.assertIn(zlib_cflags, cxxflags)
            if libcrypt_cflags:
                self.assertIn(libcrypt_cflags, cxxflags)
                
        except subprocess.CalledProcessError:
            # pkg-config might fail for missing packages, but the test should still parse the PKG-CONFIG directive
            pass
        
        # Verify LDFLAGS were extracted 
        self.assertIn("LDFLAGS", parsed_flags)
        ldflags = " ".join(parsed_flags["LDFLAGS"])
        
        try:
            zlib_libs = subprocess.run(
                ["pkg-config", "--libs", "zlib"], 
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            libcrypt_libs = subprocess.run(
                ["pkg-config", "--libs", "libcrypt"], 
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            # Verify the parsed flags contain the expected pkg-config results
            if zlib_libs:
                self.assertIn(zlib_libs, ldflags)
            if libcrypt_libs:
                self.assertIn(libcrypt_libs, ldflags)
                
        except subprocess.CalledProcessError:
            # pkg-config might fail for missing packages
            pass
        
        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
