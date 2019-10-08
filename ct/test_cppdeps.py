import os
import sys
import unittest
import shutil
import tempfile

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
    os.environ["CTCACHE"] = cache_home
    reload(ct.headerdeps)
    reload(ct.cppdeps)


class TestCPPDeps(unittest.TestCase):
    def setUp(self):
        uth.reset()

    # This test needs to run in buffered mode.
    # You can set buffer through unit2 command line flag -b, --buffer
    # or in unittest.main options.
    @unittest.skipIf(
        not hasattr(sys.stdout, "getvalue"), "Skipping test since not in buffer mode"
    )
    def test_cppdeps(self):
        tempdir = tempfile.mkdtemp()
        _reload_ct(tempdir)
        uth.reset()
        ct.cppdeps.main(
            [os.path.join(uth.samplesdir(), "numbers/test_direct_include.cpp")]
        )
        output = sys.stdout.getvalue().strip().split()
        expected_output = [
            os.path.join(uth.samplesdir(), "numbers/get_double.hpp"),
            os.path.join(uth.samplesdir(), "numbers/get_int.hpp"),
            os.path.join(uth.samplesdir(), "numbers/get_numbers.hpp"),
        ]
        self.assertEquals(expected_output.sort(), output.sort())
        shutil.rmtree(tempdir)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main(module=__name__, buffer=True)
