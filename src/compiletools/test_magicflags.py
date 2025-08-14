import os
import shutil
import configargparse
import tempfile

import compiletools.unittesthelper as uth
import compiletools.test_base as tb


class TestMagicFlagsModule(tb.BaseCompileToolsTestCase):
    def test_parsing_CFLAGS(self):
        os.chdir(self._tmpdir)

        relativepath = "simple/test_cflags.c"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(tempdir=self._tmpdir)
        assert set(magicparser.parse(realpath).get("CFLAGS")) == set(["-std=gnu99"])

    def test_SOURCE_direct(self):
        os.chdir(self._tmpdir)

        relativepath = "cross_platform/cross_platform.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(["--magic", "direct"], tempdir=self._tmpdir)
        assert set(magicparser.parse(realpath).get("SOURCE")) == \
            {os.path.join(samplesdir, "cross_platform/cross_platform_lin.cpp")}

    def test_SOURCE_cpp(self):
        os.chdir(self._tmpdir)

        relativepath = "cross_platform/cross_platform.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(["--magic", "cpp"], tempdir=self._tmpdir)
        assert set(magicparser.parse(realpath).get("SOURCE")) == \
            {os.path.join(samplesdir, "cross_platform/cross_platform_lin.cpp")}

    def test_lotsofmagic(self):
        os.chdir(self._tmpdir)

        relativepath = "lotsofmagic/lotsofmagic.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(["--magic", "cpp"], tempdir=self._tmpdir)

        expected = {
            "LDFLAGS": ["-lm"],
            "F1": ["1"],
            "LINKFLAGS": ["-lpcap"],
            "F2": ["2"],
            "F3": ["3"],
        }
        assert magicparser.parse(realpath) == expected

    def test_SOURCE_in_header(self):
        os.chdir(self._tmpdir)

        relativepath = "magicsourceinheader/main.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(["--magic", "cpp"], tempdir=self._tmpdir)
        expected = {
            "LDFLAGS": ["-lm"],
            "SOURCE": [
                os.path.join(
                    samplesdir,
                    "magicsourceinheader/include_dir/sub_dir/the_code_lin.cpp",
                )
            ]
        }
        assert magicparser.parse(realpath) == expected

    def test_SOURCE_in_header_direct(self):
        os.chdir(self._tmpdir)

        relativepath = "magicsourceinheader/main.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(["--magic", "direct"], tempdir=self._tmpdir)
        expected = {
            "LDFLAGS": ["-lm"],
            "SOURCE": [
                os.path.join(
                    samplesdir,
                    "magicsourceinheader/include_dir/sub_dir/the_code_lin.cpp",
                )
            ]
        }
        assert magicparser.parse(realpath) == expected

    def test_direct_and_cpp_magic_generate_same_results(self):
        """Test that DirectMagicFlags and CppMagicFlags produce identical results on conditional compilation samples"""
        # Test key conditional compilation samples
        test_files = [
            "cross_platform/cross_platform.cpp",
            "magicsourceinheader/main.cpp", 
            "macro_deps/main.cpp"
        ]
        
        for filename in test_files:
            tb.compare_direct_cpp_magic(self, filename, self._tmpdir)

    def test_macro_deps_cross_file(self):
        """Test that macros defined in source files affect header magic flags"""
        os.chdir(self._tmpdir)

        relativepath = "macro_deps/main.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        
        # First verify both parsers give same results
        tb.compare_direct_cpp_magic(self, relativepath, self._tmpdir)
        
        # Then test specific behavior with direct parser
        magicparser_direct = tb.create_magic_parser(["--magic", "direct"], tempdir=self._tmpdir)
        result_direct = magicparser_direct.parse(realpath)
        
        # Should only contain feature X dependencies, not feature Y
        assert "PKG-CONFIG" in result_direct
        assert "zlib" in result_direct["PKG-CONFIG"]
        assert "libcrypt" not in result_direct.get("PKG-CONFIG", [])
        
        assert "SOURCE" in result_direct
        feature_x_source = os.path.join(samplesdir, "macro_deps/feature_x_impl.cpp")
        feature_y_source = os.path.join(samplesdir, "macro_deps/feature_y_impl.cpp")
        assert feature_x_source in result_direct["SOURCE"]
        assert feature_y_source not in result_direct["SOURCE"]

    def test_conditional_ldflags_with_command_line_macro(self):
        """Test that conditional LDFLAGS work with command-line defined macros"""
        os.chdir(self._tmpdir)

        realpath = os.path.join(uth.samplesdir(), "ldflags/conditional_ldflags_test.cpp")
        debug_flags = ["-ldebug_library", "-ltest_framework"]
        production_flags = ["-lproduction_library", "-loptimized_framework"]
        
        def check_ldflags(result, expected_flags, unexpected_flags):
            ldflags_str = " ".join(result["LDFLAGS"])
            return (all(flag in ldflags_str for flag in expected_flags) and
                    not any(flag in ldflags_str for flag in unexpected_flags))
        
        # Without macro - should get debug LDFLAGS
        result_debug = tb.create_magic_parser(["--magic", "direct"], tempdir=self._tmpdir).parse(realpath)
        assert check_ldflags(result_debug, debug_flags, production_flags)
        
        # With macro using direct magic - should get production LDFLAGS (currently fails due to bug)
        result_direct = tb.create_magic_parser(
            ["--magic", "direct", "--append-CPPFLAGS=-DUSE_PRODUCTION_LIBS"], 
            tempdir=self._tmpdir
        ).parse(realpath)
        assert check_ldflags(result_direct, production_flags, debug_flags), \
            "Direct magic should handle command-line macros correctly"
        
        # With macro using cpp magic - should work correctly
        result_cpp = tb.create_magic_parser(
            ["--magic", "cpp", "--append-CPPFLAGS=-DUSE_PRODUCTION_LIBS"],
            tempdir=self._tmpdir
        ).parse(realpath)
        assert check_ldflags(result_cpp, production_flags, debug_flags), \
            "CPP magic should handle command-line macros correctly"
        
        # Test that direct magic also works with CXXFLAGS (alternate way users might define macros)
        result_direct_cxx = tb.create_magic_parser(
            ["--magic", "direct", "--append-CXXFLAGS=-DUSE_PRODUCTION_LIBS"],
            tempdir=self._tmpdir
        ).parse(realpath)
        assert check_ldflags(result_direct_cxx, production_flags, debug_flags), \
            "Direct magic should handle macros from CXXFLAGS correctly"

