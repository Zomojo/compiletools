#!/usr/bin/env python
from __future__ import print_function
import subprocess
import sys
import configargparse


class HeaderHunter:

    """ Given a filename, create the header dependencies """

    def __init__(self):
        # Grab the global argparser and tell it we need a CPP (c preprocessor)
        # and CPPFLAGS
        cap = configargparse.getArgumentParser()
        cap.add(
            "-v",
            "--verbose",
            help="Output verbosity. Add more v's to make it more verbose",
            action="count",
            default=0)
        cap.add(
            "--CPP",
            help="C preprocessor",
            default="unsupplied_implies_use_CXX")
        cap.add("--CXX", help="C++ compiler", default="g++")
        cap.add(
            "--CPPFLAGS",
            help="C preprocessor flags",
            default="unsupplied_implies_use_CXXFLAGS")
        cap.add(
            "--CXXFLAGS",
            help="C++ compiler flags",
            default="-I . -fPIC -g -Wall")
        myargs = cap.parse_known_args()
        self.cpp = myargs[0].CPP
        self.cppflags = myargs[0].CPPFLAGS
        self.verbose = myargs[0].verbose

        # If C PreProcessor variables are not set but CXX ones are set then
        # just use the CXX equivalents
        if self.cpp is "unsupplied_implies_use_CXX":
            self.cpp = myargs[0].CXX
        if self.cppflags is "unsupplied_implies_use_CXXFLAGS":
            self.cppflags = myargs[0].CXXFLAGS

    def _is_header(self, filename):
        """ Internal use.  Is filename a header file?"""
        return filename.split(
            '.')[-1].lower() in ["h", "hpp", "hxx", "hh", "inl"]

    def process(self, filename):
        """ Use the -MM option to the compiler to generate the list of dependencies
            If you supply a header file rather than a source file then
            a dummy, blank, source file will be transparently provided
            and the supplied header file will be included into the dummy source file.
        """
        file_is_header = self._is_header(filename)
        cmd = [self.cpp]
        cmd.extend(self.cppflags.split())
        cmd.append("-MM")
        if file_is_header:
            # Use /dev/null as the dummy source file.
            cmd.extend(["-include", filename, "-x", "c++", "/dev/null"])
        else:
            cmd.append(filename)

        if self.verbose >= 3:
            print(" ".join(cmd))

        try:
            output = subprocess.check_output(cmd, universal_newlines=True)
        except OSError as err:
            print(
                "HeaderHunter failed to run compiler to generate dependencies. error = ",
                err,
                file=sys.stderr)
            exit()

        # output will be something like
        # test_direct_include.o: tests/test_direct_include.cpp
        # tests/get_numbers.hpp tests/get_double.hpp tests/get_int.hpp
        # We need to throw away the object file and only keep the dependency
        # list
        deplist = output.split(":")[1]

        # Strip non-space whitespace, remove any backslashes, and remove any empty strings
        # Also remove the initially given filename and /dev/null from the list
        self.dependencies = [
            x for x in deplist.split() if x.strip('\\\t\n\r') and x not in [
                filename,
                "/dev/null"]]
        return self.dependencies

if __name__ == '__main__':
    cap = configargparse.getArgumentParser()
    cap.add("filename", help="File to use in \"$CPP $CPPFLAGS -MM filename\"")
    cap.add("-c", "--config", is_config_file=True, help="config file path")
    hh = HeaderHunter()
    myargs = cap.parse_known_args()

    if myargs[0].verbose >= 1:
        print(myargs[0])
    if myargs[0].verbose >= 2:
        cap.print_values()

    print(hh.process(myargs[0].filename))
