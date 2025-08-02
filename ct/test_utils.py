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
        self.assertIsNone(utils.implied_source("nonexistent_file.hpp"))

    def test_implied_source(self):
        relativefilename = "dottypaths/d2/d2.hpp"
        basename = os.path.splitext(relativefilename)[0]
        expected = os.path.join(uth.samplesdir(), basename + ".cpp")
        result = utils.implied_source(os.path.join(uth.samplesdir(), relativefilename))
        self.assertEqual(expected, result)


class TestOrderedUnique(unittest.TestCase):
    def test_ordered_unique_basic(self):
        result = utils.ordered_unique([5, 4, 3, 2, 1])
        self.assertEqual(len(result), 5)
        self.assertIn(3, result)
        self.assertNotIn(6, result)
        self.assertEqual(result, [5, 4, 3, 2, 1])

    def test_ordered_unique_duplicates(self):
        # Test deduplication while preserving order
        result = utils.ordered_unique(["five", "four", "three", "two", "one", "four", "two"])
        expected = ["five", "four", "three", "two", "one"]
        self.assertEqual(result, expected)
        self.assertEqual(len(result), 5)
        self.assertIn("four", result)
        self.assertIn("two", result)

    def test_ordered_union(self):
        # Test union functionality
        list1 = ["a", "b", "c"]
        list2 = ["c", "d", "e"]
        list3 = ["e", "f", "g"]
        result = utils.ordered_union(list1, list2, list3)
        expected = ["a", "b", "c", "d", "e", "f", "g"]
        self.assertEqual(result, expected)

    def test_ordered_difference(self):
        # Test difference functionality
        source = ["a", "b", "c", "d", "e"]
        subtract = ["b", "d"]
        result = utils.ordered_difference(source, subtract)
        expected = ["a", "c", "e"]
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
