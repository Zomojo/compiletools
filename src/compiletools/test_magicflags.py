import os

import compiletools.testhelper as uth
import compiletools.test_base as tb


class TestMagicFlagsModule(tb.BaseCompileToolsTestCase):
    
    def _check_flags(self, result, flag_type, expected_flags, unexpected_flags):
        """Helper to verify flags of given type contain expected flags and not unexpected ones"""
        flags_str = " ".join(result[flag_type])
        return (all(flag in flags_str for flag in expected_flags) and
                not any(flag in flags_str for flag in unexpected_flags))

    def _parse_with_magic(self, magic_type, source_file, extra_args=None):
        """Helper to create parser and parse file with given magic type"""
        args = ["--magic", magic_type] if magic_type else []
        if extra_args:
            args.extend(extra_args)
        return tb.create_magic_parser(args, tempdir=self._tmpdir).parse(
            self._get_sample_path(source_file)
        )

    def test_parsing_CFLAGS(self):
        """Test parsing CFLAGS from magic comments"""
        result = self._parse_with_magic(None, "simple/test_cflags.c")
        assert self._check_flags(result, "CFLAGS", ["-std=gnu99"], [])

    def test_SOURCE_direct(self):
        """Test SOURCE detection using direct magic"""
        result = self._parse_with_magic("direct", "cross_platform/cross_platform.cpp")
        expected_source = {self._get_sample_path("cross_platform/cross_platform_lin.cpp")}
        assert set(result.get("SOURCE")) == expected_source

    def test_SOURCE_cpp(self):
        """Test SOURCE detection using cpp magic"""
        result = self._parse_with_magic("cpp", "cross_platform/cross_platform.cpp")
        expected_source = {self._get_sample_path("cross_platform/cross_platform_lin.cpp")}
        assert set(result.get("SOURCE")) == expected_source

    def test_lotsofmagic(self):
        """Test parsing multiple magic flags from a complex file"""
        result = self._parse_with_magic("cpp", "lotsofmagic/lotsofmagic.cpp")
        
        # Check that basic magic flags are present
        assert "F1" in result and result["F1"] == ["1"]
        assert "F2" in result and result["F2"] == ["2"] 
        assert "F3" in result and result["F3"] == ["3"]
        assert "LINKFLAGS" in result and result["LINKFLAGS"] == ["-lpcap"]
        assert "PKG-CONFIG" in result and result["PKG-CONFIG"] == ["zlib"]
        
        # Check that PKG-CONFIG processing adds flags to LDFLAGS
        assert "LDFLAGS" in result
        ldflags = result["LDFLAGS"]
        assert "-lm" in ldflags  # From explicit //#LDFLAGS=-lm
        
        # Check that pkg-config flags were added (if pkg-config available)
        try:
            import subprocess
            zlib_libs = subprocess.run(["pkg-config", "--libs", "zlib"], 
                                     capture_output=True, text=True, check=True)
            if zlib_libs.stdout.strip():
                # The entire pkg-config output should be in LDFLAGS as a single item
                pkg_output = zlib_libs.stdout.strip()
                assert pkg_output in ldflags, f"Expected '{pkg_output}' from pkg-config to be in LDFLAGS"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # pkg-config not available or zlib not found - that's ok
            pass
            
        # Check that PKG-CONFIG processing adds empty entries for flag types
        assert "CPPFLAGS" in result
        assert "CFLAGS" in result  
        assert "CXXFLAGS" in result

    def test_SOURCE_in_header(self):
        """Test SOURCE detection from header files using cpp magic"""
        result = self._parse_with_magic("cpp", "magicsourceinheader/main.cpp")
        expected = {
            "LDFLAGS": ["-lm"],
            "SOURCE": [self._get_sample_path("magicsourceinheader/include_dir/sub_dir/the_code_lin.cpp")]
        }
        assert result == expected

    def test_SOURCE_in_header_direct(self):
        """Test SOURCE detection from header files using direct magic"""
        result = self._parse_with_magic("direct", "magicsourceinheader/main.cpp")
        expected = {
            "LDFLAGS": ["-lm"],
            "SOURCE": [self._get_sample_path("magicsourceinheader/include_dir/sub_dir/the_code_lin.cpp")]
        }
        assert result == expected

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
        source_file = "macro_deps/main.cpp"
        
        # First verify both parsers give same results
        tb.compare_direct_cpp_magic(self, source_file, self._tmpdir)
        
        # Then test specific behavior with direct parser
        result_direct = self._parse_with_magic("direct", source_file)
        
        # Should only contain feature X dependencies, not feature Y
        assert "PKG-CONFIG" in result_direct
        assert "zlib" in result_direct["PKG-CONFIG"]
        assert "libcrypt" not in result_direct.get("PKG-CONFIG", [])
        
        assert "SOURCE" in result_direct
        feature_x_source = self._get_sample_path("macro_deps/feature_x_impl.cpp")
        feature_y_source = self._get_sample_path("macro_deps/feature_y_impl.cpp")
        assert feature_x_source in result_direct["SOURCE"]
        assert feature_y_source not in result_direct["SOURCE"]

    def test_conditional_ldflags_with_command_line_macro(self):
        """Test that conditional LDFLAGS work with command-line defined macros"""
        
        source_file = "ldflags/conditional_ldflags_test.cpp"
        debug_flags = ["-ldebug_library", "-ltest_framework"]
        production_flags = ["-lproduction_library", "-loptimized_framework"]
        
        # Without macro - should get debug LDFLAGS
        result_debug = self._parse_with_magic("direct", source_file)
        assert self._check_flags(result_debug, "LDFLAGS", debug_flags, production_flags)
        
        # With macro using direct magic via CPPFLAGS
        result_direct = self._parse_with_magic("direct", source_file, ["--append-CPPFLAGS=-DUSE_PRODUCTION_LIBS"])
        assert self._check_flags(result_direct, "LDFLAGS", production_flags, debug_flags), \
            "Direct magic should handle command-line macros correctly"
        
        # With macro using cpp magic - should work correctly
        result_cpp = self._parse_with_magic("cpp", source_file, ["--append-CPPFLAGS=-DUSE_PRODUCTION_LIBS"])
        assert self._check_flags(result_cpp, "LDFLAGS", production_flags, debug_flags), \
            "CPP magic should handle command-line macros correctly"
        
        # Test that direct magic also works with CXXFLAGS
        result_direct_cxx = self._parse_with_magic("direct", source_file, ["--append-CXXFLAGS=-DUSE_PRODUCTION_LIBS"])
        assert self._check_flags(result_direct_cxx, "LDFLAGS", production_flags, debug_flags), \
            "Direct magic should handle macros from CXXFLAGS correctly"

    def test_version_dependent_ldflags_requires_feature_parity(self):
        """Test that DirectMagicFlags must have feature parity with CppMagicFlags for complex #if expressions"""
        
        source_file = "ldflags/version_dependent_ldflags.cpp"
        new_api_flags = ["-lnewapi", "-ladvanced_features"]
        old_api_flags = ["-loldapi", "-lbasic_features"]
        
        # Both magic types should produce identical results for complex #if expressions
        result_cpp = self._parse_with_magic("cpp", source_file)
        result_direct = self._parse_with_magic("direct", source_file)
        
        # Both should correctly evaluate the complex expression and choose new API
        assert self._check_flags(result_cpp, "LDFLAGS", new_api_flags, old_api_flags), \
            "CPP magic should correctly evaluate complex #if expressions"
        assert self._check_flags(result_direct, "LDFLAGS", new_api_flags, old_api_flags), \
            "DirectMagicFlags must have feature parity with CppMagicFlags for complex #if expressions"

