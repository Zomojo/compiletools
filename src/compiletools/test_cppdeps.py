import os
import sys
import shutil
import tempfile
import io
from contextlib import redirect_stdout

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
    
    with uth.CPPDepsTestContext(
        variant_configs=['gcc.debug.conf'],
        reload_modules=[compiletools.headerdeps, compiletools.cppdeps]
    ):
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


