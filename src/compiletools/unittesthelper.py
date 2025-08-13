import configargparse
import os
import contextlib
import shutil
from io import open
import tempfile
import textwrap
from pathlib import Path
import compiletools.apptools

# The abbreviation "uth" is often used for this "unittesthelper"


def reset():
    delete_existing_parsers()
    compiletools.apptools.resetcallbacks()


def delete_existing_parsers():
    """The singleton parsers supplied by configargparse
    don't play well with the unittest framework.
    This function will delete them so you are
    starting with a clean slate
    """
    configargparse._parsers = {}


def ctdir():
    return os.path.dirname(os.path.realpath(__file__))


def cakedir():
    return os.path.realpath(os.path.join(ctdir(), ".."))


def samplesdir():
    return os.path.realpath(os.path.join(ctdir(), "samples"))


def ctconfdir():
    return os.path.realpath(os.path.join(ctdir(), "ct.conf.d"))


def create_temp_config(tempdir=None, filename=None, extralines=[]):
    """User is responsible for removing the config file when
    they are finished
    """
    try:
        CC = os.environ["CC"]
        CXX = os.environ["CXX"]
    except KeyError:
        CC = "gcc"
        CXX = "g++"

    if not filename:
        tf_handle, filename = tempfile.mkstemp(suffix=".conf", text=True, dir=tempdir)

    with open(filename, "w") as ff:
        ff.write("ID=GNU\n")
        ff.write("CC=" + CC + "\n")
        ff.write("CXX=" + CXX + "\n")
        ff.write('CPPFLAGS="-std=c++20"\n')
        for line in extralines:
            ff.write(line + "\n")

    return filename


def create_temp_ct_conf(tempdir, defaultvariant="debug", extralines=[]):
    """User is responsible for removing the config file when
    they are finished
    """
    with open(os.path.join(tempdir, "ct.conf"), "w") as ff:
        # ff.write('CTCACHE = ' + os.path.join(tempdir,'ct-unittest-cache' + '\n'))
        # ff.write('CTCACHE = None' + '\n')
        ff.write(" ".join(["variant =", defaultvariant, "\n"]))
        ff.write("variantaliases = {'dbg':'foo.debug', 'rls':'foo.release'}\n")
        ff.write("exemarkers = [main]" + "\n")
        ff.write("testmarkers = unit_test.hpp" + "\n")
        for line in extralines:
            ff.write(line + "\n")


class TempDirectoryContext:
    """Context manager for temporary directories with optional directory changing.
    
    Unifies all temp directory patterns into a single, flexible context manager.
    """
    
    def __init__(self, change_dir=True, prefix=None, suffix=None, dir=None):
        """
        Args:
            change_dir: If True, changes to the temp directory (default: True for backward compatibility)
            prefix: Prefix for temp directory name
            suffix: Suffix for temp directory name  
            dir: Parent directory for temp directory
        """
        self.change_dir = change_dir
        self.prefix = prefix
        self.suffix = suffix 
        self.dir = dir
        self._tmpdir = None
        self._origdir = None
        
    def __enter__(self):
        if self.change_dir:
            self._origdir = os.getcwd()
        
        self._tmpdir = tempfile.mkdtemp(prefix=self.prefix, suffix=self.suffix, dir=self.dir)
        
        if self.change_dir:
            os.chdir(self._tmpdir)
        
        return self._tmpdir
        
    def __exit__(self, exc_type, exc_value, traceback):
        if self.change_dir and self._origdir:
            os.chdir(self._origdir)
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)


# Backward compatibility aliases
class TempDirContext(TempDirectoryContext):
    """Backward compatibility: temp directory with directory change."""
    def __init__(self):
        super().__init__(change_dir=True)
    
    def __enter__(self):
        super().__enter__()
        return self  # Original returned self, not tmpdir


