from __future__ import print_function
from __future__ import unicode_literals

import unittest
import ct.apptools

class FakeNamespace(object):
    def __init__(self):
        self.n1 = 'v1_noquotes'
        self.n2 = '"v2_doublequotes"'
        self.n3 = "'v3_singlequotes'"
    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)

class TestFuncs(unittest.TestCase):

    def test_strip_quotes(self):
        fns = FakeNamespace()
        ct.apptools._strip_quotes(fns)
        self.assertEqual(fns.n1, 'v1_noquotes')
        self.assertEqual(fns.n2, 'v2_doublequotes')
        self.assertEqual(fns.n3, 'v3_singlequotes')

if __name__ == '__main__':
    unittest.main()
