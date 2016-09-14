from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import subprocess

# Only used for the verbose print.
import configargparse

from ct.version import __version__
import ct.git_utils
import ct.configutils
import ct.utils
import ct.dirnamer


def add_base_arguments(cap, argv=None, variant=None):
    # Even though the variant is actually sucked out of the command line by
    # parsing the sys.argv directly, we put it into the configargparse to get
    # the help.
    if variant is None:
        variant = ct.configutils.extract_variant(argv=argv)

    cap.add(
        "--variant",
        help="Specifies which variant of the config should be used. "
             "Use the config name without the .conf",
        default=variant)
    cap.add(
        "-v",
        "--verbose",
        help="Output verbosity. Add more v's to make it more verbose",
        action="count",
        default=0)
    cap.add(
        "-q",
        "--quiet",
        help="Decrement verbosity. Useful in apps where the default verbosity > 0.",
        action="count",
        default=0)
    cap.add(
        "--version",
        action="version",
        version=__version__)
    cap.add(
        "-?",
        action='help',
        help='Help')


def add_common_arguments(cap, argv=None, variant=None):
    """ Insert common arguments into the configargparse object """
    add_base_arguments(cap, argv=argv, variant=variant)
    ct.dirnamer.add_arguments(cap)
    cap.add(
        "--ID",
        help="Compiler identification string.  The same string as CMake uses.",
        default=None)
    cap.add(
        "--CPP",
        help="C preprocessor",
        default="unsupplied_implies_use_CXX")
    cap.add("--CC", help="C compiler", default="gcc")
    cap.add("--CXX", help="C++ compiler", default="g++")
    cap.add(
        "--CPPFLAGS",
        help="C preprocessor flags",
        default="unsupplied_implies_use_CXXFLAGS")
    cap.add(
        "--CXXFLAGS",
        help="C++ compiler flags",
        default="-fPIC -g -Wall")
    cap.add(
        "--CFLAGS",
        help="C compiler flags",
        default="-fPIC -g -Wall")
    ct.utils.add_flag_argument(
        parser=cap,
        name="git-root",
        dest="git_root",
        default=True,
        help="Determine the git root then add it to the include paths.")
    cap.add(
        "--include",
        help="Extra path(s) to add to the list of include paths",
        nargs='*',
        default=[])
    ct.git_utils.NameAdjuster.add_arguments(cap)


def add_link_arguments(cap):
    """ Insert the link arguments into the configargparse singleton """
    cap.add(
        "--LD",
        help="Linker",
        default="unsupplied_implies_use_CXX")
    cap.add(
        "--LDFLAGS",
        help="Linker flags",
        default="unsupplied_implies_use_CXXFLAGS")


def add_output_directory_arguments(cap, variant):
    cap.add(
        "--bindir",
        help="Output directory for executables",
        default="".join(["bin/", variant]))
    cap.add(
        "--objdir",
        help="Output directory for object files",
        default="".join(["bin/", variant, "/obj"]))


def add_target_arguments(cap):
    """ Insert the arguments that control what targets get created
        into the configargparse singleton.
    """
    # Don't re-add filename if it is already in the configargparsea
    if not any('filename' in action.dest for action in cap._actions):
        cap.add(
            "filename",
            nargs="*",
            help="File(s) to compile to an executable(s)")
    cap.add(
        "--dynamic",
        nargs='*',
        help="File(s) to compile to a dynamic library")
    cap.add(
        "--static",
        nargs='*',
        help="File(s) to compile to a static library")
    cap.add(
        "--tests",
        nargs='*',
        help="File(s) to compile to a test and then execute")

def add_target_arguments_ex(cap):
    """ Add the target arguments and the extra arguments that augment 
        the target arguments 
    """
    add_target_arguments(cap)
    cap.add(
        "--TESTPREFIX",
        help='Runs tests with the given prefix, eg. "valgrind --quiet --error-exitcode=1"')
    cap.add(
        "--project-version",
        dest="projectversion",
        help="Set the CAKE_PROJECT_VERSION macro to this value")
    cap.add(
        "--project-version-cmd",
        dest="projectversioncmd",
        help="Execute this command to determine the CAKE_PROJECT_VERSION macro")


def unsupplied_replacement(variable, default_variable, verbose, variable_str):
    """ If a given variable has the letters "unsupplied" in it
        then return the given default variable.
    """
    replacement = variable
    if "unsupplied" in variable:
        replacement = default_variable
        if verbose >= 4:            
            print(" ".join([variable_str,
                            "was unsupplied. Changed to use ",
                            default_variable]))
    return replacement


