#!/usr/bin/env python
from __future__ import print_function
import subprocess
import sys
import utils
import configargparse
import os

import re
import tree

class HeaderTree:

    """ Create a tree structure that shows the header include tree """

    def __init__(self):
        # self.args will exist after this call
        utils.setattr_args(self)

        # Grab the include paths from the CPPFLAGS
        pat=re.compile('-I ([\S]*)')
        self.includes=pat.findall(self.args.CPPFLAGS)

        if self.args.verbose >= 3:
            print("Includes="+str(self.includes))

    def process(self, filename, node = None):
        """ Return a tree that describes the header includes
            The node is passed recursively, however the original caller 
            does not need to pass it in.
        """
        realpath=os.path.realpath(filename)
        if self.args.verbose >= 4:
            print("process: " + realpath)
        if node is None:
            node=tree.tree()

        node[realpath]
        if self.args.verbose >= 6:
            print("Inserting node: ")
            pprint(tree.dicts(node))

        with open(filename) as ff:
            text=ff.read(2048)  # Assume that all includes occur in the first 2048 bytes

        # The pattern is intended to match all include statements
        pat=re.compile('^[\s]*#include[\s]*["<][\s]*([\S]*)[\s]*[">]',re.MULTILINE)
 
        cwd=os.path.dirname(realpath)
        for iter in pat.finditer(text):
            include = iter.group(1)

            # Check if the file is referable from the current working directory
            # if that guess doesn't exist then try all the include paths
            trialpath=os.path.join(cwd,include)
            if not os.path.isfile( trialpath ):
                for inc_dir in self.includes:
                    trialpath=os.path.join(inc_dir,include)
                    if os.path.isfile( trialpath ):
                        break
                else:
                    # TODO: Try system include paths if the user sets (the currently nonexistent) "use-system" flag
                    # Only get here if the include file cannot be found anywhere    
                    # raise FileNotFoundError("HeaderTree could not determine the location of ",include)
                    return node
            
            self.process(trialpath,node[realpath])
            if self.args.verbose >= 5:
                print("Building tree: ")
                pprint(tree.dicts(node))
        return node



class HeaderDependencies:

    """ Using the C Pre Processor, create the list of headers that the given file depends upon. """

    def __init__(self):
        # self.args will exist after this call
        utils.setattr_args(self)

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
        cmd = [self.args.CPP]
        cmd.extend(self.args.CPPFLAGS.split())
        cmd.append("-MM")
        if file_is_header:
            # Use /dev/null as the dummy source file.
            cmd.extend(["-include", filename, "-x", "c++", "/dev/null"])
        else:
            cmd.append(filename)

        if self.args.verbose >= 3:
            print(" ".join(cmd))

        try:
            output = subprocess.check_output(cmd, universal_newlines=True)
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
        self.dependencies = map(os.path.realpath, work_in_progress)
        return self.dependencies

# class ImpliedFileHunter:
#    """ If a header file is included in a build then assume that the corresponding c or cpp file must also be build. """


if __name__ == '__main__':
    cap = configargparse.getArgumentParser()
    cap.add("filename", help="File to use in \"$CPP $CPPFLAGS -MM filename\"")
    cap.add("-c", "--config", is_config_file=True, help="config file path")
    hh = HeaderDependencies()
    myargs = cap.parse_known_args()

    if myargs[0].verbose >= 1:
        print(myargs[0])
    if myargs[0].verbose >= 2:
        cap.print_values()

    map(print, hh.process(myargs[0].filename))