class TempDirContextNoChange(TempDirectoryContext):
    """Backward compatibility: temp directory without directory change."""
    def __init__(self, prefix=None, suffix=None, dir=None):
        super().__init__(change_dir=False, prefix=prefix, suffix=suffix, dir=dir)


class TempDirContextWithChange(TempDirectoryContext):
    """Backward compatibility: temp directory with directory change."""
    def __init__(self, prefix=None, suffix=None, dir=None):
        super().__init__(change_dir=True, prefix=prefix, suffix=suffix, dir=dir)


@contextlib.contextmanager
def DirectoryContext(target_dir):
    """Context manager for changing to a specific directory temporarily."""
    origdir = os.getcwd()
    try:
        os.chdir(target_dir)
        yield target_dir
    finally:
        os.chdir(origdir)


@contextlib.contextmanager  
def EnvironmentContext(env_vars):
    """Context manager for temporarily setting environment variables.
    
    Args:
        env_vars: Dictionary of environment variables to set
    """
    original_values = {}
    
    # Save original values and set new ones
    for key, value in env_vars.items():
        if value:  # Only set non-empty values
            original_values[key] = os.getenv(key)
            os.environ[key] = value
    
    try:
        yield
    finally:
        # Restore original values
        for key in env_vars:
            if key in original_values:
                if original_values[key] is not None:
                    os.environ[key] = original_values[key]
                else:
                    os.environ.pop(key, None)  # Remove if it wasn't set before


@contextlib.contextmanager
def ParserContext():
    """Context manager for temporarily resetting configargparse state."""
    saved_parsers = configargparse._parsers.copy()
    delete_existing_parsers()
    compiletools.apptools.resetcallbacks()
    
    try:
        yield
    finally:
        configargparse._parsers = saved_parsers
        compiletools.apptools.resetcallbacks()


@contextlib.contextmanager
def TempConfigContext(tempdir=None, filename=None, extralines=None):
    """Context manager for temporary config files with automatic cleanup.
    
    Args:
        tempdir: Directory to create temp config in (default: system temp)
        filename: Specific filename to use (default: auto-generated)
        extralines: Additional config lines to add
    """
    config_path = create_temp_config(
        tempdir=tempdir,
        filename=filename,
        extralines=extralines or []
    )
    try:
        yield config_path
    finally:
        if config_path and os.path.exists(config_path):
            os.unlink(config_path)


@contextlib.contextmanager
def CompileToolsTestContext(ctcache=None, reload_modules=None, config_extralines=None):
    """A higher-level context manager for compiletools tests.
    
    This combines the most common testing patterns:
    - TempDirContextWithChange: Creates temp directory and changes to it
    - TempConfigContext: Creates temporary config file with cleanup
    - EnvironmentContext: Sets CTCACHE environment variable  
    - ParserContext: Provides isolated parser state
    - Module reloads: Reloads specified modules to pick up changes
    
    Args:
        ctcache: CTCACHE value (default: "None" to disable caching)
        reload_modules: List of modules to reload (e.g., [compiletools.headerdeps])
        config_extralines: Additional lines to add to temp config file
        
    Returns:
        tuple: (tempdir, config_path) for use in test
    """
    import importlib
    
    reload_modules = reload_modules or []
    ctcache = ctcache or "None"
    
    with TempDirContextWithChange() as tempdir:
        with TempConfigContext(tempdir=tempdir, extralines=config_extralines) as config_path:
            with EnvironmentContext({"CTCACHE": ctcache}):
                with ParserContext():
                    # Reload specified modules
                    for module in reload_modules:
                        importlib.reload(module)
                    
                    yield (tempdir, config_path)