def _substitute_CXX_for_missing(args):
    """ If C PreProcessor variables (and the same for the LD*) are not set
        but CXX ones are set then just use the CXX equivalents
    """
    args.CPP = unsupplied_replacement(args.CPP, args.CXX, args.verbose, "CPP")
    args.CPPFLAGS = unsupplied_replacement(
        args.CPPFLAGS, args.CXXFLAGS, args.verbose, "CPPFLAGS")
    try:
        args.LD = unsupplied_replacement(args.LD, args.CXX, args.verbose, "LD")
    except AttributeError:
        pass
    try:
        args.LDFLAGS = unsupplied_replacement(
            args.LDFLAGS, args.CXXFLAGS, args.verbose, "LDFLAGS")
    except AttributeError:
        pass


def _extend_includes_using_git_root(args):
    """ Unless turned off, the git root will be added
        to the list of include paths
    """
    if args.git_root and (
            hasattr(args, 'filename') or
            hasattr(args, 'static') or
            hasattr(args, 'dynamic') or
            hasattr(args, 'tests')):

        git_roots = set()

        # No matter whether args.filename is a single value or a list,
        # filenames will be a list
        filenames = []

        if hasattr(args, 'filename') and args.filename:
            filenames.extend(args.filename)

        if hasattr(args, 'static') and args.static:
            filenames.extend(args.static)

        if hasattr(args, 'dynamic') and args.dynamic:
            filenames.extend(args.dynamic)

        if hasattr(args, 'tests') and args.tests:
            filenames.extend(args.tests)

        for filename in filenames:
            git_roots.add(ct.git_utils.find_git_root(filename))

        args.include.extend(git_roots)


def _add_include_paths_to_flags(args):
    """ Add all the include paths to all three compile flags """
    for path in args.include:
        if path is not None:
            if path not in args.CPPFLAGS:
                args.CPPFLAGS += " -I " + path
            if path not in args.CFLAGS:
                args.CFLAGS += " -I " + path
            if path not in args.CXXFLAGS:
                args.CXXFLAGS += " -I " + path

    if args.verbose >= 4 and len(args.include) > 0:
        print(
            "Extra include paths have been appended to the *FLAG variables:")
        print("\tCPPFLAGS=" + args.CPPFLAGS)
        print("\tCFLAGS=" + args.CFLAGS)
        print("\tCXXFLAGS=" + args.CXXFLAGS)


def _set_project_version(args):
    """ C/C++ source code can rely on the CAKE_PROJECT_VERSION macro being set.
        If the user specified a projectversion then use that.
        Otherwise execute projectversioncmd to determine projectversion.
        In the completely unspecified case, use the zero version.
    """
    if hasattr(args,'projectversion') and args.projectversion:
        return

    try:
        args.projectversion = subprocess.check_output(
            args.projectversioncmd.split(),
            universal_newlines=True).strip('\n').split()[0]
        if args.verbose >= 4:
            print("Used projectversioncmd to set projectversion")
    except (subprocess.CalledProcessError, OSError) as err:        
            sys.stderr.write(" ".join(["Could not use projectversioncmd =",
                                      args.projectversioncmd,
                                      "to set projectversion.\n"]))
            if args.verbose <= 2:
                sys.stderr.write(str(err)+"\n")
                sys.exit(1)
            else:
                raise
    except AttributeError:        
        if args.verbose >= 6:
            print("Could not use projectversioncmd to set projectversion. Will use either existing projectversion or the zero version.")

    try:
        if not args.projectversion:
            args.projectversion = "-".join(
                [os.path.basename(os.getcwd()), "0.0.0-0"])
            if args.verbose >= 5:
                print("Set projectversion to the zero version")

        if '-DCAKE_PROJECT_VERSION' not in args.CPPFLAGS:
            args.CPPFLAGS += ' -DCAKE_PROJECT_VERSION=\\"' + \
                args.projectversion + '\\"'
        if '-DCAKE_PROJECT_VERSION' not in args.CFLAGS:
            args.CFLAGS += ' -DCAKE_PROJECT_VERSION=\\"' + \
                args.projectversion + '\\"'
        if '-DCAKE_PROJECT_VERSION' not in args.CXXFLAGS:
            args.CXXFLAGS += ' -DCAKE_PROJECT_VERSION=\\"' + \
                args.projectversion + '\\"'

        if args.verbose >= 4:
            print(
                "*FLAG variables have been modified with the project version:")
            print("\tCPPFLAGS=" + args.CPPFLAGS)
            print("\tCFLAGS=" + args.CFLAGS)
            print("\tCXXFLAGS=" + args.CXXFLAGS)
    except AttributeError:
        if args.verbose >= 3:
            print("No projectversion specified for the args.")

