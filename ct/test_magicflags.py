import os
import unittest
import shutil
import configargparse
import tempfile

import ct.unittesthelper as uth
import ct.test_base as tb


class TestMagicFlagsModule(tb.BaseCompileToolsTestCase):



    def test_parsing_CFLAGS(self):
        os.chdir(self._tmpdir)

        relativepath = "simple/test_cflags.c"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(tempdir=self._tmpdir)
        self.assertSetEqual(
            set(magicparser.parse(realpath).get("CFLAGS")), set(["-std=gnu99"])
        )

    def test_SOURCE_direct(self):
        os.chdir(self._tmpdir)

        relativepath = "cross_platform/cross_platform.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(["--magic", "direct"], tempdir=self._tmpdir)
        self.assertSetEqual(
            set(magicparser.parse(realpath).get("SOURCE")),
            {os.path.join(samplesdir, "cross_platform/cross_platform_lin.cpp")},
        )

    def test_SOURCE_cpp(self):
        os.chdir(self._tmpdir)

        relativepath = "cross_platform/cross_platform.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = tb.create_magic_parser(["--magic", "cpp"], tempdir=self._tmpdir)
        self.assertSetEqual(
            set(magicparser.parse(realpath).get("SOURCE")),
            {os.path.join(samplesdir, "cross_platform/cross_platform_lin.cpp")},
        )

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
        self.assertEqual(magicparser.parse(realpath), expected)

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
        self.assertEqual(magicparser.parse(realpath), expected)

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
        self.assertEqual(magicparser.parse(realpath), expected)

    def test_direct_and_cpp_magic_generate_same_results(self):
        """Test that DirectMagicFlags and CppMagicFlags produce identical results on conditional compilation samples"""
        # Test key conditional compilation samples
        test_files = [
            "cross_platform/cross_platform.cpp",
            "magicsourceinheader/main.cpp", 
            "macro_deps/main.cpp"
        ]
        
        for filename in test_files:
            with self.subTest(filename=filename):
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
        self.assertIn("PKG-CONFIG", result_direct)
        self.assertIn("zlib", result_direct["PKG-CONFIG"])
        self.assertNotIn("libcrypt", result_direct.get("PKG-CONFIG", []))
        
        self.assertIn("SOURCE", result_direct)
        feature_x_source = os.path.join(samplesdir, "macro_deps/feature_x_impl.cpp")
        feature_y_source = os.path.join(samplesdir, "macro_deps/feature_y_impl.cpp")
        self.assertIn(feature_x_source, result_direct["SOURCE"])
        self.assertNotIn(feature_y_source, result_direct["SOURCE"])