def run_headerdeps(kind, filename, cppflags=None, cache="None", extra_args=None):
    """Helper function to run headerdeps analysis and return result set.
    
    Eliminates the repetitive pattern of:
    - Creating config
    - Setting up environment  
    - Creating parser
    - Running analysis
    - Converting to set
    
    Args:
        kind: HeaderDeps kind ("direct" or "cpp")
        filename: File to analyze
        cppflags: Optional CPPFLAGS string
        cache: CTCACHE value (default "None")
        extra_args: Additional command line arguments
        
    Returns:
        set: Set of header dependencies found
    """
    with TempConfigContext() as temp_config_name:
        argv = [
            "--config=" + temp_config_name,
            f"--headerdeps={kind}",
            "--include", samplesdir(),
        ]
        
        if cppflags:
            argv.extend(["--CPPFLAGS", f"-I{samplesdir()} {cppflags}"])
            
        if extra_args:
            argv.extend(extra_args)
            
        with HeaderDepsTestContext(argv, cache=cache) as hdeps:
            return set(hdeps.process(filename))


@contextlib.contextmanager
def HeaderDepsTestContext(argv, cache="None", config_extralines=None):
    """Context manager for headerdeps tests that handles the common boilerplate pattern.
    
    Encapsulates the repeated pattern of:
    - Save original cache
    - Set CTCACHE environment 
    - Reload modules
    - Create and configure parser
    - Parse arguments
    - Create headerdeps object
    - Restore cache on exit
    
    Args:
        argv: Command line arguments for headerdeps
        cache: CTCACHE value (default: "None" to disable caching)
        config_extralines: Additional config file lines if needed
        
    Yields:
        headerdeps: Configured HeaderDeps object ready for testing
    """
    import configargparse
    import compiletools.dirnamer
    import compiletools.headerdeps
    import compiletools.apptools
    from importlib import reload
    
    # Save original cache setting
    origcache = compiletools.dirnamer.user_cache_dir()
    
    try:
        # Set up test environment
        with EnvironmentContext({"CTCACHE": cache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)
            
            # Create and configure parser
            cap = configargparse.getArgumentParser()
            compiletools.headerdeps.add_arguments(cap)
            args = compiletools.apptools.parseargs(cap, argv)
            
            # Create headerdeps object
            headerdeps = compiletools.headerdeps.create(args)
            yield headerdeps
            
    finally:
        # Restore original cache
        with EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)


@contextlib.contextmanager
def CPPDepsTestContext(variant_configs=None, reload_modules=None, ctcache=None):
    """A context manager for tests that call main() functions requiring configuration.
    
    Currently used by test_cppdeps. This combines:
    - TempDirContext: Creates temp directory and changes to it
    - Config file setup: Copies ct.conf and specified variant config files
    - EnvironmentContext: Sets CTCACHE to current directory or custom value
    - Module reloads: Reloads specified modules to pick up new cache
    - Parser cleanup: Resets configargparse state
    
    Args:
        variant_configs: List of config files to copy (e.g., ['gcc.debug.conf'])
        reload_modules: List of modules to reload (e.g., [compiletools.headerdeps])
        ctcache: Override CTCACHE value (default: current working directory, can be "None" to disable)
    """
    import importlib
    
    variant_configs = variant_configs or ['gcc.debug.conf']
    reload_modules = reload_modules or []
    
    # Use our refactored context managers in a nested fashion
    with TempDirContext() as temp_context:
        # Copy config files to test environment
        ct_conf_dir = os.path.join(os.getcwd(), "ct.conf.d")
        os.makedirs(ct_conf_dir, exist_ok=True)
        
        src_config_dir = ctconfdir()
        # Always copy ct.conf
        config_files = ['ct.conf'] + variant_configs
        for config_file in config_files:
            src_path = os.path.join(src_config_dir, config_file)
            dst_path = os.path.join(ct_conf_dir, config_file)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
        
        # Set up environment with CTCACHE
        ctcache_value = ctcache if ctcache is not None else os.getcwd()
        with EnvironmentContext({"CTCACHE": ctcache_value}):
            # Reload specified modules
            for module in reload_modules:
                importlib.reload(module)
                
            # Reset parser state
            reset()
            
            try:
                yield temp_context
            finally:
                reset()


