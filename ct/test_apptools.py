import unittest
import ct.apptools
import argparse  # Used for the parse_args test


class FakeNamespace(object):
    def __init__(self):
        self.n1 = "v1_noquotes"
        self.n2 = '"v2_doublequotes"'
        self.n3 = "'v3_singlequotes'"
        self.n4 = '''"''v4_lotsofquotes''"'''

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


class TestFuncs(unittest.TestCase):
    def test_strip_quotes(self):
        fns = FakeNamespace()
        ct.apptools._strip_quotes(fns)
        self.assertEqual(fns.n1, "v1_noquotes")
        self.assertEqual(fns.n2, "v2_doublequotes")
        self.assertEqual(fns.n3, "v3_singlequotes")
        self.assertEqual(fns.n4, "v4_lotsofquotes")

    def test_parse_args_strips_quotes(self):
        cmdline = [
            '--append-CPPFLAGS="-DNEWPROTOCOL -DV172"',
            '--append-CXXFLAGS="-DNEWPROTOCOL -DV172"',
        ]
        ap = argparse.ArgumentParser()
        ap.add_argument("--append-CPPFLAGS", action="append")
        ap.add_argument("--append-CXXFLAGS", action="append")
        args = ap.parse_args(cmdline)
        ct.apptools._strip_quotes(args)
        self.assertEqual(args.append_CPPFLAGS, ["-DNEWPROTOCOL -DV172"])
        self.assertEqual(args.append_CXXFLAGS, ["-DNEWPROTOCOL -DV172"])


if __name__ == "__main__":
    unittest.main()
