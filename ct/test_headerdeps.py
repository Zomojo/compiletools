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

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
