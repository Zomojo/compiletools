import os
import sys
import shutil
import tempfile
import io
from contextlib import redirect_stdout

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload

import compiletools.cppdeps
import compiletools.unittesthelper as uth


def _reload_ct_with_cache(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the compiletools.* modules
    """
    with uth.EnvironmentContext({"CTCACHE": cache_home}):
        reload(compiletools.headerdeps)
        reload(compiletools.cppdeps)
        return cache_home


def test_cppdeps():
    uth.reset()
    
    with uth.TempDirContext() as ctx:
        # Copy config files to test environment so cppdeps can find its configuration
        ct_conf_dir = os.path.join(os.getcwd(), "ct.conf.d")
        os.makedirs(ct_conf_dir, exist_ok=True)
        
        # Copy the essential config files from the real config directory
        src_config_dir = uth.ctconfdir()
        for config_file in ["ct.conf", "gcc.debug.conf"]:
            src_path = os.path.join(src_config_dir, config_file)
            dst_path = os.path.join(ct_conf_dir, config_file)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
        
        with uth.EnvironmentContext({"CTCACHE": os.getcwd()}):
            reload(compiletools.headerdeps)
            reload(compiletools.cppdeps)
            uth.reset()
            
            output_buffer = io.StringIO()
            with redirect_stdout(output_buffer):
                compiletools.cppdeps.main(
                    [os.path.join(uth.samplesdir(), "numbers/test_direct_include.cpp")]
                )
            
            output = output_buffer.getvalue().strip().split()
            expected_output = [
                os.path.join(uth.samplesdir(), "numbers/get_double.hpp"),
                os.path.join(uth.samplesdir(), "numbers/get_int.hpp"),
                os.path.join(uth.samplesdir(), "numbers/get_numbers.hpp"),
            ]
            assert sorted(expected_output) == sorted(output)
        uth.reset()


