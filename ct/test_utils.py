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

class TestVariant(unittest.TestCase):
    def test_extract_variant(self):
       self.assertEqual("abc",utils.extract_variant_from_argv("--variant=abc".split())) 
       self.assertEqual("abc",utils.extract_variant_from_argv("--variant abc".split())) 
       self.assertEqual("abc.123",utils.extract_variant_from_argv("-a -b -c --blah --variant=abc.123 -a -b -c --blah".split())) 
       self.assertEqual("abc.123",utils.extract_variant_from_argv("-a -b -c --blah --variant abc.123 -a -b -c --blah".split())) 

    def test_variant_with_hash(self):
        cap = configargparse.getArgumentParser()
        argv1 = "--variant=debug".split()
        args1 = utils.parseargs(cap,argv1)

        # Make a second, different, but logically equivalent argv
        argv2 = "--no-shorten --variant=debug".split()
        args2 = utils.parseargs(cap,argv2)
        self.assertEqual(args1,args2)

        # And a third ...
        argv3 = []
        args3 = utils.parseargs(cap,argv3)
        self.assertEqual(args1,args3)

        vwh1 = utils.variant_with_hash(args1, argv=argv1)
        vwh2 = utils.variant_with_hash(args2, argv=argv2)
        self.assertEqual(vwh1, vwh2)

        vwh3 = utils.variant_with_hash(args3, argv=argv3)
        self.assertEqual(vwh1, vwh3)

    def test_extract_variant_from_ct_conf(self):
        # Due to the search paths, this should not find any default variant
        variant = utils.extract_item_from_ct_conf(key='variant')
        self.assertEqual(None, variant)

        # Now it should find the one in the git repo ct.conf.d/ct.conf
        variant = utils.extract_item_from_ct_conf(key='variant', exedir=uth.cakedir())
        self.assertEqual("debug", variant)

    def test_extract_variant_from_blank_argv(self):
        variant = utils.extract_variant_from_argv(exedir=uth.cakedir())
        self.assertEqual("gcc.debug", variant)

class TestNamer(unittest.TestCase):

    @unittest.skipUnless(int(sys.version[0]) < 3, "The hardcoded hash value is only valid on python 2")
    def test_executable_pathname(self):
        cap = configargparse.getArgumentParser()
        argv = ['--no-git-root']
        utils.Namer.add_arguments(cap=cap)
        args = utils.parseargs(cap, argv)
        namer = utils.Namer(args)
        exename = namer.executable_pathname('/home/user/code/my.cpp')
        self.assertEqual(
            exename,
            os.path.join(
                os.getcwd(),
                'bin/debug.c9005649/home/user/code/my'))


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