def _do_xxpend(args, name):
    """ For example, if name is CPPFLAGS, take the 
        args.prependcppflags and prepend them to args.CPPFLAGS.
        Similarly for append.
    """
    xxlist=('prepend','append')
    for xx in xxlist:
        xxpendname = ''.join([xx,name.lower()])
        if hasattr(args, xxpendname):
            xxpendattr = getattr(args, xxpendname)
            attr = getattr(args, name)
            if xxpendattr:
                extra = []
                for flag in xxpendattr:
                    if flag not in attr:
                        extra.append(flag)
                if xx == 'prepend':
                    attr = " ".join(extra + [attr])
                else:
                    attr = " ".join([attr] + extra)
            setattr(args, name, attr) 

def _tier_one_modifications(args):
    """ Do some early modifications that can potentially cause 
        downstream modifications.
    """
    _substitute_CXX_for_missing(args)
    flaglist = ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS')
    for flag in flaglist:
        _do_xxpend(args, flag)

    # Cake used preprocess to mean both magic flag preprocess and headerdeps preprocess
    if hasattr(args, 'preprocess') and args.preprocess:
        args.magic = 'cpp'
        args.headerdeps = 'cpp'
    

def _commonsubstitutions(args):
    """ If certain arguments have not been specified but others have
        then there are some obvious substitutions to make
    """
    args.verbose -= args.quiet

    # Fix the variant for any variant aliases
    # Taking the easy way out and just reparsing
    args.variant = ct.configutils.extract_variant()

    _tier_one_modifications(args)
    _extend_includes_using_git_root(args)
    _add_include_paths_to_flags(args)
    _set_project_version(args)

    try:
        # If the user didn't explicitly supply a bindir then modify the bindir to use the variant name
        args.bindir = unsupplied_replacement(args.bindir, os.path.join("bin",args.variant), args.verbose, "bindir")
    except AttributeError:
        pass

    try:
        # Same idea as the bindir modification
        args.objdir = unsupplied_replacement(args.objdir, os.path.join(args.bindir,"obj"), args.verbose, "objdir")
    except AttributeError:
        pass

# List to store the callback functions for parse args
_substitutioncallbacks = [_commonsubstitutions]

def resetcallbacks():
    """ Useful in tests to clear out the substitution callbacks """
    global _substitutioncallbacks
    _substitutioncallbacks = [_commonsubstitutions]

def registercallback(callback):
    """ Use this to register a function to be called back during the 
        substitutions call (usually during parseargs).
        The callback function will later be given "args" as its argument.
    """
    _substitutioncallbacks.append(callback)

def substitutions(args, verbose=None):
    if verbose is None:
        verbose = args.verbose

    for func in _substitutioncallbacks:
        func(args)

    if verbose >= 2:
        verboseprintconfig(args)

def parseargs(cap, argv=None, verbose=None):
    args = cap.parse_args(args=argv)

    if verbose is None:
        verbose = args.verbose

    substitutions(args, verbose)
    return args


def terminalcolumns():
    """ How many columns in the text terminal """
    try:
        columns = int(subprocess.check_output(['stty', 'size']).split()[1])
    except subprocess.CalledProcessError:
        columns = 80
    return columns

def verboseprintconfig(args):
    if args.verbose >= 3:
        print(" ".join(["Using variant =", args.variant]))
        cap = configargparse.getArgumentParser()
        cap.print_values()

    if args.verbose >= 2:
        verbose_print_args(args)

def verbose_print_args(args):
    # Print the args in two columns Attr: Value
    print("\n\nFinal aggregated variables for build:")
    maxattrlen = 0
    for attr in args.__dict__.keys():
        if len(attr) > maxattrlen:
            maxattrlen = len(attr)
    fmt = "".join(["{0:", str(maxattrlen + 1), "}: {1}"])
    rightcolbegin = maxattrlen + 3
    maxcols = terminalcolumns()
    rightcolsize = maxcols - rightcolbegin
    if maxcols <= rightcolbegin:
        print("Verbose print of args aborted due to small terminal size!")
        return

    for attr, value in sorted(args.__dict__.items()):
        if value is None:
            print(fmt.format(attr, ""))
            continue
        strvalue = str(value)
        valuelen = len(strvalue)
        if rightcolbegin + valuelen < maxcols:
            print(fmt.format(attr, strvalue))
        else:
            # values are too long to fit.  Split them on spaces
            valuesplit = strvalue.split(' ', valuelen % rightcolsize)
            print(fmt.format(attr, valuesplit[0]))
            for kk in range(1, len(valuesplit)):
                print(fmt.format("", valuesplit[kk]))
