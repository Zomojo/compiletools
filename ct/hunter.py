#!/usr/bin/env python
from __future__ import print_function
import os
import subprocess
import sys
import configargparse
import re
import ct.wrappedos
import ct.utils as utils
import ct.tree as tree
from ct.memoize import memoize
from ct.memoize import memoize_false
from ct.diskcache import diskcache

# At deep verbose levels pprint is used
from pprint import pprint


class HeaderTree:

    """ Create a tree structure that shows the header include tree """

    def __init__(self, argv=None):

        # Keep track of ancestor paths so that we can do header cycle detection
        self.ancestor_paths = []

        self.args = None
        # self.args will exist after this call
        utils.setattr_args(self, argv)

        # Grab the include paths from the CPPFLAGS
        pat = re.compile('-I ([\S]*)')
        self.includes = pat.findall(self.args.CPPFLAGS)

        if self.args.verbose >= 8:
            print("HeaderTree::__init__")
        if self.args.verbose >= 3:
            print("Includes=" + str(self.includes))

    @memoize
    def _search_project_includes(self, include):
        """ Internal use.  Find the given include file in the project include paths """
        for inc_dir in self.includes:
            trialpath = os.path.join(inc_dir, include)
            if ct.wrappedos.isfile(trialpath):
                return ct.wrappedos.realpath(trialpath)

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
        if ct.wrappedos.isfile(trialpath):
            return ct.wrappedos.realpath(trialpath)
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

    def _generate_tree_impl(self, realpath, node=None):
        """ Return a tree that describes the header includes
            The node is passed recursively, however the original caller
            does not need to pass it in.
        """

        if self.args.verbose >= 4:
            print("HeaderTree::_generate_tree_impl: ",realpath)

        if node is None:
            node = tree.tree()

        # Stop cycles
        if realpath in self.ancestor_paths:
            if self.args.verbose >= 7:
                print(
                    "HeaderTree::_generate_tree_impl is breaking the cycle on ",
                    realpath)
            return node
        self.ancestor_paths.append(realpath)

        # This next line is how you create the node in the tree
        node[realpath]

        if self.args.verbose >= 6:
            print("HeaderTree inserted: " + realpath)
            pprint(tree.dicts(node))

        cwd = os.path.dirname(realpath)
        for include in self._create_include_list(realpath):
            trialpath = self._find_include(include, cwd)
            if trialpath:
                self._generate_tree_impl(trialpath, node[realpath])
                if self.args.verbose >= 5:
                    print("HeaderTree building tree: ")
                    pprint(tree.dicts(node))

        self.ancestor_paths.pop()
        return node

    def generatetree(self, filename):
        """ Returns the tree of include files """
        self.ancestor_paths = []
        realpath = ct.wrappedos.realpath(filename)
        return self._generate_tree_impl(realpath)

    def _process_impl_recursive(self, realpath, results):
        results.add(realpath)
        cwd = os.path.dirname(realpath)
        for include in self._create_include_list(realpath):
            trialpath = self._find_include(include, cwd)
            if trialpath and trialpath not in results:
                if self.args.verbose >= 9:
                    print("HeaderTree::_process_impl_recursive about to follow ",trialpath)
                self._process_impl_recursive(trialpath,results)

    # TODO: Stop writing to the same cache as HeaderDependencies.
    # Because the magic flags rely on the .deps cache, this hack was put in
    # place.
    @diskcache('deps', deps_mode=True)
    def _process_impl(self, realpath):
        if self.args.verbose >= 9:
            print("HeaderTree::_process_impl: " + realpath)

        results = set()
        self._process_impl_recursive(realpath,results)
        results.remove(realpath)
        return results

    def process(self, filename):
        """ Returns the dependencies in the same format as HeaderDependencies """
        if self.args.verbose >= 8:
            print("HeaderTree::process: " + filename)
        realpath = ct.wrappedos.realpath(filename)
        return self._process_impl(realpath)


class HeaderDependencies:

    """ Using the C Pre Processor, create the list of headers that the given file depends upon. """

    def __init__(self, argv=None):
        self.args = None
        # self.args will exist after this call
        utils.setattr_args(self, argv)

        if self.args.verbose >= 8:
            print("HeaderDependencies::__init__")

    @diskcache('deps', deps_mode=True)
    def _process_impl(self, realpath):
        """ Use the -MM option to the compiler to generate the list of dependencies
            If you supply a header file rather than a source file then
            a dummy, blank, source file will be transparently provided
            and the supplied header file will be included into the dummy source file.
        """
        cmd = self.args.CPP.split() + self.args.CPPFLAGS.split() + ["-MM"]
        if ct.utils.isheader(realpath):
            # Use /dev/null as the dummy source file.
            cmd.extend(["-include", realpath, "-x", "c++", "/dev/null"])
        else:
            cmd.append(realpath)

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
        # Also remove the initially given realpath and /dev/null from the list
        # Use a set to inherently remove any redundancies
        # Use realpath to get rid of  // and ../../ etc in paths (similar to normpath) and
        # to get the full path even to files in the current working directory
        return {ct.wrappedos.realpath(x) for x in deplist.split() if x.strip(
            '\\\t\n\r') and x not in [realpath, "/dev/null"]}

    def process(self, filename):
        """ Return the set of dependencies for a given filename """
        realpath = ct.wrappedos.realpath(filename)
        return self._process_impl(realpath)


