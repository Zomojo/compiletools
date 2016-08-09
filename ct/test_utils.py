from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import unittest
import configargparse

import ct.unittesthelper as uth
import ct.utils as utils


class TestIsFuncs(unittest.TestCase):

    def test_isheader(self):
        self.assertTrue(utils.isheader("myfile.h"))
        self.assertTrue(utils.isheader("/home/user/myfile.h"))
        self.assertTrue(utils.isheader("myfile.H"))
        self.assertTrue(utils.isheader("My File.H"))
        self.assertTrue(utils.isheader("myfile.inl"))
        self.assertTrue(utils.isheader("myfile.hh"))
        self.assertTrue(utils.isheader("myfile.hxx"))
        self.assertTrue(utils.isheader("myfile.hpp"))
        self.assertTrue(utils.isheader("/home/user/myfile.hpp"))
        self.assertTrue(utils.isheader("myfile.with.dots.hpp"))
        self.assertTrue(utils.isheader("/home/user/myfile.with.dots.hpp"))
        self.assertTrue(utils.isheader("myfile_underscore.h"))
        self.assertTrue(utils.isheader("myfile-hypen.h"))
        self.assertTrue(utils.isheader("myfile.h"))

        self.assertFalse(utils.isheader("myfile.c"))
        self.assertFalse(utils.isheader("myfile.cc"))
        self.assertFalse(utils.isheader("myfile.cpp"))
        self.assertFalse(utils.isheader("/home/user/myfile"))

    def test_issource(self):
        self.assertTrue(utils.issource("myfile.c"))
        self.assertTrue(utils.issource("myfile.cc"))
        self.assertTrue(utils.issource("myfile.cpp"))
        self.assertTrue(utils.issource("/home/user/myfile.cpp"))
        self.assertTrue(utils.issource("/home/user/myfile.with.dots.cpp"))
        self.assertTrue(utils.issource("myfile.C"))
        self.assertTrue(utils.issource("myfile.CC"))
        self.assertTrue(utils.issource("My File.c"))
        self.assertTrue(utils.issource("My File.cpp"))
        self.assertTrue(utils.issource("myfile.cxx"))

        self.assertFalse(utils.issource("myfile.h"))
        self.assertFalse(utils.issource("myfile.hh"))
        self.assertFalse(utils.issource("myfile.hpp"))
        self.assertFalse(utils.issource("/home/user/myfile.with.dots.hpp"))


class TestImpliedSource(unittest.TestCase):

    def test_implied_source_nonexistent_file(self):
        self.assertIsNone(utils.implied_source('nonexistent_file.hpp'))

    def test_implied_source(self):
        relativefilename = 'dottypaths/d2/d2.hpp'
        basename = os.path.splitext(relativefilename)[0]
        expected = os.path.join(uth.samplesdir(), basename + '.cpp')
        result = utils.implied_source(
            os.path.join(
                uth.samplesdir(),
                relativefilename))
        self.assertEqual(expected, result)

class TestOrderedSet(unittest.TestCase):

    def test_initialization(self):
        s1 = utils.OrderedSet([5, 4, 3, 2, 1])
        self.assertEqual(len(s1), 5)
        self.assertTrue(3 in s1)
        self.assertFalse(6 in s1)

    def test_add_uniqueness(self):
        # Create and test expected elements
        s1 = utils.OrderedSet(["five", "four", "three", "two", "one"])
        self.assertEqual(len(s1), 5)
        self.assertIn("four", s1)
        self.assertIn("two", s1)

        # Re-add existing elements and check that nothing occured
        s1.add("four")
        s1.add("two")
        self.assertEqual(len(s1), 5)
        self.assertIn("four", s1)
        self.assertIn("two", s1)

        # Add a new entry and verify it is at the end
        s1.add("newentry")
        self.assertEqual(len(s1), 6)
        self.assertIn("newentry", s1)
        s2 = utils.OrderedSet(
            ["five", "four", "three", "two", "one", "newentry"])
        self.assertEqual(s1, s2)


if __name__ == '__main__':
    unittest.main()
