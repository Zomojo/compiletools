from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
from io import open
import configargparse
import ct.utils

def add_arguments(cap):
    """ Add the command line arguments that the HeaderDeps classes require """
    ct.utils.Namer.add_arguments(cap)

class NullStyle(object):
    def __call__(self, executabletargets, testtargets):
        print(executabletargets)
        print(testtargets)

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
            sys.stdout.write(' --filename')
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
    def __init__(self, args):
        self._args = args
        self._exemarkers = ['main(', 'main (', 'wxIMPLEMENT_APP']
        self._testmarkers = ['unit_test.hpp']

    def __call__(self):
        """ Returns a tuple ([executabletargets], [testtargets]) """
        executabletargets = []
        testtargets = []
        namer = ct.utils.Namer(self._args)
        bindir = namer.topbindir()
        for root, dirs, files in os.walk('.'):
            if bindir in root or self._args.objdir in root:
                continue
            for filename in files:
                pathname = os.path.join(root, filename)
                if not ct.utils.issource(pathname):
                    continue
                with open(pathname, encoding='utf-8', errors='ignore') as ff:
                    for line in ff:
                        if any( marker in line for marker in self._exemarkers ):
                            if filename.startswith('test'):
                                testtargets.append(pathname)
                                if self._args.verbose >= 3:
                                    print("auto found a test: " + pathname)
                            else:
                                executabletargets.append(pathname)
                                if self._args.verbose >= 3:
                                    print("auto found an executable source: " + pathname)
                            break
                        if any( marker in line for marker in self._testmarkers ):
                            testtargets.append(pathname)
                            if self._args.verbose >= 3:
                                print("auto found a test: " + pathname)
                            break
        return executabletargets,testtargets

def main(argv=None):
    if argv is None:
        argv = sys.argv

    variant = ct.utils.extract_variant_from_argv(argv)
    cap = configargparse.getArgumentParser()
    ct.findtargets.add_arguments(cap)

    # Figure out what style classes are available and add them to the command
    # line options
    styles = [st[:-5].lower() for st in dict(globals()) if st.endswith('Style')]
    cap.add(
        '--style',
        choices=styles,
        default='indent',
        help="Output formatting style")

    args = ct.utils.parseargs(cap, argv)
    findtargets = FindTargets(args)

    styleclass = globals()[args.style.title() + 'Style']
    styleobj = styleclass()
    executabletargets,testtargets = findtargets()
    styleobj(executabletargets, testtargets)

    return 0
