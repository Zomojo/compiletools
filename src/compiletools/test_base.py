import os
import configargparse
import compiletools.unittesthelper as uth
import compiletools.uth_reload as uthr
import compiletools.dirnamer
import compiletools.apptools
import compiletools.headerdeps
import compiletools.magicflags
import compiletools.utils
import compiletools.configutils
import compiletools.wrappedos

from importlib import reload


class BaseCompileToolsTestCase:
    """Base test case with common setup/teardown for compiletools tests"""
    
    def setup_method(self):
        self._temp_context = uth.TempDirectoryContext(change_dir=True)
        self._tmpdir = self._temp_context.__enter__()
        uth.delete_existing_parsers()
        compiletools.apptools.resetcallbacks()
        
    def teardown_method(self):
        if hasattr(self, '_temp_context'):
            self._temp_context.__exit__(None, None, None)
        uth.delete_existing_parsers()
        compiletools.apptools.resetcallbacks()
        
    def _verify_one_exe_per_main(self, relativepaths, search_dir=None):
        """Common executable verification logic"""
        search_directory = search_dir or self._tmpdir
        actual_exes = set()
        for root, dirs, files in os.walk(search_directory):
            for ff in files:
                if compiletools.utils.isexecutable(os.path.join(root, ff)):
                    actual_exes.add(ff)

        expected_exes = {
            os.path.splitext(os.path.split(filename)[1])[0]
            for filename in relativepaths
            if compiletools.utils.issource(filename)
        }
        assert expected_exes == actual_exes

    def _get_sample_path(self, relative_path):
        """Helper to get full path for sample file"""
        return os.path.join(uth.samplesdir(), relative_path)


def create_magic_parser(extraargs=None, cache_home="None", tempdir=None):
    """Factory function for creating magic flag parsers"""
    if not extraargs:
        extraargs = []
    temp_config_name = uth.create_temp_config(tempdir)
    argv = ["--config=" + temp_config_name] + extraargs
    
    with uth.EnvironmentContext({"CTCACHE": cache_home}):
        reload(compiletools.dirnamer)
        reload(compiletools.apptools)
        reload(compiletools.headerdeps)
        reload(compiletools.magicflags)
    
    config_files = compiletools.configutils.config_files_from_variant(
        argv=argv, exedir=uth.cakedir()
    )
    
    # Check if parser already exists and use it, otherwise create new one
    try:
        cap = configargparse.getArgumentParser(
            description="TestMagicFlagsModule",
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            default_config_files=config_files,
            args_for_setting_config_path=["-c", "--config"],
            ignore_unknown_config_file_keys=True,
        )
    except ValueError:
        # Parser already exists, get it without parameters
        cap = configargparse.getArgumentParser()
        
    compiletools.apptools.add_common_arguments(cap)
    compiletools.dirnamer.add_arguments(cap)
    compiletools.headerdeps.add_arguments(cap)
    compiletools.magicflags.add_arguments(cap)
    args = compiletools.apptools.parseargs(cap, argv)
    headerdeps = compiletools.headerdeps.create(args)
    return compiletools.magicflags.create(args, headerdeps)

def compare_direct_cpp_magic(test_case, relativepath, tempdir=None):
    """Utility to test that DirectMagicFlags and CppMagicFlags produce identical results"""
    with uth.TempDirContext() as temp_ctx:
        if tempdir is not None:
            # If specific tempdir provided, copy current working dir content there
            os.chdir(tempdir)
            
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        
        # Test direct parser with isolated context
        with uth.ParserContext():
            magicparser_direct = create_magic_parser(["--magic", "direct"], tempdir=os.getcwd())
            result_direct = magicparser_direct.parse(realpath)
        
        # Test cpp parser with fresh isolated context
        with uth.ParserContext():
            magicparser_cpp = create_magic_parser(["--magic", "cpp"], tempdir=os.getcwd())
            result_cpp = magicparser_cpp.parse(realpath)
        
        # Results should be identical
        assert result_direct == result_cpp, \
                           f"DirectMagicFlags and CppMagicFlags gave different results for {relativepath}"


def compare_direct_cpp_headers(test_case, filename, extraargs=None):
    """Utility to test that DirectHeaderDeps and CppHeaderDeps produce identical results"""
    if extraargs is None:
        extraargs = []
    realpath = compiletools.wrappedos.realpath(filename)
    
    with uth.TempConfigContext() as temp_config_name:
        argv = ["--config=" + temp_config_name] + extraargs

        # Turn off diskcaching so that we can't just read up a prior result
        origcache = compiletools.dirnamer.user_cache_dir()
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            
            cap = configargparse.getArgumentParser()
            compiletools.headerdeps.add_arguments(cap)
            argvdirect = argv + ["--headerdeps=direct"]
            argsdirect = compiletools.apptools.parseargs(cap, argvdirect)

            argvcpp = argv + ["--headerdeps", "cpp"]
            argscpp = compiletools.apptools.parseargs(cap, argvcpp)

            hdirect = compiletools.headerdeps.create(argsdirect)
            hcpp = compiletools.headerdeps.create(argscpp)
            hdirectresult = hdirect.process(realpath)
            hcppresult = hcpp.process(realpath)
            assert set(hdirectresult) == set(hcppresult)
            
        with uth.EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
