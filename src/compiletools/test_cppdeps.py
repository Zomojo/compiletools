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


def _reload_ct(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the compiletools.* modules
    """
    os.environ["CTCACHE"] = cache_home
    reload(compiletools.headerdeps)
    reload(compiletools.cppdeps)


def test_cppdeps():
    uth.reset()
    
    tempdir = tempfile.mkdtemp()
    try:
        _reload_ct(tempdir)
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
    finally:
        shutil.rmtree(tempdir)
        uth.reset()


