from __future__ import print_function
from __future__ import unicode_literals

import os
import re
from io import open

# At deep verbose levels pprint is used
from pprint import pprint

from ct.memoize import memoize
import ct.wrappedos
import ct.apptools
import ct.tree as tree
import ct.preprocessor
from ct.diskcache import diskcache


def create(args):
    """ HeaderDeps Factory """
    classname = args.headerdeps.title() + 'HeaderDeps'
    if args.verbose >= 4:
        print("Creating " + classname + " to process header dependencies.")
    depsclass = globals()[classname]
    depsobject = depsclass(args)
    return depsobject


def add_arguments(cap):
    """ Add the command line arguments that the HeaderDeps classes require """
    ct.apptools.add_common_arguments(cap)
    alldepscls = [st[:-10].lower()
                  for st in dict(globals()) if st.endswith('HeaderDeps')]
    cap.add(
        '--headerdeps',
        choices=alldepscls,
        default='direct',
        help="Methodology for determining header dependencies")


class HeaderDepsBase(object):

    """ Implement the common functionality of the different header
        searching classes.  This really should be an abstract base class.
    """

    def __init__(self, args):
        self.args = args

    def _process_impl(self, realpath):
        """ Derived classes implement this function """
        raise NotImplemented

    def process(self, filename):
        """ Return the set of dependencies for a given filename """
        realpath = ct.wrappedos.realpath(filename)
        return self._process_impl(realpath)


class DirectHeaderDeps(HeaderDepsBase):

    """ Create a tree structure that shows the header include tree """

    def __init__(self, args):
        HeaderDepsBase.__init__(self, args)

        # Keep track of ancestor paths so that we can do header cycle detection
        self.ancestor_paths = []

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
            if ct.wrappedos.isfile(trialpath):
                return ct.wrappedos.realpath(trialpath)

        # else:
        #    TODO: Try system include paths if the user sets (the currently nonexistent) "use-system" flag
        #    Only get here if the include file cannot be found anywhere
        #    raise FileNotFoundError("DirectHeaderDeps could not determine the location of ",include)
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
        with open(realpath, encoding='utf-8', errors='ignore') as ff:
            # Assume that all includes occur at the top of the file
            text = ff.read(4096)

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
            print("DirectHeaderDeps::_generate_tree_impl: ", realpath)

        if node is None:
            node = tree.tree()

        # Stop cycles
        if realpath in self.ancestor_paths:
            if self.args.verbose >= 7:
                print(
                    "DirectHeaderDeps::_generate_tree_impl is breaking the cycle on ",
                    realpath)
            return node
        self.ancestor_paths.append(realpath)

        # This next line is how you create the node in the tree
        node[realpath]

        if self.args.verbose >= 6:
            print("DirectHeaderDeps inserted: " + realpath)
            pprint(tree.dicts(node))

        cwd = os.path.dirname(realpath)
        for include in self._create_include_list(realpath):
            trialpath = self._find_include(include, cwd)
            if trialpath:
                self._generate_tree_impl(trialpath, node[realpath])
                if self.args.verbose >= 5:
                    print("DirectHeaderDeps building tree: ")
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
        cwd = ct.wrappedos.dirname(realpath)
        for include in self._create_include_list(realpath):
            trialpath = self._find_include(include, cwd)
            if trialpath and trialpath not in results:
                if self.args.verbose >= 9:
                    print(
                        "DirectHeaderDeps::_process_impl_recursive about to follow ",
                        trialpath)
                self._process_impl_recursive(trialpath, results)

    # TODO: Stop writing to the same cache as CPPHeaderDeps.
    # Because the magic flags rely on the .deps cache, this hack was put in
    # place.
    @diskcache('deps', deps_mode=True)
    def _process_impl(self, realpath):
        if self.args.verbose >= 9:
            print("DirectHeaderDeps::_process_impl: " + realpath)

        results = set()
        self._process_impl_recursive(realpath, results)
        results.remove(realpath)
        return results


class CppHeaderDeps(HeaderDepsBase):

    """ Using the C Pre Processor, create the list of headers that the given file depends upon. """

    def __init__(self, args):
        HeaderDepsBase.__init__(self, args)
        self.preprocessor = ct.preprocessor.PreProcessor(args)

    @diskcache('deps', deps_mode=True)
    def _process_impl(self, realpath):
        """ Use the -MM option to the compiler to generate the list of dependencies
            If you supply a header file rather than a source file then
            a dummy, blank, source file will be transparently provided
            and the supplied header file will be included into the dummy source file.
        """
        output = self.preprocessor.process(realpath, extraargs="-MM")

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
