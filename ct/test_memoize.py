from __future__ import print_function
from __future__ import unicode_literals

import time
import unittest

from ct.memoize import memoize


@memoize
def noargsfunc():
    time.sleep(0.51)
    return 42


class TestMemoize(unittest.TestCase):
    def test_noargsfunc(self):
        start = time.time()
        output = noargsfunc()
        self.assertEqual(42, output)
        self.assertTrue(time.time() - start > 0.5)

        start = time.time()
        output2 = noargsfunc()
        self.assertEqual(42, output2)
        self.assertTrue(time.time() - start < 0.1)


if __name__ == '__main__':
    unittest.main()