class Hunter:

    """ Deeply inspect files to understand what are the header dependencies,
        other required source files, other required compile/link flags.
    """

    def __init__(self, argv=None):
        cap = configargparse.getArgumentParser()
        utils.add_boolean_argument(
            parser=cap,
            name="directread",
            default=True,
            help="Follow includes by directly reading files (the alternative is to use gcc -MM ... which is slower but more accurate).")
        utils.add_boolean_argument(
            parser=cap,
            name="preprocess",
            default=False,
            help="Invoke the preprocessor to find the magic flags (by default it just reads the file directly).")

        self.args = None
        # self.args will exist after this call
        utils.setattr_args(self, argv)

        if self.args.directread:
            if self.args.verbose >= 4:
                print("Using HeaderTree to trace dependencies")
            self.header_deps = HeaderTree(argv)
        else:
            if self.args.verbose >= 4:
                print("Using HeaderDependencies to trace dependencies")
            self.header_deps = HeaderDependencies(argv)

        # Extra command line options will now be understood so reprocess the
        # commandline
        utils.setattr_args(self, argv)

        # The magic pattern is //#key=value with whitespace ignored
        self.magic_pattern = re.compile(
            '^[\s]*//#([\S]*?)[\s]*=[\s]*(.*)',
            re.MULTILINE)

    # TODO: Rethink the whole diskcache concept.
    # Each diskcache is its own object.  So the deps files end up being loaded
    # twice.  Once for the HeaderDependencies deps diskcache and once for the
    # Hunter diskcache because the magic flags need to know what the tree of
    # dependencies are. My current thoughts are that the deps cache and
    # magic cache should be their own objects rather than trying to use
    # decorators
    @diskcache('magicflags', magic_mode=True)
    def reparse_magic_flags(self, source_filename):
        """ The Hunter needs to maintain a map of filenames
            to the map of all magic flags and each flag is a set
            E.g., { '/somepath/libs/base/somefile.hpp':
                       {'CPPFLAGS':set('-D MYMACRO','-D MACRO2'),
                        'CXXFLAGS':set('-fsomeoption'),
                        'LDFLAGS':set('-lsomelib')}}
            This function will extract all the magics flags from the given 
            source (and all its included headers).
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
            headers = self.header_dependencies(source_filename)
            for filename in headers | set([source_filename]):
                with open(filename) as ff:
                    text += ff.read(2048)

        flags_for_filename = {}

        for match in self.magic_pattern.finditer(text):
            magic, flag = match.groups()
            flags_for_filename.setdefault(magic, set()).add(flag)
            if self.args.verbose >= 5:
                print(
                    "Using magic flag {0}={1} for source = {2}".format(
                        magic,
                        flag,
                        source_filename))

        return flags_for_filename

    def parse_magic_flags(self, realpath):
        return self.reparse_magic_flags(realpath)

    def _extractSOURCE(self, realpath):
        sources = self.parse_magic_flags(realpath).get('SOURCE', set())
        cwd = os.path.dirname(realpath)        
        return {ct.wrappedos.realpath(os.path.join(cwd, es)) for es in sources}
    
    def _required_files_impl(self, realpath, source_only, processed=None, result=None):
        """ The recursive implementation that finds the source files.
            The source_only flag describes whether the return set of files
            contains source files only or all headers and files encountered.
            It is a precondition that realpath actually is a realpath.
        """
        if not processed:
            processed = set()
        if not result:
            result = set()

        if self.args.verbose >=7:
            print("Hunter::_required_files_impl. Finding header deps for ",realpath)
        
        # Don't try and collapse these lines.  
        # We don't want todo as a handle to the header_deps.process object.
        todo = set()
        todo |= self.header_deps.process(realpath)

        # One of the magic flags is SOURCE.  If that was present, add to the
        # file list.  WARNING:  Only use //#SOURCE= in a cpp file.
        ess = self._extractSOURCE(realpath)
        if self.args.verbose >= 2:
            print("Hunter. SOURCE flag files:",ess)
        todo |= ess

        # The header deps and magic flags have been parsed at this point so it 
        # is now safe to mark the realpath as processed.
        processed.add(realpath)
        if not source_only or ct.utils.issource(realpath):
            result.add(realpath)

        implied = ct.utils.implied_source(realpath)
        if implied and implied not in processed:
            todo.add(implied)

        try:
            todo.remove(realpath)
        except KeyError:
            pass
        todo -= processed

        while todo:
            morefiles = set()
            for nextfile in todo:
                morefiles |= self._required_files_impl(nextfile,source_only,processed,result)
            todo = morefiles.difference(processed)
            if self.args.verbose >= 9:
                print("Hunter::_required_files_impl. todo:",todo)

        if self.args.verbose >= 9:
            print("Hunter::_required_files_impl. Returning ", result)
        return result

    @memoize
    def required_source_files(self, filename):
        """ Create the list of source files that also need to be compiled to complete the linkage of the given source file.
            The returned set will contain the original source_filename.
            As a side effect, examine the files to determine the magic //#... flags
        """
        if self.args.verbose >= 9:
            print("Hunter::required_source_files for " + filename)
        return self._required_files_impl(filename, source_only=True)

    @memoize
    def required_files(self, filename):
        """ Create the list of files (both header and source)
            that are either directly or indirectly utilised by the given file.
            The returned set will contain the original filename.
            As a side effect, examine the files to determine the magic //#... flags
        """
        if self.args.verbose >= 9:
            print("Hunter::required_files for " + filename)
        return self._required_files_impl(
            ct.wrappedos.realpath(filename), source_only=False)

    def header_dependencies(self, source_filename):
        if self.args.verbose >= 8:
            print("Hunter asking for header dependencies for ",source_filename)
        return self.header_deps.process(source_filename)
