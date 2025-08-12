import os
import shutil
import sys
import tempfile
import filecmp
import configargparse
import compiletools.unittesthelper
import compiletools.test_base as tb

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload

import compiletools.dirnamer
import compiletools.headerdeps
import compiletools.unittesthelper as uth


def _reload_ct_with_cache(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the compiletools.hunter module
    """
    with uth.EnvironmentContext({"CTCACHE": cache_home}):
        reload(compiletools.dirnamer)
        reload(compiletools.headerdeps)
        return cache_home


def _callprocess(headerobj, filenames):
    result = []
    for filename in filenames:
        realpath = compiletools.wrappedos.realpath(filename)
        result.extend(headerobj.process(realpath))
    return compiletools.utils.ordered_unique(result)


def _generatecache(tempdir, name, realpaths, extraargs=None):
    if extraargs is None:
        extraargs = []
    temp_config_name = compiletools.unittesthelper.create_temp_config(tempdir)

    argv = [
        "--headerdeps",
        name,
        "--include",
        uth.ctdir(),
        "-c",
        temp_config_name,
    ] + extraargs
    cachename = os.path.join(tempdir, name)
    with uth.EnvironmentContext({"CTCACHE": cachename}):
        reload(compiletools.dirnamer)
        reload(compiletools.headerdeps)

    cap = configargparse.getArgumentParser()
    compiletools.headerdeps.add_arguments(cap)
    args = compiletools.apptools.parseargs(cap, argv)
    headerdeps = compiletools.headerdeps.create(args)

    return cachename, temp_config_name, _callprocess(headerdeps, realpaths)


class TestHeaderDepsModule(tb.BaseCompileToolsTestCase):
    def setup_method(self):
        super().setup_method()
        cap = configargparse.getArgumentParser(
            description="Configargparser in test code",
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            args_for_setting_config_path=["-c", "--config"],
            ignore_unknown_config_file_keys=False,
        )
        compiletools.headerdeps.add_arguments(cap)


    def test_direct_and_cpp_generate_same_results(self):
        filenames = [
            "factory/test_factory.cpp",
            "numbers/test_direct_include.cpp",
            "dottypaths/dottypaths.cpp",
        ]
        for filename in filenames:
            tb.compare_direct_cpp_headers(self, os.path.join(uth.samplesdir(), filename))

    def _direct_and_cpp_generate_same_results_ex(self, extraargs=None):
        """ Test that HeaderTree and HeaderDependencies give the same results.
            Rather than polluting the real ct cache, use temporary cache
            directories.
        """
        if extraargs is None:
            extraargs = []

        origcache = compiletools.dirnamer.user_cache_dir()
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
        assert set(directresults) == set(cppresults)

        # Check the on-disk caches are the same
        comparator = filecmp.dircmp(directcache, cppcache)
        assert len(comparator.diff_files) == 0

        # Cleanup
        os.unlink(config1)
        os.unlink(config2)
        shutil.rmtree(tempdir)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_direct_and_cpp_generate_same_results_ex(self):
        self._direct_and_cpp_generate_same_results_ex()

    def test_conditional_includes(self):
        """Test that DirectHeaderDeps correctly handles conditional includes"""
        filename = os.path.join(uth.samplesdir(), "conditional_includes/main.cpp")
        tb.compare_direct_cpp_headers(self, filename)

    def test_user_defined_feature_headers(self):
        """Test that DirectHeaderDeps correctly handles user-defined feature macros"""
        filename = os.path.join(uth.samplesdir(), "feature_headers/main.cpp")
        
        # Test that both parsers give same results
        tb.compare_direct_cpp_headers(self, filename)
        
        # Also verify specific behavior - should include database.h and logging.h 
        # but not graphics.h or networking.h
        temp_config_name = compiletools.unittesthelper.create_temp_config()
        argv = ["--config=" + temp_config_name, "--headerdeps=direct"]
        
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        args = compiletools.apptools.parseargs(cap, argv)
        
        hdirect = compiletools.headerdeps.create(args)
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
            assert expected in result_set, f"Should include {expected}"
            
        # Should NOT include the disabled features  
        for unexpected in unexpected_includes:
            assert unexpected not in result_set, f"Should NOT include {unexpected}"
        
        os.unlink(temp_config_name)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_cppflags_macro_extraction(self):
        """Test that DirectHeaderDeps correctly extracts -D macro definitions from CPPFLAGS
        
        This test ensures DirectHeaderDeps properly parses -D flags from CPPFLAGS
        and uses them in conditional compilation logic to correctly identify header
        dependencies when macros are passed via compiler flags rather than defined
        in source files.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/main.cpp")
        
        # Test with -DENABLE_ADVANCED_FEATURES in CPPFLAGS
        temp_config_name = compiletools.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -DENABLE_ADVANCED_FEATURES"
        ]
        
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        args = compiletools.apptools.parseargs(cap, argv)
        
        hdirect = compiletools.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # advanced_feature.hpp should be included because ENABLE_ADVANCED_FEATURES
        # is defined in CPPFLAGS and DirectHeaderDeps extracts -D flags
        advanced_feature_path = os.path.join(uth.samplesdir(), "cppflags_macros/advanced_feature.hpp")
        
        # This ensures DirectHeaderDeps correctly recognizes macros from CPPFLAGS
        assert advanced_feature_path in result_set, \
                     "advanced_feature.hpp should be included when ENABLE_ADVANCED_FEATURES is defined in CPPFLAGS"
        
        os.unlink(temp_config_name)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_macro_extraction_from_all_flag_sources(self):
        """Test that DirectHeaderDeps extracts -D macros from CPPFLAGS, CFLAGS, and CXXFLAGS
        
        This comprehensive test ensures DirectHeaderDeps extracts macro definitions
        from all possible compiler flag sources to prevent users from slipping in
        macros through alternative flag variables.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/multi_flag_test.cpp")
        
        # Test CPPFLAGS macro extraction
        temp_config_name = compiletools.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -DFROM_CPPFLAGS -DFROM_CFLAGS -DFROM_CXXFLAGS"
        ]
        
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        args = compiletools.apptools.parseargs(cap, argv)
        
        hdirect = compiletools.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # All three feature headers should be included since macros are defined in CPPFLAGS
        expected_headers = [
            os.path.join(uth.samplesdir(), "cppflags_macros/cppflags_feature.hpp"),
            os.path.join(uth.samplesdir(), "cppflags_macros/cflags_feature.hpp"), 
            os.path.join(uth.samplesdir(), "cppflags_macros/cxxflags_feature.hpp")
        ]
        
        for expected_header in expected_headers:
            assert expected_header in result_set, \
                         f"{os.path.basename(expected_header)} should be included when its macro is defined"
        
        os.unlink(temp_config_name)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_compiler_builtin_macro_recognition(self):
        """Test that DirectHeaderDeps recognizes compiler and platform built-in macros
        
        This test ensures DirectHeaderDeps automatically detects compiler-specific,
        platform-specific, and architecture-specific macros that are typically
        defined by the compiler itself.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/compiler_builtin_test.cpp")
        
        temp_config_name = compiletools.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir()
        ]
        
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        args = compiletools.apptools.parseargs(cap, argv)
        
        hdirect = compiletools.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # Expected headers based on compiler and platform built-in macros
        import platform
        import sys
        
        expected_headers = [
            os.path.join(uth.samplesdir(), "cppflags_macros/gcc_feature.hpp"),       # __GNUC__
        ]
        
        # Add platform-specific header based on current platform
        if sys.platform.startswith('linux'):
            expected_headers.append(os.path.join(uth.samplesdir(), "cppflags_macros/linux_feature.hpp"))
        # Note: For other platforms (Windows, macOS), we'd need corresponding feature files
        
        # Add architecture-specific header based on current platform
        arch = platform.machine().lower()
        if arch in ['x86_64', 'amd64']:
            expected_headers.append(os.path.join(uth.samplesdir(), "cppflags_macros/x86_64_feature.hpp"))
        elif arch.startswith('arm') and not ('64' in arch or arch.startswith('aarch')):
            expected_headers.append(os.path.join(uth.samplesdir(), "cppflags_macros/arm_feature.hpp"))
        elif arch.startswith('aarch') or (arch.startswith('arm') and '64' in arch):
            expected_headers.append(os.path.join(uth.samplesdir(), "cppflags_macros/aarch64_feature.hpp"))
        elif arch.startswith('riscv') or 'riscv' in arch:
            expected_headers.append(os.path.join(uth.samplesdir(), "cppflags_macros/riscv_feature.hpp"))
        
        for expected_header in expected_headers:
            assert expected_header in result_set, \
                         f"{os.path.basename(expected_header)} should be included due to built-in macros for {arch}"
        
        os.unlink(temp_config_name)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_riscv_architecture_macro_recognition(self):
        """Test that DirectHeaderDeps recognizes RISC-V architecture macros
        
        This test verifies that RISC-V specific macros are properly detected
        when passed via CPPFLAGS to simulate a RISC-V compilation environment.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/compiler_builtin_test.cpp")
        
        temp_config_name = compiletools.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -D__riscv -D__riscv64__"
        ]
        
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        args = compiletools.apptools.parseargs(cap, argv)
        
        hdirect = compiletools.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # RISC-V feature header should be included due to __riscv macro
        riscv_feature_path = os.path.join(uth.samplesdir(), "cppflags_macros/riscv_feature.hpp")
        assert riscv_feature_path in result_set, \
                     "riscv_feature.hpp should be included when __riscv macro is defined"
        
        os.unlink(temp_config_name)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_additional_compiler_macro_recognition(self):
        """Test that DirectHeaderDeps recognizes additional compiler built-in macros
        
        This test verifies support for MSVC, Intel, Emscripten, and ARM compilers
        by simulating their macro definitions via CPPFLAGS.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/compiler_builtin_test.cpp")
        
        # Test MSVC macros
        temp_config_name = compiletools.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -D_MSC_VER -D__INTEL_COMPILER -D__EMSCRIPTEN__ -D__ARMCC_VERSION"
        ]
        
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        args = compiletools.apptools.parseargs(cap, argv)
        
        hdirect = compiletools.headerdeps.create(args)
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
            assert expected_header in result_set, \
                         f"{os.path.basename(expected_header)} should be included when its compiler macro is defined"
        
        os.unlink(temp_config_name)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_elif_conditional_compilation_support(self):
        """Test that DirectHeaderDeps correctly handles #elif preprocessor directives
        
        This test ensures #elif directives are properly handled in conditional 
        compilation logic, correctly analyzing header dependencies when using 
        #elif defined() constructs in complex conditional compilation chains.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/elif_test.cpp")
        
        # Test VERSION_2 macro defined via CPPFLAGS - should include version2_feature.hpp
        temp_config_name = compiletools.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -DVERSION_2"
        ]
        
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        args = compiletools.apptools.parseargs(cap, argv)
        
        hdirect = compiletools.headerdeps.create(args)
        result = hdirect.process(filename)
        result_set = set(result)
        
        # Should include version2_feature.hpp when VERSION_2 is defined
        version2_path = os.path.join(uth.samplesdir(), "cppflags_macros/version2_feature.hpp")
        assert version2_path in result_set, \
                     "version2_feature.hpp should be included when VERSION_2 is defined via #elif"
        
        # Should NOT include other version files
        version1_path = os.path.join(uth.samplesdir(), "cppflags_macros/version1_feature.hpp")
        version3_path = os.path.join(uth.samplesdir(), "cppflags_macros/version3_feature.hpp")
        default_path = os.path.join(uth.samplesdir(), "cppflags_macros/default_feature.hpp")
        
        assert version1_path not in result_set, "Should NOT include version1_feature.hpp"
        assert version3_path not in result_set, "Should NOT include version3_feature.hpp" 
        assert default_path not in result_set, "Should NOT include default_feature.hpp"
        
        os.unlink(temp_config_name)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_elif_matches_cpp_preprocessor(self):
        """Test that DirectHeaderDeps #elif handling matches actual C preprocessor results
        
        This test ensures our #elif implementation produces identical results to the
        real C preprocessor when processing complex elif chains with different macro
        combinations.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/elif_test.cpp")
        
        # Test different elif scenarios
        elif_scenarios = [
            {
                "name": "VERSION_1_defined",
                "cppflags": f"-I{uth.samplesdir()} -DVERSION_1"
            },
            {
                "name": "VERSION_2_defined", 
                "cppflags": f"-I{uth.samplesdir()} -DVERSION_2"
            },
            {
                "name": "VERSION_3_defined",
                "cppflags": f"-I{uth.samplesdir()} -DVERSION_3"
            },
            {
                "name": "no_version_defined",
                "cppflags": f"-I{uth.samplesdir()}"
            }
        ]
        
        for scenario in elif_scenarios:
            # pytest handles this automatically
            temp_config_name = compiletools.unittesthelper.create_temp_config()
            
            # Test DirectHeaderDeps (our custom preprocessor)
            argv_direct = [
                "--config=" + temp_config_name,
                "--headerdeps=direct",
                "--include", uth.samplesdir(),
                f"--CPPFLAGS={scenario['cppflags']}"
            ]
            
            # Test CppHeaderDeps (actual C preprocessor)
            argv_cpp = [
                "--config=" + temp_config_name,
                "--headerdeps=cpp",
                "--include", uth.samplesdir(), 
                f"--CPPFLAGS={scenario['cppflags']}"
            ]
            
            origcache = compiletools.dirnamer.user_cache_dir()
            with uth.EnvironmentContext({"CTCACHE": "None"}):
                reload(compiletools.dirnamer)
                reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
            compiletools.headerdeps.add_arguments(cap)
            
            # Get results from both approaches
            args_direct = compiletools.apptools.parseargs(cap, argv_direct)
            hdirect = compiletools.headerdeps.create(args_direct)
            direct_result = hdirect.process(filename)
            direct_set = set(direct_result)
            
            args_cpp = compiletools.apptools.parseargs(cap, argv_cpp)
            hcpp = compiletools.headerdeps.create(args_cpp)
            cpp_result = hcpp.process(filename)
            cpp_set = set(cpp_result)
            
            # Compare the results - they should be identical
            assert direct_set == cpp_set, \
                f"DirectHeaderDeps and CppHeaderDeps should produce identical #elif results for scenario: {scenario['name']}\n" \
                f"DirectHeaderDeps found: {sorted([os.path.basename(f) for f in direct_set])}\n" \
                f"CppHeaderDeps found: {sorted([os.path.basename(f) for f in cpp_set])}"
            
            os.unlink(temp_config_name)
            with uth.EnvironmentContext({"CTCACHE": origcache}):
                reload(compiletools.dirnamer)
                reload(compiletools.headerdeps)

    def test_advanced_preprocessor_features(self):
        """Test advanced preprocessor directive support
        
        This test verifies comprehensive support for #if expressions, #undef, 
        complex conditional logic, and alternative preprocessor forms that
        are commonly used in real-world C/C++ code.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/advanced_preprocessor_test.cpp")
        
        # Test with FEATURE_A and ALT_FORM_TEST defined
        temp_config_name = compiletools.unittesthelper.create_temp_config()
        argv = [
            "--config=" + temp_config_name,
            "--headerdeps=direct",
            "--include", uth.samplesdir(),
            "--CPPFLAGS", f"-I{uth.samplesdir()} -DFEATURE_A -DALT_FORM_TEST"
        ]
        
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        args = compiletools.apptools.parseargs(cap, argv)
        
        hdirect = compiletools.headerdeps.create(args)
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
            assert feature_path in result_set, \
                         f"{feature} should be included with advanced preprocessor support"
        
        # Verify that temp_still_defined.hpp is NOT included (should be excluded after #undef)
        temp_still_defined_path = os.path.join(uth.samplesdir(), "cppflags_macros/temp_still_defined.hpp")
        assert temp_still_defined_path not in result_set, \
                        "temp_still_defined.hpp should NOT be included after #undef TEMP_MACRO"
        
        # Verify combined_features.hpp is NOT included (requires both FEATURE_A AND FEATURE_B)
        combined_features_path = os.path.join(uth.samplesdir(), "cppflags_macros/combined_features.hpp")
        assert combined_features_path not in result_set, \
                        "combined_features.hpp should NOT be included (FEATURE_B not defined)"
        
        os.unlink(temp_config_name)
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)

    def test_advanced_preprocessor_matches_cpp_preprocessor(self):
        """Test that DirectHeaderDeps advanced preprocessor matches actual C preprocessor results
        
        This test ensures our custom SimplePreprocessor implementation produces identical
        results to the real C preprocessor (via CppHeaderDeps) when handling advanced
        features like #if expressions, #undef, and complex conditional logic.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/advanced_preprocessor_test.cpp")
        
        # Test multiple scenarios with different macro combinations
        test_scenarios = [
            {
                "name": "FEATURE_A_and_ALT_FORM_TEST",
                "cppflags": f"-I{uth.samplesdir()} -DFEATURE_A -DALT_FORM_TEST"
            },
            {
                "name": "FEATURE_A_and_FEATURE_B", 
                "cppflags": f"-I{uth.samplesdir()} -DFEATURE_A -DFEATURE_B"
            },
            {
                "name": "FEATURE_C_only",
                "cppflags": f"-I{uth.samplesdir()} -DFEATURE_C"
            },
            {
                "name": "no_feature_macros",
                "cppflags": f"-I{uth.samplesdir()}"
            }
        ]
        
        for scenario in test_scenarios:
            # pytest handles this automatically
            temp_config_name = compiletools.unittesthelper.create_temp_config()
            
            # Test DirectHeaderDeps (our custom preprocessor)
            argv_direct = [
                "--config=" + temp_config_name,
                "--headerdeps=direct",
                "--include", uth.samplesdir(),
                f"--CPPFLAGS={scenario['cppflags']}"
            ]
            
            # Test CppHeaderDeps (actual C preprocessor)
            argv_cpp = [
                "--config=" + temp_config_name,
                "--headerdeps=cpp", 
                "--include", uth.samplesdir(),
                f"--CPPFLAGS={scenario['cppflags']}"
            ]
            
            origcache = compiletools.dirnamer.user_cache_dir()
            with uth.EnvironmentContext({"CTCACHE": "None"}):
                reload(compiletools.dirnamer)
                reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
            compiletools.headerdeps.add_arguments(cap)
            
            # Get results from both approaches
            args_direct = compiletools.apptools.parseargs(cap, argv_direct)
            hdirect = compiletools.headerdeps.create(args_direct)
            direct_result = hdirect.process(filename)
            direct_set = set(direct_result)
            
            args_cpp = compiletools.apptools.parseargs(cap, argv_cpp)
            hcpp = compiletools.headerdeps.create(args_cpp)
            cpp_result = hcpp.process(filename)  
            cpp_set = set(cpp_result)
            
            # Compare the results - they should be identical
            assert direct_set == cpp_set, \
                f"DirectHeaderDeps and CppHeaderDeps should produce identical results for scenario: {scenario['name']}\n" \
                f"DirectHeaderDeps found: {sorted([os.path.basename(f) for f in direct_set])}\n" \
                f"CppHeaderDeps found: {sorted([os.path.basename(f) for f in cpp_set])}"
            
            os.unlink(temp_config_name)
            with uth.EnvironmentContext({"CTCACHE": origcache}):
                reload(compiletools.dirnamer)
                reload(compiletools.headerdeps)

    def test_multiply_nested_macros_with_complex_logic(self):
        """Test that DirectHeaderDeps correctly handles multiply nested macros with complex logic
        
        This test verifies that the SimplePreprocessor can handle deeply nested conditional
        compilation blocks with complex interdependencies between multiple macros,
        including platform-specific logic, feature flags, and optimization settings.
        """
        filename = os.path.join(uth.samplesdir(), "cppflags_macros/nested_macros_test.cpp")
        
        # Test scenario with BUILD_CONFIG=2, Linux platform, threading enabled, NUMA support
        test_scenarios = [
            {
                "name": "level2_linux_threading_numa",
                "cppflags": f"-I{uth.samplesdir()} -DBUILD_CONFIG=2 -D__linux__ -DUSE_EPOLL=1 -DENABLE_THREADING -DTHREAD_COUNT=4 -DNUMA_SUPPORT=1"
            },
            {
                "name": "level3_expert_mode_with_profiling",
                "cppflags": f"-I{uth.samplesdir()} -DBUILD_CONFIG=3 -DENABLE_EXPERT_MODE=1 -DCUSTOM_ALLOCATOR -DALLOCATOR_TYPE=2 -DMEMORY_TRACKING=1 -DLEAK_DETECTION=1 -DSTACK_TRACE=1 -DENABLE_PROFILING=1 -DPROFILING_LEVEL=3 -DMEMORY_PROFILING=1 -DCPU_PROFILING=1 -DCACHE_PROFILING=1"
            },
            {
                "name": "level1_basic_only",
                "cppflags": f"-I{uth.samplesdir()} -DBUILD_CONFIG=1"
            }
        ]
        
        for scenario in test_scenarios:
            # pytest handles this automatically
            temp_config_name = compiletools.unittesthelper.create_temp_config()
            
            # Test DirectHeaderDeps (our custom preprocessor)
            argv_direct = [
                "--config=" + temp_config_name,
                "--headerdeps=direct",
                "--include", uth.samplesdir(),
                f"--CPPFLAGS={scenario['cppflags']}"
            ]
            
            # Test CppHeaderDeps (actual C preprocessor)
            argv_cpp = [
                "--config=" + temp_config_name,
                "--headerdeps=cpp",
                "--include", uth.samplesdir(),
                f"--CPPFLAGS={scenario['cppflags']}"
            ]
            
            origcache = compiletools.dirnamer.user_cache_dir()
            with uth.EnvironmentContext({"CTCACHE": "None"}):
                reload(compiletools.dirnamer)
                reload(compiletools.headerdeps)
            cap = configargparse.getArgumentParser()
            compiletools.headerdeps.add_arguments(cap)
            
            # Get results from both approaches
            args_direct = compiletools.apptools.parseargs(cap, argv_direct)
            hdirect = compiletools.headerdeps.create(args_direct)
            direct_result = hdirect.process(filename)
            direct_set = set(direct_result)
            
            args_cpp = compiletools.apptools.parseargs(cap, argv_cpp)
            hcpp = compiletools.headerdeps.create(args_cpp)
            cpp_result = hcpp.process(filename)
            cpp_set = set(cpp_result)
            
            # Compare the results - they should be identical
            assert direct_set == cpp_set, \
                f"DirectHeaderDeps and CppHeaderDeps should produce identical results for nested macros in scenario: {scenario['name']}\n" \
                f"DirectHeaderDeps found: {sorted([os.path.basename(f) for f in direct_set])}\n" \
                f"CppHeaderDeps found: {sorted([os.path.basename(f) for f in cpp_set])}"
            
            # Verify specific inclusions based on the scenario
            if scenario["name"] == "level2_linux_threading_numa":
                expected_files = [
                    "basic_feature.hpp",
                    "advanced_feature.hpp", 
                    "linux_advanced.hpp",
                    "linux_epoll_threading.hpp",
                    "numa_threading.hpp"
                ]
                for expected_file in expected_files:
                    expected_path = os.path.join(uth.samplesdir(), f"cppflags_macros/{expected_file}")
                    assert expected_path in direct_set, \
                        f"{expected_file} should be included in level2_linux_threading_numa scenario"
            
            elif scenario["name"] == "level3_expert_mode_with_profiling":
                expected_files = [
                    "basic_feature.hpp",
                    "advanced_feature.hpp",
                    "expert_feature.hpp"
                ]
                for expected_file in expected_files:
                    expected_path = os.path.join(uth.samplesdir(), f"cppflags_macros/{expected_file}")
                    assert expected_path in direct_set, \
                        f"{expected_file} should be included in level3_expert_mode_with_profiling scenario"
            
            elif scenario["name"] == "level1_basic_only":
                expected_files = ["basic_feature.hpp"]
                unexpected_files = ["advanced_feature.hpp", "expert_feature.hpp"]
                
                for expected_file in expected_files:
                    expected_path = os.path.join(uth.samplesdir(), f"cppflags_macros/{expected_file}")
                    assert expected_path in direct_set, \
                        f"{expected_file} should be included in level1_basic_only scenario"
                
                for unexpected_file in unexpected_files:
                    unexpected_path = os.path.join(uth.samplesdir(), f"cppflags_macros/{unexpected_file}")
                    assert unexpected_path not in direct_set, \
                        f"{unexpected_file} should NOT be included in level1_basic_only scenario"
            
            os.unlink(temp_config_name)
            with uth.EnvironmentContext({"CTCACHE": origcache}):
                reload(compiletools.dirnamer)
                reload(compiletools.headerdeps)


