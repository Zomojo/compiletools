from __future__ import print_function
from __future__ import unicode_literals

import collections
import os
import subprocess
import sys
import inspect
import zlib
import appdirs
import configargparse

import ct.git_utils as git_utils
import ct.wrappedos
from ct.memoize import memoize


@memoize
def isheader(filename):
    """ Internal use.  Is filename a header file?"""
    return filename.split(
        '.')[-1].lower() in ["h", "hpp", "hxx", "hh", "inl"]


@memoize
def issource(filename):
    """ Internal use. Is the filename a source file?"""
    return filename.split('.')[-1].lower() in ["cpp", "cxx", "cc", "c"]


def isexecutable(filename):
    return os.path.isfile(filename) and os.access(filename, os.X_OK)

@memoize
def implied_source(filename):
    """ If a header file is included in a build then assume that the corresponding c or cpp file must also be build. """
    basename = os.path.splitext(filename)[0]
    extensions = [".cpp", ".cxx", ".cc", ".c", ".C", ".CC"]
    for ext in extensions:
        trialpath = basename + ext
        if ct.wrappedos.isfile(trialpath):
            return ct.wrappedos.realpath(trialpath)
    else:
        return None


@memoize
def impliedheader(filename):
    """ Guess what the header file is corresponding to the given source file """
    basename = os.path.splitext(filename)[0]
    extensions = [".hpp", ".hxx", ".hh", ".h", ".H", ".HH"]
    for ext in extensions:
        trialpath = basename + ext
        if ct.wrappedos.isfile(trialpath):
            return ct.wrappedos.realpath(trialpath)
    else:
        return None


def extractinitargs(args, classname):
    """ Extract the arguments that classname.__init__ needs out of args """
    # Build up the appropriate arguments to pass to the __init__ of the object.
    # For each argument given on the command line, check if it matches one for
    # the __init__
    kwargs = {}
    function_args = inspect.getargspec(classname.__init__).args
    for key, value in list(vars(args).items()):
        if key in function_args:
            kwargs[key] = value
    return kwargs


def tobool(value):
    """
    Tries to convert a wide variety of values to a boolean
    Raises an exception for unrecognised values
    """
    if str(value).lower() in ("yes", "y", "true", "t", "1", "on"):
        return True
    if str(value).lower() in ("no", "n", "false", "f", "0", "off"):
        return False

    raise Exception("Don't know how to convert " + str(value) + " to boolean.")


def add_boolean_argument(parser, name, dest=None, default=False, help=None):
    """Add a boolean argument to an ArgumentParser instance."""
    if not dest:
        dest = name
    group = parser.add_mutually_exclusive_group()
    bool_help = help + " Use --no-" + name + " to turn the feature off."
    group.add_argument(
        '--' + name,
        metavar="",
        nargs='?',
        dest=dest,
        default=default,
        const=True,
        type=tobool,
        help=bool_help)
    group.add_argument('--no-' + name, dest=dest, action='store_false')


def extract_variant_from_argv(argv=None):
    """ The variant argument is parsed directly from the command line arguments
        so that it can be used to specify the default config for configargparse.
    """
    if argv is None:
        argv = sys.argv

    # Parse the command line, extract the variant the user wants, then use
    # that as the default config file for configargparse
    variant = "debug"
    for arg in argv:
        try:
            if "--variant=" in arg:
                variant = arg.split('=')[1]
            elif "--variant" in arg:
                variant_index = argv.index("--variant")
                variant = argv[variant_index + 1]
        except ValueError:
            pass

    return variant


def variant_with_hash(args, argv=None, variant=None):
    """ Note that the argv can override the options in the config file.
        If we want to keep the differently specified flags separate then
        some hash of the argv must be added onto the config file name.
        Choose adler32 for speed
    """
    if argv is None:
        argv = sys.argv

    if not variant:
        variant = extract_variant_from_argv(argv)

    # The & <magicnumber> at the end is so that python2/3 give the same result
    return "%s.%08x" % (variant, (zlib.adler32(str(args)) & 0xffffffff))


