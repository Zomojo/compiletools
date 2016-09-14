from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import unittest
import shutil

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload

import ct.cppdeps
import ct.unittesthelper as uth

def _reload_ct(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the ct.* modules
    """
    os.environ['CTCACHE'] = cache_home
    reload(ct.headerdeps)
    reload(ct.cppdeps)

class TestCPPDeps(unittest.TestCase):

    def setUp(self):
        uth.reset()        

    # This test needs to run in buffered mode. 
    #You can set buffer through unit2 command line flag -b, --buffer 
    # or in unittest.main options.
    @unittest.skipIf(not hasattr(sys.stdout, "getvalue"), "Skipping test since not in buffer mode")
    def test_cppdeps(self):
        tempdir = '/dev/shm/test.ct.cppdeps'
        _reload_ct(tempdir)
        uth.reset()
        ct.cppdeps.main(['samples/numbers/test_direct_include.cpp'])
        output = sys.stdout.getvalue().strip().split()
        expected_output = [
            "/data/home/geoff/Cake/samples/numbers/get_double.hpp",
            "/data/home/geoff/Cake/samples/numbers/get_int.hpp",
            "/data/home/geoff/Cake/samples/numbers/get_numbers.hpp"]
        self.assertEquals(expected_output.sort(), output.sort())
        shutil.rmtree(tempdir)

    def tearDown(self):
        uth.reset()


if __name__ == '__main__':
    unittest.main()
