import configargparse
import os
import contextlib
import shutil
from io import open
import tempfile
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


class TempDirContext:
    def __enter__(self):
        self._origdir = os.getcwd()  # Save the current directory
        self._tmpdir = tempfile.mkdtemp()
        os.chdir(self._tmpdir)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self._origdir)  # Return to the original directory
        shutil.rmtree(self._tmpdir, ignore_errors=True)  # Cleanup the temporary directory


class EnvironmentContext:
    def __init__(self, flagsdict):
        self._flagsdict = flagsdict
        self._orig = {}

    def __enter__(self):
        for key, value in self._flagsdict.items():
            if value:
                self._orig[key] = os.getenv(key)
                os.environ[key] = value
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for key, value in self._orig.items():
            if value:
                os.environ[key] = value
            else:
                os.unsetenv(key)


class ParserContext:
    def __enter__(self):
        self._saved_parsers = configargparse._parsers.copy()
        delete_existing_parsers()
        compiletools.apptools.resetcallbacks()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        configargparse._parsers = self._saved_parsers
        compiletools.apptools.resetcallbacks()


class CPPDepsTestContext:
    """A context manager for tests that call main() functions requiring configuration.
    
    Currently used by test_cppdeps. This combines:
    - TempDirContext: Creates temp directory and changes to it
    - Config file setup: Copies ct.conf and specified variant config files
    - EnvironmentContext: Sets CTCACHE to current directory or custom value
    - Module reloads: Reloads specified modules to pick up new cache
    - Parser cleanup: Resets configargparse state
    
    TODO: Rename to CompileToolsTestContext once proven to work with more tests.
    """
    
    def __init__(self, variant_configs=None, reload_modules=None, ctcache=None):
        """
        Args:
            variant_configs: List of config files to copy (e.g., ['gcc.debug.conf'])
            reload_modules: List of modules to reload (e.g., [compiletools.headerdeps])
            ctcache: Override CTCACHE value (default: current working directory, can be "None" to disable)
        """
        self.variant_configs = variant_configs or ['gcc.debug.conf']
        self.reload_modules = reload_modules or []
        self.ctcache = ctcache
        self._temp_context = None
        self._env_context = None
        
    def __enter__(self):
        import importlib
        
        # Create temp directory and change to it
        self._temp_context = TempDirContext()
        self._temp_context.__enter__()
        
        # Copy config files to test environment
        ct_conf_dir = os.path.join(os.getcwd(), "ct.conf.d")
        os.makedirs(ct_conf_dir, exist_ok=True)
        
        src_config_dir = ctconfdir()
        # Always copy ct.conf
        config_files = ['ct.conf'] + self.variant_configs
        for config_file in config_files:
            src_path = os.path.join(src_config_dir, config_file)
            dst_path = os.path.join(ct_conf_dir, config_file)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
        
        # Set up environment with CTCACHE
        ctcache_value = self.ctcache if self.ctcache is not None else os.getcwd()
        self._env_context = EnvironmentContext({"CTCACHE": ctcache_value})
        self._env_context.__enter__()
        
        # Reload specified modules
        for module in self.reload_modules:
            importlib.reload(module)
            
        # Reset parser state
        reset()
        
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        if self._env_context:
            self._env_context.__exit__(exc_type, exc_value, traceback)
        if self._temp_context:
            self._temp_context.__exit__(exc_type, exc_value, traceback)
        reset()
