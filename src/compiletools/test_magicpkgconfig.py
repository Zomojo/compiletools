import os
import shutil
import subprocess
import configargparse
import compiletools.testhelper as uth
import compiletools.utils
import compiletools.cake
import compiletools.magicflags
import compiletools.headerdeps
import compiletools.test_base as tb

# Although this is virtually identical to the test_cake.py, we can't merge
# the tests due to memoized results.


class TestMagicPKGCONFIG(tb.BaseCompileToolsTestCase):


    def test_magicpkgconfig(self):
        # This test is to ensure that the //#PKG-CONFIG magic flag 
        # correctly acquires extra cflags and libs

        with uth.CompileToolsTestContext() as (tmpdir, config_path):
            # Copy the magicpkgconfig test files to the temp directory and compile
            # using ct-cake
            tmpmagicpkgconfig = os.path.join(tmpdir, "magicpkgconfig")
            shutil.copytree(self._get_sample_path("magicpkgconfig"), tmpmagicpkgconfig)
            
            with uth.DirectoryContext(tmpmagicpkgconfig):
                argv = [
                    "--exemarkers=main",
                    "--testmarkers=gtest.hpp",
                    "--CTCACHE=None",
                    "--quiet",
                    "--auto",
                    "--config=" + config_path,
                ]

                compiletools.cake.main(argv)

            relativepaths = ["magicpkgconfig/main.cpp"]
            self._verify_one_exe_per_main(relativepaths, search_dir=tmpdir)

    def test_cmdline_pkgconfig(self):
        # This test is to ensure that the "--pkg-config zlib" flag 
        # correctly acquires extra cflags and libs

        with uth.CompileToolsTestContext() as (tmpdir, config_path):
            # Copy the pkgconfig test files to the temp directory and compile
            # using ct-cake
            tmppkgconfig = os.path.join(tmpdir, "pkgconfig")
            shutil.copytree(self._get_sample_path("pkgconfig"), tmppkgconfig)
            
            with uth.DirectoryContext(tmppkgconfig):
                argv = [
                    "--exemarkers=main",
                    "--testmarkers=gtest.hpp",
                    "--CTCACHE=None",
                    "--quiet",
                    "--auto",
                    "--pkg-config=zlib",
                    "--config=" + config_path,
                ]

                compiletools.cake.main(argv)

            relativepaths = ["pkgconfig/main.cpp"]
            self._verify_one_exe_per_main(relativepaths, search_dir=tmpdir)

    def test_magicpkgconfig_flags_discovery(self):
        with uth.CompileToolsTestContext() as (tmpdir, config_path):
            # Copy the magicpkgconfig test files to the temp directory
            tmpmagicpkgconfig = os.path.join(tmpdir, "magicpkgconfig")
            shutil.copytree(self._get_sample_path("magicpkgconfig"), tmpmagicpkgconfig)
            
            with uth.DirectoryContext(tmpmagicpkgconfig):
                # Create a minimal args object for testing
                # Use a simpler approach - create args from scratch like other tests
                class MockArgs:
                    def __init__(self):
                        self.config_file = config_path
                        self.variant = 'debug'
                        self.verbose = 0
                        self.quiet = True
                        self.CTCACHE = 'None'
                        self.magic = 'direct'
                        self.headerdeps = 'direct'
                        self.CPPFLAGS = ''
                
                args = MockArgs()
                
                # Create magicflags parser
                headerdeps = compiletools.headerdeps.create(args)
                magicparser = compiletools.magicflags.create(args, headerdeps)
                
                # Test the sample file that contains //#PKG-CONFIG=zlib libcrypt
                sample_file = os.path.join(tmpmagicpkgconfig, "main.cpp")
                
                # Parse the magic flags
                parsed_flags = magicparser.parse(sample_file)
                
                # Verify PKG-CONFIG flag was found
                assert "PKG-CONFIG" in parsed_flags
                pkgconfig_flags = list(parsed_flags["PKG-CONFIG"])
                assert len(pkgconfig_flags) == 1
                assert pkgconfig_flags[0] == "zlib libcrypt"
                
                # Verify CXXFLAGS were extracted (should contain zlib and libcrypt cflags)
                assert "CXXFLAGS" in parsed_flags
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
                        assert zlib_cflags in cxxflags
                    if libcrypt_cflags:
                        assert libcrypt_cflags in cxxflags
                        
                except subprocess.CalledProcessError:
                    # pkg-config might fail for missing packages, but the test should still parse the PKG-CONFIG directive
                    pass
                
                # Verify LDFLAGS were extracted 
                assert "LDFLAGS" in parsed_flags
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
                        assert zlib_libs in ldflags
                    if libcrypt_libs:
                        assert libcrypt_libs in ldflags
                        
                except subprocess.CalledProcessError:
                    # pkg-config might fail for missing packages
                    pass