def default_config_directories(
        user_config_dir=None,
        system_config_dir=None,
        argv=None):
    # Use configuration in the order (lowest to highest priority)
    # 1) same path as exe,
    # 2) system config (XDG compliant.  /etc/xdg/ct)
    # 3) user config   (XDG compliant. ~/.config/ct)
    # 4) given on the command line
    # 5) environment variables

    # These variables are settable to assist writing tests
    if user_config_dir is None:
        user_config_dir = appdirs.user_config_dir(appname='ct')
    if system_config_dir is None:
        system_config_dir = appdirs.site_config_dir(appname='ct')
    if argv is None:
        argv = sys.argv

    executable_config_dir = os.path.join(
        ct.wrappedos.dirname(
            ct.wrappedos.realpath(argv[0])),
        "ct.conf.d")
    return [user_config_dir, system_config_dir, executable_config_dir]


def config_files_from_variant(variant=None, argv=None):
    if variant is None:
        variant = extract_variant_from_argv(argv)
    return [
        os.path.join(defaultdir, variant)
        + ".conf" for defaultdir in default_config_directories(argv=argv)]


def add_common_arguments(cap):
    """ Insert common arguments into the configargparse object """
    # Even though the variant is actually sucked out of the command line by
    # parsing the sys.argv directly, we put it into the configargparse to get
    # the help.
    cap.add(
        "--variant",
        help="Specifies which variant of the config should be used. "
             "Use the config name without the .conf",
        default="debug")
    cap.add(
        "-v",
        "--verbose",
        help="Output verbosity. Add more v's to make it more verbose",
        action="count",
        default=0)
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
    add_boolean_argument(
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
    add_boolean_argument(
        cap,
        "shorten",
        'strip_git_root',
        default=False,
        help="Strip the git root from the filenames")


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
        if verbose >= 3:
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
        hasattr(args,'filename') or 
        hasattr(args,'static') or 
        hasattr(args,'dynamic') or
        hasattr(args,'tests')):

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
            git_roots.add(git_utils.find_git_root(filename))

        args.include.extend(git_roots)


def _add_include_paths_to_flags(args):
    """ Add all the include paths to all three compile flags """
    if args.include:
        for path in args.include:
            if path is None:
                raise ValueError(
                    "Parsing the args.include and path is unexpectedly None")
            args.CPPFLAGS += " -I " + path
            args.CFLAGS += " -I " + path
            args.CXXFLAGS += " -I " + path
        if args.verbose >= 3:
            print(
                "Extra include paths have been appended to the *FLAG variables:")
            print("\tCPPFLAGS=" + args.CPPFLAGS)
            print("\tCFLAGS=" + args.CFLAGS)
            print("\tCXXFLAGS=" + args.CXXFLAGS)


def _set_project_version(args):
    """ C/C++ source code can rely on the CAKE_PROJECT_VERSION macro being set.
        Preferentially execute projectversioncmd to determine projectversion.
        Otherwise, fall back to any given projectversion.
        In the completely unspecified case, use the zero version.
    """
    try:
        args.projectversion = subprocess.check_output(
            args.projectversioncmd.split(),
            universal_newlines=True).strip('\n')
        if args.verbose >= 4:
            print("Used projectversioncmd to set projectversion")
    except AttributeError:
        if args.verbose >= 6:
            print(
                "Could not use projectversioncmd to set projectversion. Will use either existing projectversion or the zero version.")

    try:
        if not args.projectversion:
            args.projectversion = "-".join(
                [os.path.basename(os.getcwd()), "0.0.0-0"])
            if args.verbose >= 5:
                print("Set projectversion to the zero version")

        args.CPPFLAGS += ' -DCAKE_PROJECT_VERSION=\\"' + \
            args.projectversion + '\\"'
        args.CFLAGS += ' -DCAKE_PROJECT_VERSION=\\"' + \
            args.projectversion + '\\"'
        args.CXXFLAGS += ' -DCAKE_PROJECT_VERSION=\\"' + \
            args.projectversion + '\\"'

        if args.verbose >= 3:
            print(
                "*FLAG variables have been modified with the project version:")
            print("\tCPPFLAGS=" + args.CPPFLAGS)
            print("\tCFLAGS=" + args.CFLAGS)
            print("\tCXXFLAGS=" + args.CXXFLAGS)
    except AttributeError:
        if args.verbose >= 3:
            print("No projectversion specified for the args.")


def commonsubstitutions(args):
    """ If certain arguments have not been specified but others have
        then there are some obvious substitutions to make
    """
    _substitute_CXX_for_missing(args)
    _extend_includes_using_git_root(args)
    _add_include_paths_to_flags(args)
    _set_project_version(args)

