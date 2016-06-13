from __future__ import print_function
import unittest
import os
import sys
import ct.cppdeps


class TestCPPDeps(unittest.TestCase):

    def test_something(self):
        ct.cppdeps.main([os.path.realpath('ct-cppdeps'),
                         '--filename',
                         'samples/numbers/test_direct_include.cpp'])
        if not hasattr(sys.stdout, "getvalue"):
            self.fail(
                "need to run in buffered mode. You can set buffer through unit2 command line flag -b, --buffer or in unittest.main options. The opposite is achieved through nosetest flag --nocapture.")
        # because stdout is an StringIO instance
        output = sys.stdout.getvalue().strip().split()
        expected_output = [
            "/data/home/geoff/Cake/samples/numbers/get_double.hpp",
            "/data/home/geoff/Cake/samples/numbers/get_int.hpp",
            "/data/home/geoff/Cake/samples/numbers/get_numbers.hpp"]
        self.assertEquals(expected_output.sort(), output.sort())

if __name__ == '__main__':
    unittest.main()
