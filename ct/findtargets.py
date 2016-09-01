from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
from io import open
import configargparse
import ct.utils
import ct.namer

def add_arguments(cap):
    """ Add the command line arguments that the HeaderDeps classes require """
    ct.namer.Namer.add_arguments(cap)
    cap.add(
        "--exemarkers",
        action='append',
        help='String that identifies a file as being an executable source.  e.g., "main ("')
    cap.add(
        "--testmarkers",
        action='append',
        help='String that identifies a file as being an test source.  e.g., "unit_test.hpp"')

    ct.utils.add_flag_argument(
        parser=cap,
        name="auto",
        default=False,
        help="Search the filesystem from the current working directory to find all the C/C++ files with main functions and unit tests")

    # Figure out what style classes are available and add them to the command
    # line options
    styles = [st[:-5].lower()
              for st in dict(globals()) if st.endswith('Style')]
    cap.add(
        '--style',
        choices=styles,
        default='indent',
        help="Output formatting style")


class NullStyle(object):

    def __call__(self, executabletargets, testtargets):
        print(executabletargets)
        print(testtargets)

class FlatStyle(object):

    def __call__(self, executabletargets, testtargets):
        print(" ".join(executabletargets+testtargets))

class IndentStyle(object):

    def __call__(self, executabletargets, testtargets):
        print("Executable Targets:")
        if executabletargets:
            for target in executabletargets:
                print("\t{}".format(target))
        else:
            print("\tNone found")

        print("Test Targets:")
        if testtargets:
            for target in testtargets:
                print("\t{}".format(target))
        else:
            print("\tNone found")


class ArgsStyle(object):

    def __call__(self, executabletargets, testtargets):
        if executabletargets:
            for target in executabletargets:
                sys.stdout.write(" {}".format(target))

        if testtargets:
            sys.stdout.write(' --tests')
            for target in testtargets:
                sys.stdout.write(" {}".format(target))


class FindTargets(object):

    """ Search the filesystem from the current working directory to find
        all the C/C++ files with main functions and unit tests.
    """

    def __init__(self, args, argv=None, variant=None, exedir=None):
        self._args = args
        self.namer = ct.namer.Namer(self._args, argv=argv, variant=variant, exedir=exedir)

    def process(self, args, path=None):
        """ Put the output of __call__ into the args """
        executabletargets, testtargets = self(path)
        args.filename += executabletargets
        if testtargets:
            if not args.tests:
                args.tests = []
            args.tests += testtargets

        if args.verbose >= 2:
            styleobj = ct.findtargets.IndentStyle()
            styleobj(executabletargets, testtargets)


    def __call__(self, path=None):
        """ Do the file system search and
            return the tuple ([executabletargets], [testtargets])
        """
        if path is None:
            path = "."
        executabletargets = []
        testtargets = []
        bindir = self.namer.topbindir()
        for root, dirs, files in os.walk(path):
            if bindir in root or self._args.objdir in root:
                continue
            for filename in files:
                pathname = os.path.join(root, filename)
                if not ct.utils.issource(pathname):
                    continue
                with open(pathname, encoding='utf-8', errors='ignore') as ff:
                    for line in ff:
                        if any(marker in line 
                               for marker in self._args.exemarkers):
                            # A file starting with test....cpp will be interpreted
                            # As a test even though it satisfied the exemarker
                            if filename.startswith('test'):
                                testtargets.append(pathname)
                                if self._args.verbose >= 3:
                                    print("Found a test: " + pathname)
                            else:
                                executabletargets.append(pathname)
                                if self._args.verbose >= 3:
                                    print(
                                        "Found an executable source: " +
                                        pathname)
                            break
                        if any(marker in line 
                               for marker in self._args.testmarkers):
                            testtargets.append(pathname)
                            if self._args.verbose >= 3:
                                print("Found a test: " + pathname)
                            break
        return executabletargets, testtargets


def main(argv=None):
    cap = configargparse.getArgumentParser()
    ct.findtargets.add_arguments(cap)

    args = ct.apptools.parseargs(cap, argv)
    findtargets = FindTargets(args)

    styleclass = globals()[args.style.title() + 'Style']
    styleobj = styleclass()
    executabletargets, testtargets = findtargets()
    styleobj(executabletargets, testtargets)

    return 0