def parseargs(cap, argv=None):
    if not argv:
        argv = sys.argv
    ka = cap.parse_known_args(args=argv[1:])
    commonsubstitutions(ka[0])
    verbose_print_args(cap, ka[0])
    return ka[0]
    

def verbose_print_args(cap, args):
    if args.verbose >= 3:
        cap.print_values()
    if args.verbose >= 2:
        print(args)


def removemount(absolutepath):
    """ Remove the '/' on unix and (TODO) 'C:\' on Windows """
    return absolutepath[1:]


class Namer(object):

    """ From a source filename, calculate related names
        like executable name, object name, etc.
    """
    # The first Namer may change this.  All others need to be able to read it.
    _using_variant_with_hash_bindir = False
    
    def __init__(self, args):
        self.args = args

        # If the user didn't explicitly tell us what bindir to use the
        # generate a unique one for the args
        if self.args.bindir == 'bin/default':
            Namer._using_variant_with_hash_bindir = True
            vwh = variant_with_hash(args)
            self.args.bindir = "".join(["bin/", vwh])
            self.args.objdir = "".join(["bin/", vwh, "/obj"])

    @staticmethod
    def add_arguments(cap):
        add_common_arguments(cap)
        add_output_directory_arguments(cap,'default')

    def topbindir(self):
        """ What is the topmost part of the bin directory """
        if self._using_variant_with_hash_bindir:
            return "bin/"
        else:
            return self.args.bindir

    def _outputdir(self, defaultdir, sourcefilename=None):
        """ Used by object_dir and executable_dir.
            defaultdir must be either self.args.objdir or self.args.bindir
        """
        if sourcefilename:
            try:
                project_pathname = git_utils.strip_git_root(sourcefilename)
            except OSError:
                project_pathname = removemount(sourcefilename)

            relative = os.path.join(
                defaultdir,
                ct.wrappedos.dirname(project_pathname))
        else:
            relative = defaultdir
        return ct.wrappedos.realpath(relative)

    @memoize
    def object_dir(self, sourcefilename=None):
        """ Put objects into a directory structure that starts with the
            command line objdir but then replicates the project directory
            structure.  This way we can separate object files that have
            the same name but different paths.
        """
        return self._outputdir(self.args.objdir, sourcefilename)

    @memoize
    def object_name(self, sourcefilename):
        """ Return the name (not the path) of the object file
            for the given source.
        """
        name = os.path.split(sourcefilename)[1]
        basename = os.path.splitext(name)[0]
        return "".join([basename, ".o"])

    @memoize
    def object_pathname(self, sourcefilename):
        return "".join([self.object_dir(sourcefilename),
                        "/", self.object_name(sourcefilename)])

    @memoize
    def executable_dir(self, sourcefilename=None):
        """ Put the binaries into a directory structure that starts with the
            command line bindir but then replicates the project directory
            structure.  This way we can separate executable files that have
            the same name but different paths.
        """
        return self._outputdir(self.args.bindir, sourcefilename)

    @memoize
    def executable_name(self, sourcefilename):
        name = os.path.split(sourcefilename)[1]
        return os.path.splitext(name)[0]

    @memoize
    def executable_pathname(self, sourcefilename):
        return "".join([self.executable_dir(sourcefilename),
                        "/",
                        self.executable_name(sourcefilename)])

    @memoize
    def staticlibrary_name(self, sourcefilename):
        name = os.path.split(sourcefilename)[1]
        return "lib" + os.path.splitext(name)[0] + ".a"

    @memoize
    def staticlibrary_pathname(self, sourcefilename):
        """ Put static libraries in the same directory as executables """
        return "".join([self.executable_dir(sourcefilename),
                        "/",
                        self.staticlibrary_name(sourcefilename)])

    @memoize
    def dynamiclibrary_name(self, sourcefilename):
        name = os.path.split(sourcefilename)[1]
        return "lib" + os.path.splitext(name)[0] + ".so"

    @memoize
    def dynamiclibrary_pathname(self, sourcefilename):
        """ Put dynamic libraries in the same directory as executables """
        return "".join([self.executable_dir(sourcefilename),
                        "/",
                        self.dynamiclibrary_name(sourcefilename)])


class OrderedSet(collections.MutableSet):

    """ Set that remembers original insertion order.
        See https://code.activestate.com/recipes/576694/
    """

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next_ = self.map.pop(key)
            prev[2] = next_
            next_[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)
