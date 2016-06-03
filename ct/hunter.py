#!/usr/bin/env python
from __future__ import print_function
import subprocess
import sys
import ct.utils as utils
import configargparse
import os
import re
import ct.tree as tree
from ct.memoize import memoize

# At deep verbose levels pprint is used
from pprint import pprint


@memoize
def implied_source(filename):
    """ If a header file is included in a build then assume that the corresponding c or cpp file must also be build. """
    basename = os.path.splitext(filename)[0]
    extensions = [".cpp", ".cxx", ".cc", ".c", ".C", ".CC"]
    for ext in extensions:
        trialpath = basename + ext
        if utils.isfile(trialpath):
            return trialpath
    else:
        return None


class HeaderTree:

    """ Create a tree structure that shows the header include tree """

    def __init__(self):
        # Keep track of ancestor paths so that we can do header cycle detection
        self.ancestor_paths = []

        # self.args will exist after this call
        utils.setattr_args(self)

        # Grab the include paths from the CPPFLAGS
        pat = re.compile('-I ([\S]*)')
        self.includes = pat.findall(self.args.CPPFLAGS)

        if self.args.verbose >= 3:
            print("Includes=" + str(self.includes))

    @memoize
    def _search_project_includes(self, include):
        """ Internal use.  Find the given include file in the project include paths """
        for inc_dir in self.includes:
            trialpath = os.path.join(inc_dir, include)
            if utils.isfile(trialpath):
                return trialpath

        # else:
        #    TODO: Try system include paths if the user sets (the currently nonexistent) "use-system" flag
        #    Only get here if the include file cannot be found anywhere
        #    raise FileNotFoundError("HeaderTree could not determine the location of ",include)
        return None

    @memoize
    def _find_include(self, include, cwd):
        """ Internal use.  Find the given include file.
            Start at the current working directory then try the project includes
        """
        # Check if the file is referable from the current working directory
        # if that guess doesn't exist then try all the include paths
        trialpath = os.path.join(cwd, include)
        if utils.isfile(trialpath):
            return trialpath
        else:
            return self._search_project_includes(include)

    @memoize
    def _create_include_list(self, realpath):
        """ Internal use. Create the list of includes for the given file """
        with open(realpath) as ff:
            # Assume that all includes occur in the first 2048 bytes
            text = ff.read(2048)

        # The pattern is intended to match all include statements
        pat = re.compile(
            '^[\s]*#include[\s]*["<][\s]*([\S]*)[\s]*[">]',
            re.MULTILINE)

        return pat.findall(text)

    def process(self, filename, node=None):
        """ Return a tree that describes the header includes
            The node is passed recursively, however the original caller
            does not need to pass it in.
        """
        realpath = utils.realpath(filename)

        if self.args.verbose >= 4:
            print("HeaderTree::process: " + realpath)

        if node is None:
            node = tree.tree()

        # Stop cycles
        if realpath in self.ancestor_paths:
            if self.args.verbose >= 4:
                print(
                    "HeaderTree::process is breaking the cycle on " +
                    realpath)
            return node
        self.ancestor_paths.append(realpath)

        # This next line is how you create the node in the tree
        node[realpath]

        if self.args.verbose >= 6:
            print("HeaderHunter inserted: " + realpath)
            pprint(tree.dicts(node))

        cwd = os.path.dirname(realpath)
        for include in self._create_include_list(realpath):
            trialpath = self._find_include(include, cwd)
            if trialpath:
                self.process(trialpath, node[realpath])
                if self.args.verbose >= 5:
                    print("HeaderHunter building tree: ")
                    pprint(tree.dicts(node))

        self.ancestor_paths.pop()
        return node