def headerdeps_result(filename, kind="direct", cppflags=None, include=None, extra_args=None, cache="None"):
    """Return set of headers for given filename using specified headerdeps kind.
    Provides full isolation (TempConfig, Environment, Parser).
    Args:
        filename: Path to file to analyse (can be relative; will be realpathed by headerdeps)
        kind: 'direct' or 'cpp'
        cppflags: Raw CPPFLAGS string (pass full string, do NOT auto-prepend -I)
        include: Directory to use with --include (defaults to samplesdir())
        extra_args: List of extra CLI args (e.g., ["--something", "value"])
        cache: CTCACHE value (default 'None' for disabling disk cache)
    Returns: set of header paths
    """
    include = include or samplesdir()
    if extra_args is None:
        extra_args = []
    from importlib import reload
    import compiletools.headerdeps
    import compiletools.dirnamer
    
    # Save original cache setting
    origcache = compiletools.dirnamer.user_cache_dir()
    
    try:
        # Create config with custom CPPFLAGS if needed
        config_extralines = []
        if cppflags:
            config_extralines.append(f'CPPFLAGS="-std=c++20 {cppflags}"')
        
        with TempConfigContext(extralines=config_extralines) as temp_config_name:
            with EnvironmentContext({"CTCACHE": cache}):
                reload(compiletools.dirnamer)
                reload(compiletools.headerdeps)
                
                # Create fresh parser with complete isolation
                with ParserContext():
                    cap = configargparse.ArgumentParser(
                        description="HeaderDeps test parser",
                        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
                        args_for_setting_config_path=["-c", "--config"],
                        ignore_unknown_config_file_keys=False,
                    )
                    compiletools.headerdeps.add_arguments(cap)
                    argv = ["--config=" + temp_config_name, f"--headerdeps={kind}", "--include", include] + extra_args
                    args = compiletools.apptools.parseargs(cap, argv)
                    h = compiletools.headerdeps.create(args)
                    return set(h.process(filename))
    finally:
        # Restore original cache
        with EnvironmentContext({"CTCACHE": origcache}):
            reload(compiletools.dirnamer)
            reload(compiletools.headerdeps)


def compare_headerdeps_kinds(filename, cppflags=None, kinds=("direct", "cpp"), include=None, extra_args=None, cache="None", scenario_name=None):
    """Run multiple headerdeps kinds and assert their results match (if >1 kinds).
    Returns dict kind->set.
    scenario_name included in assertion message if provided.
    """
    results = {}
    for kind in kinds:
        results[kind] = headerdeps_result(filename, kind=kind, cppflags=cppflags, include=include, extra_args=extra_args, cache=cache)
    if len(kinds) > 1:
        baseline = results[kinds[0]]
        for kind in kinds[1:]:
            if results[kind] != baseline:
                raise AssertionError(
                    f"HeaderDeps results differ{(' for ' + scenario_name) if scenario_name else ''}: "
                    f"{kinds[0]}={sorted(os.path.basename(f) for f in baseline)} vs "
                    f"{kind}={sorted(os.path.basename(f) for f in results[kind])}"
                )
    return results


def write_sources(mapping, target_dir=None):
    """Central utility for temp source file creation.
    
    Args:
        mapping: Dictionary of {relative_path: content} for files to create
        target_dir: Directory to create files in (defaults to current directory)
        
    Returns:
        Dictionary of {relative_path: Path} for created files
        
    Usage:
        files = uth.write_sources({
            "main.cpp": '''
                #include <iostream>
                int main() { return 0; }
            ''',
            "extra.hpp": '''
                #pragma once
                void helper();
            '''
        })
        # files["main.cpp"] is a Path object to the created file
        
        # Or write to specific directory:
        files = uth.write_sources(mapping, target_dir="/tmp/test")
    """
    if target_dir is None:
        base_path = Path(os.getcwd())
    else:
        base_path = Path(target_dir)
        
    paths = {}
    for rel, text in mapping.items():
        p = base_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text).lstrip())
        paths[rel] = p
    return paths
