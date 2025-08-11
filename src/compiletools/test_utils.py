import sys
import os
import configargparse

import compiletools.unittesthelper as uth
import compiletools.utils as utils


class TestIsFuncs:
    def test_isheader(self):
        assert utils.isheader("myfile.h")
        assert utils.isheader("/home/user/myfile.h")
        assert utils.isheader("myfile.H")
        assert utils.isheader("My File.H")
        assert utils.isheader("myfile.inl")
        assert utils.isheader("myfile.hh")
        assert utils.isheader("myfile.hxx")
        assert utils.isheader("myfile.hpp")
        assert utils.isheader("/home/user/myfile.hpp")
        assert utils.isheader("myfile.with.dots.hpp")
        assert utils.isheader("/home/user/myfile.with.dots.hpp")
        assert utils.isheader("myfile_underscore.h")
        assert utils.isheader("myfile-hypen.h")
        assert utils.isheader("myfile.h")

        assert not utils.isheader("myfile.c")
        assert not utils.isheader("myfile.cc")
        assert not utils.isheader("myfile.cpp")
        assert not utils.isheader("/home/user/myfile")

    def test_issource(self):
        assert utils.issource("myfile.c")
        assert utils.issource("myfile.cc")
        assert utils.issource("myfile.cpp")
        assert utils.issource("/home/user/myfile.cpp")
        assert utils.issource("/home/user/myfile.with.dots.cpp")
        assert utils.issource("myfile.C")
        assert utils.issource("myfile.CC")
        assert utils.issource("My File.c")
        assert utils.issource("My File.cpp")
        assert utils.issource("myfile.cxx")

        assert not utils.issource("myfile.h")
        assert not utils.issource("myfile.hh")
        assert not utils.issource("myfile.hpp")
        assert not utils.issource("/home/user/myfile.with.dots.hpp")


class TestImpliedSource:
    def test_implied_source_nonexistent_file(self):
        assert utils.implied_source("nonexistent_file.hpp") is None

    def test_implied_source(self):
        relativefilename = "dottypaths/d2/d2.hpp"
        basename = os.path.splitext(relativefilename)[0]
        expected = os.path.join(uth.samplesdir(), basename + ".cpp")
        result = utils.implied_source(os.path.join(uth.samplesdir(), relativefilename))
        assert expected == result


class TestOrderedUnique:
    def test_ordered_unique_basic(self):
        result = utils.ordered_unique([5, 4, 3, 2, 1])
        assert len(result) == 5
        assert 3 in result
        assert 6 not in result
        assert result == [5, 4, 3, 2, 1]

    def test_ordered_unique_duplicates(self):
        # Test deduplication while preserving order
        result = utils.ordered_unique(["five", "four", "three", "two", "one", "four", "two"])
        expected = ["five", "four", "three", "two", "one"]
        assert result == expected
        assert len(result) == 5
        assert "four" in result
        assert "two" in result

    def test_ordered_union(self):
        # Test union functionality
        list1 = ["a", "b", "c"]
        list2 = ["c", "d", "e"]
        list3 = ["e", "f", "g"]
        result = utils.ordered_union(list1, list2, list3)
        expected = ["a", "b", "c", "d", "e", "f", "g"]
        assert result == expected

    def test_ordered_difference(self):
        # Test difference functionality
        source = ["a", "b", "c", "d", "e"]
        subtract = ["b", "d"]
        result = utils.ordered_difference(source, subtract)
        expected = ["a", "c", "e"]
        assert result == expected