class HeaderDependencies:

    """ Using the C Pre Processor, create the list of headers that the given file depends upon. """

    def __init__(self):
        # self.args will exist after this call
        utils.setattr_args(self)

    @memoize
    def _is_header(self, filename):
        """ Internal use.  Is filename a header file?"""
        return filename.split(
            '.')[-1].lower() in ["h", "hpp", "hxx", "hh", "inl"]

    @memoize
    def process(self, filename):
        """ Use the -MM option to the compiler to generate the list of dependencies
            If you supply a header file rather than a source file then
            a dummy, blank, source file will be transparently provided
            and the supplied header file will be included into the dummy source file.
        """
        cmd = self.args.CPP.split()+self.args.CPPFLAGS.split()+["-MM"]
        if self._is_header(filename):
            # Use /dev/null as the dummy source file.
            cmd.extend(["-include", filename, "-x", "c++", "/dev/null"])
        else:
            cmd.append(filename)

        if self.args.verbose >= 3:
            print(" ".join(cmd))

        try:
            output = subprocess.check_output(cmd, universal_newlines=True)
            if self.args.verbose >= 5:
                print(output)
        except OSError as err:
            print(
                "HeaderDependencies failed to run compiler to generate dependencies. error = ",
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
        # Use a set to inherently remove any redundancies
        work_in_progress = {
            x for x in deplist.split() if x.strip('\\\t\n\r') and x not in [
                filename,
                "/dev/null"]}

        # Use realpath to get rid of  // and ../../ etc in paths (similar to normpath) and
        # to get the full path even to files in the current working directory
        return set(map(utils.realpath, work_in_progress))


class Hunter:

    """ Deeply inspect files to understand what are the header dependencies,
        other required source files, other required compile/link flags.
    """

    def __init__(self):
        self.header_deps = HeaderDependencies()

        cap = configargparse.getArgumentParser()
        utils.add_boolean_argument(
            parser=cap,
            name="preprocess",
            default=False,
            help="Invoke the preprocessor to find the magic flags (by default it just reads the file directly).")

        # self.args will exist after this call
        utils.setattr_args(self)

        # The Hunter needs to maintain a map of filenames to the map of all magic flags and each flag is a set
        # E.g., { '/somepath/libs/base/somefile.hpp':
        #           {'CPPFLAGS':set('-D MYMACRO','-D MACRO2'),
        #            'CXXFLAGS':set('-fsomeoption'),
        #            'LDFLAGS':set('-lsomelib')}}
        self.magic_flags = {}

        # The magic pattern is //#key=value with whitespace ignored
        self.magic_pattern = re.compile(
            '^[\s]*//#([\S]*?)[\s]*=[\s]*(.*)',
            re.MULTILINE)

    def magic(self):
        return self.magic_flags

    def parse_magic_flags(self, source_filename, headers):
        """ Extract all the magics flags from the given source (and all its included headers).
            A magic flag is anything that starts with a //# and ends with an =
        """
        text = ""
        if self.args.preprocess:
            # Preprocess but leave comments
            cmd = []
            cmd.extend(self.args.CPP.split())
            cmd.extend(self.args.CPPFLAGS.split())
            cmd.extend(["-C", "-E", source_filename])
            if self.args.verbose >= 3:
                print(" ".join(cmd))
            try:
                text = subprocess.check_output(cmd, universal_newlines=True)
                if self.args.verbose >= 7:
                    print(text)
            except OSError as err:
                print(
                    "Hunter failed to parse/preprocess the magic flags in " +
                    source_filename +
                    ". error = ",
                    err,
                    file=sys.stderr)
                exit()
        else:
            # reading and handling as one string is slightly faster than
            # handling a list of strings.
            # Only read first 2k for speed
            for filename in headers | set([source_filename]):
                with open(filename) as ff:
                    text += ff.read(2048)

        flags_for_filename = self.magic_flags.setdefault(source_filename, {})

        for match in self.magic_pattern.finditer(text):
            magic, flag = match.groups()
            flags_for_filename.setdefault(magic, set()).add(flag)
            if self.args.verbose >= 5:
                print(
                    "Using magic flag {0}={1} for source = {2}".format(
                        magic,
                        flag,
                        source_filename))

    @memoize
    def _required_files_impl(self, filename, source_only = True):
        """ The recursive implementation that finds the source files.  
            Necessary because we don't want to wipe out the cycle detection. 
            The source_only flag describes whether the return set of files 
            contains source files only or all headers and files encountered.
        """
        # TODO: See if we can just make it a precondition that source_filename
        # is a realpath.  The current check could be expensive.
        realpath = utils.realpath(filename)
        self.cycle_detection.add(realpath)
        deplist = self.header_deps.process(realpath)
        if filename not in self.magic_flags:
            self.parse_magic_flags(realpath, deplist)

        # One of the magic flags is SOURCE.  If that was present, add to the
        # file list.
        cwd = os.path.dirname(realpath)
        filelist = deplist
        extra_sources = self.magic_flags[realpath].get('SOURCE', set())
        for es in extra_sources:
            es_realpath = utils.realpath(os.path.join(cwd, es))
            if es_realpath not in self.cycle_detection:
                filelist.add(es_realpath)
                if self.args.verbose >= 2:
                    print(
                        "Adding extra source files due to magic SOURCE flag: " +
                        es_realpath)

        encountered_files = set([realpath])
        if not source_only:
            # Now if the magic source specified a source file this will miss them when source_only = True
            # However, they will get caught as an implied file below
            encountered_files |= filelist

        for nextfile in filelist:
            implied = implied_source(nextfile)            
            if implied and implied not in self.cycle_detection:
                encountered_files |= self._required_files_impl(implied,source_only)

        return encountered_files

    @memoize
    def required_source_files(self, source_filename):
        """ Create the list of source files that also need to be compiled to complete the linkage of the given source file.
            The returned set will contain the original source_filename.
            As a side effect, examine the files to determine the magic //#... flags
        """
        self.cycle_detection = set()
        return self._required_files_impl(source_filename)

    @memoize
    def required_files(self, filename):
        """ Create the list of files (both header and source) 
            that are either directly or indirectly utilised by the given file.
            The returned set will contain the original filename.
            As a side effect, examine the files to determine the magic //#... flags
        """
        self.cycle_detection = set()
        return self._required_files_impl(filename, source_only = False)

    def header_dependencies(self, source_filename):
        return self.header_deps.process(source_filename)
