import os
import shutil
import sys
import tempfile
import unittest
import filecmp
import configargparse
import ct.unittesthelper

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload

import ct.dirnamer
import ct.headerdeps
import ct.unittesthelper as uth


def _reload_ct(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the ct.hunter module
    """
    os.environ["CTCACHE"] = cache_home
    reload(ct.dirnamer)
    reload(ct.headerdeps)


def _callprocess(headerobj, filenames):
    result = []
    for filename in filenames:
        realpath = ct.wrappedos.realpath(filename)
        result.extend(headerobj.process(realpath))
    return ct.utils.ordered_unique(result)


def _generatecache(tempdir, name, realpaths, extraargs=None):
    if extraargs is None:
        extraargs = []
    temp_config_name = ct.unittesthelper.create_temp_config(tempdir)

    argv = [
        "--headerdeps",
        name,
        "--include",
        uth.ctdir(),
        "-c",
        temp_config_name,
    ] + extraargs
    cachename = os.path.join(tempdir, name)
    _reload_ct(cachename)

    cap = configargparse.getArgumentParser()
    ct.headerdeps.add_arguments(cap)
    args = ct.apptools.parseargs(cap, argv)
    headerdeps = ct.headerdeps.create(args)

    return cachename, temp_config_name, _callprocess(headerdeps, realpaths)


class TestHeaderDepsModule(unittest.TestCase):
    def setUp(self):
        uth.reset()
        cap = configargparse.getArgumentParser(
            description="Configargparser in test code",
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            args_for_setting_config_path=["-c", "--config"],
            ignore_unknown_config_file_keys=False,
        )
        ct.headerdeps.add_arguments(cap)

    def _direct_cpp_tester(self, filename, extraargs=None):
        """ For a given filename call HeaderTree.process() and HeaderDependencies.process """
        if extraargs is None:
            extraargs = []
        realpath = ct.wrappedos.realpath(filename)
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = ["--config=" + temp_config_name] + extraargs

        # Turn off diskcaching so that we can't just read up a prior result
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        argvdirect = argv + ["--headerdeps=direct"]
        argsdirect = ct.apptools.parseargs(cap, argvdirect)

        argvcpp = argv + ["--headerdeps", "cpp"]
        argscpp = ct.apptools.parseargs(cap, argvcpp)

        hdirect = ct.headerdeps.create(argsdirect)
        hcpp = ct.headerdeps.create(argscpp)
        hdirectresult = hdirect.process(realpath)
        hcppresult = hcpp.process(realpath)
        self.assertSetEqual(set(hdirectresult), set(hcppresult))
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def test_direct_and_cpp_generate_same_results(self):
        filenames = [
            "factory/test_factory.cpp",
            "numbers/test_direct_include.cpp",
            "dottypaths/dottypaths.cpp",
        ]
        for filename in filenames:
            self._direct_cpp_tester(os.path.join(uth.samplesdir(), filename))

    def _direct_and_cpp_generate_same_results_ex(self, extraargs=None):
        """ Test that HeaderTree and HeaderDependencies give the same results.
            Rather than polluting the real ct cache, use temporary cache
            directories.
        """
        if extraargs is None:
            extraargs = []

        origcache = ct.dirnamer.user_cache_dir()
        tempdir = tempfile.mkdtemp()
        samplesdir = uth.samplesdir()
        relativepaths = [
            "factory/test_factory.cpp",
            "numbers/test_direct_include.cpp",
            "simple/helloworld_c.c",
            "simple/helloworld_cpp.cpp",
            "simple/test_cflags.c",
        ]
        realpaths = [os.path.join(samplesdir, filename) for filename in relativepaths]

        directcache, config1, directresults = _generatecache(
            tempdir, "direct", realpaths, extraargs
        )
        cppcache, config2, cppresults = _generatecache(
            tempdir, "cpp", realpaths, extraargs
        )

        # Check the returned python sets are the same regardless of methodology
        # used to create
        self.assertSetEqual(set(directresults), set(cppresults))

        # Check the on-disk caches are the same
        comparator = filecmp.dircmp(directcache, cppcache)
        self.assertEqual(len(comparator.diff_files), 0)

        # Cleanup
        os.unlink(config1)
        os.unlink(config2)
        shutil.rmtree(tempdir)
        _reload_ct(origcache)

    def test_direct_and_cpp_generate_same_results_ex(self):
        self._direct_and_cpp_generate_same_results_ex()

    def test_conditional_includes(self):
        """Test that DirectHeaderDeps correctly handles conditional includes"""
        filename = os.path.join(uth.samplesdir(), "conditional_includes/main.cpp")
        self._direct_cpp_tester(filename)

    def test_user_defined_feature_headers(self):
        """Test that DirectHeaderDeps correctly handles user-defined feature macros"""
        filename = os.path.join(uth.samplesdir(), "feature_headers/main.cpp")
        
        # Test that both parsers give same results
        self._direct_cpp_tester(filename)
        
        # Also verify specific behavior - should include database.h and logging.h 
        # but not graphics.h or networking.h
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = ["--config=" + temp_config_name, "--headerdeps=direct"]
        
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        
        hdirect = ct.headerdeps.create(args)
        result = hdirect.process(filename)
        
        samplesdir = uth.samplesdir()
        expected_includes = {
            os.path.join(samplesdir, "feature_headers/feature_config.h"),
            os.path.join(samplesdir, "feature_headers/database.h"),
            os.path.join(samplesdir, "feature_headers/logging.h")
        }
        unexpected_includes = {
            os.path.join(samplesdir, "feature_headers/graphics.h"),
            os.path.join(samplesdir, "feature_headers/networking.h")
        }
        
        result_set = set(result)
        
        # Should include the enabled features
        for expected in expected_includes:
            self.assertIn(expected, result_set, f"Should include {expected}")
            
        # Should NOT include the disabled features  
        for unexpected in unexpected_includes:
            self.assertNotIn(unexpected, result_set, f"Should NOT include {unexpected}")
        
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def test_cppflags_macro_extraction(self):
        """Test that DirectHeaderDeps correctly extracts -D macro definitions from CPPFLAGS
        
        This test ensures DirectHeaderDeps properly parses -D flags from CPPFLAGS
        and uses them in conditional compilation logic to correctly identify header
        dependencies when macros are passed via compiler flags rather than defined
        in source files.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/main.cpp")
        
        # Test with -DENABLE_ADVANCED_FEATURES in CPPFLAGS
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -DENABLE_ADVANCED_FEATURES"
        ]
        
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        
        hdirect = ct.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # advanced_feature.hpp should be included because ENABLE_ADVANCED_FEATURES
        # is defined in CPPFLAGS and DirectHeaderDeps extracts -D flags
        advanced_feature_path = os.path.join(uth.samplesdir(), "cppflags_macros/advanced_feature.hpp")
        
        # This ensures DirectHeaderDeps correctly recognizes macros from CPPFLAGS
        self.assertIn(advanced_feature_path, result_set, 
                     "advanced_feature.hpp should be included when ENABLE_ADVANCED_FEATURES is defined in CPPFLAGS")
        
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def test_macro_extraction_from_all_flag_sources(self):
        """Test that DirectHeaderDeps extracts -D macros from CPPFLAGS, CFLAGS, and CXXFLAGS
        
        This comprehensive test ensures DirectHeaderDeps extracts macro definitions
        from all possible compiler flag sources to prevent users from slipping in
        macros through alternative flag variables.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/multi_flag_test.cpp")
        
        # Test CPPFLAGS macro extraction
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -DFROM_CPPFLAGS -DFROM_CFLAGS -DFROM_CXXFLAGS"
        ]
        
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        
        hdirect = ct.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # All three feature headers should be included since macros are defined in CPPFLAGS
        expected_headers = [
            os.path.join(uth.samplesdir(), "cppflags_macros/cppflags_feature.hpp"),
            os.path.join(uth.samplesdir(), "cppflags_macros/cflags_feature.hpp"), 
            os.path.join(uth.samplesdir(), "cppflags_macros/cxxflags_feature.hpp")
        ]
        
        for expected_header in expected_headers:
            self.assertIn(expected_header, result_set, 
                         f"{os.path.basename(expected_header)} should be included when its macro is defined")
        
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def test_compiler_builtin_macro_recognition(self):
        """Test that DirectHeaderDeps recognizes compiler and platform built-in macros
        
        This test ensures DirectHeaderDeps automatically detects compiler-specific,
        platform-specific, and architecture-specific macros that are typically
        defined by the compiler itself.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/compiler_builtin_test.cpp")
        
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir()
        ]
        
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        
        hdirect = ct.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # Expected headers based on typical GCC on Linux x86_64
        expected_headers = [
            os.path.join(uth.samplesdir(), "cppflags_macros/gcc_feature.hpp"),       # __GNUC__
            os.path.join(uth.samplesdir(), "cppflags_macros/x86_64_feature.hpp"),   # __x86_64__
            os.path.join(uth.samplesdir(), "cppflags_macros/linux_feature.hpp")     # __linux__
        ]
        
        for expected_header in expected_headers:
            self.assertIn(expected_header, result_set, 
                         f"{os.path.basename(expected_header)} should be included due to built-in macros")
        
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def test_riscv_architecture_macro_recognition(self):
        """Test that DirectHeaderDeps recognizes RISC-V architecture macros
        
        This test verifies that RISC-V specific macros are properly detected
        when passed via CPPFLAGS to simulate a RISC-V compilation environment.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/compiler_builtin_test.cpp")
        
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -D__riscv -D__riscv64__"
        ]
        
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        
        hdirect = ct.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # RISC-V feature header should be included due to __riscv macro
        riscv_feature_path = os.path.join(uth.samplesdir(), "cppflags_macros/riscv_feature.hpp")
        self.assertIn(riscv_feature_path, result_set, 
                     "riscv_feature.hpp should be included when __riscv macro is defined")
        
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def test_additional_compiler_macro_recognition(self):
        """Test that DirectHeaderDeps recognizes additional compiler built-in macros
        
        This test verifies support for MSVC, Intel, Emscripten, and ARM compilers
        by simulating their macro definitions via CPPFLAGS.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/compiler_builtin_test.cpp")
        
        # Test MSVC macros
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -D_MSC_VER -D__INTEL_COMPILER -D__EMSCRIPTEN__ -D__ARMCC_VERSION"
        ]
        
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        
        hdirect = ct.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # All compiler-specific headers should be included
        expected_headers = [
            os.path.join(uth.samplesdir(), "cppflags_macros/msvc_feature.hpp"),
            os.path.join(uth.samplesdir(), "cppflags_macros/intel_feature.hpp"),
            os.path.join(uth.samplesdir(), "cppflags_macros/emscripten_feature.hpp"),
            os.path.join(uth.samplesdir(), "cppflags_macros/armcc_feature.hpp")
        ]
        
        for expected_header in expected_headers:
            self.assertIn(expected_header, result_set, 
                         f"{os.path.basename(expected_header)} should be included when its compiler macro is defined")
        
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def test_elif_conditional_compilation_support(self):
        """Test that DirectHeaderDeps correctly handles #elif preprocessor directives
        
        This test ensures #elif directives are properly handled in conditional 
        compilation logic, correctly analyzing header dependencies when using 
        #elif defined() constructs in complex conditional compilation chains.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/elif_test.cpp")
        
        # Test VERSION_2 macro defined via CPPFLAGS - should include version2_feature.hpp
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -DVERSION_2"
        ]
        
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        
        hdirect = ct.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # Should include version2_feature.hpp when VERSION_2 is defined
        version2_path = os.path.join(uth.samplesdir(), "cppflags_macros/version2_feature.hpp")
        self.assertIn(version2_path, result_set, 
                     "version2_feature.hpp should be included when VERSION_2 is defined via #elif")
        
        # Should NOT include other version files
        version1_path = os.path.join(uth.samplesdir(), "cppflags_macros/version1_feature.hpp")
        version3_path = os.path.join(uth.samplesdir(), "cppflags_macros/version3_feature.hpp")
        default_path = os.path.join(uth.samplesdir(), "cppflags_macros/default_feature.hpp")
        
        self.assertNotIn(version1_path, result_set, "Should NOT include version1_feature.hpp")
        self.assertNotIn(version3_path, result_set, "Should NOT include version3_feature.hpp") 
        self.assertNotIn(default_path, result_set, "Should NOT include default_feature.hpp")
        
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def test_advanced_preprocessor_features(self):
        """Test advanced preprocessor directive support
        
        This test verifies comprehensive support for #if expressions, #undef, 
        complex conditional logic, and alternative preprocessor forms that
        are commonly used in real-world C/C++ code.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/advanced_preprocessor_test.cpp")
        
        # Test with FEATURE_A and ALT_FORM_TEST defined
        temp_config_name = ct.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -DFEATURE_A -DALT_FORM_TEST"
        ]
        
        origcache = ct.dirnamer.user_cache_dir()
        _reload_ct("None")
        cap = configargparse.getArgumentParser()
        ct.headerdeps.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        
        hdirect = ct.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # Expected headers that should be included with advanced preprocessor support
        expected_included_features = [
            "version_ge_2_feature.hpp",     # #if VERSION >= 2 (VERSION=3, so >= 2 is true)
            "partial_features.hpp",         # #elif with OR logic (FEATURE_A is defined)
            "temp_defined.hpp",             # Should be included before #undef
            "alt_form_feature.hpp",         # #if defined() form (ALT_FORM_TEST is defined)
            "version_205_plus.hpp"          # Complex numeric expressions (2*100+5 >= 205)
        ]
        
        # Verify all expected features are included
        for feature in expected_included_features:
            feature_path = os.path.join(uth.samplesdir(), f"cppflags_macros/{feature}")
            self.assertIn(feature_path, result_set, 
                         f"{feature} should be included with advanced preprocessor support")
        
        # Verify that temp_still_defined.hpp is NOT included (should be excluded after #undef)
        temp_still_defined_path = os.path.join(uth.samplesdir(), "cppflags_macros/temp_still_defined.hpp")
        self.assertNotIn(temp_still_defined_path, result_set, 
                        "temp_still_defined.hpp should NOT be included after #undef TEMP_MACRO")
        
        # Verify combined_features.hpp is NOT included (requires both FEATURE_A AND FEATURE_B)
        combined_features_path = os.path.join(uth.samplesdir(), "cppflags_macros/combined_features.hpp")
        self.assertNotIn(combined_features_path, result_set,
                        "combined_features.hpp should NOT be included (FEATURE_B not defined)")
        
        os.unlink(temp_config_name)
        _reload_ct(origcache)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
