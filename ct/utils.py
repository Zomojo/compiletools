import subprocess
import configargparse
import ct.git_utils as git_utils
import collections
import os.path
import sys
from ct.memoize import memoize

import pdb


@memoize
def isfile(trialpath):
    """ Just a cached version of os.path.isfile """
    return os.path.isfile(trialpath)


@memoize
def realpath(trialpath):
    """ Just a cached version of os.path.realpath """
    return os.path.realpath(trialpath)


@memoize
def dirname(trialpath):
    """ A cached verion of os.path.dirname """
    return os.path.dirname(trialpath)


def isc(trialpath):
    """ Is the given file a C file ? """
    return ".c" == os.path.splitext(trialpath)[1]


def to_bool(value):
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
    group.add_argument(
        '--' + name,
        metavar="",
        nargs='?',
        dest=dest,
        default=default,
        const=True,
        type=to_bool,
        help=help + " Use --no-" + name + " to turn the feature off.")
    group.add_argument('--no-' + name, dest=dest, action='store_false')


def extract_variant_from_argv():
    """ The variant argument is parsed directly so that it can specify what actual config to load up """

    # Parse the command line, extract the variant the user wants, then use
    # that as the default config file.
    variant = "debug"
    for arg in sys.argv:
        try:
            if "--variant=" in arg:
                variant = arg.split('=')[1]
            elif "--variant" in arg:
                variant_index = sys.argv.index("--variant")
                variant = sys.argv[variant_index + 1]
        except:
            pass

    return variant


def default_config_directories():
    # Use configuration in the order (lowest to highest priority)
    # 1) same path as exe,
    # 2) system config
    # 3) user config
    # 4) given on the command line
    # 5) environment variables
    user_config_dir = os.path.join(os.path.expanduser("~"), ".config/ct/")
    system_config_dir = "/etc/ct.conf.d/"
    executable_config_dir = os.path.join(
        os.path.dirname(
            os.path.realpath(sys.argv[0])),
        "ct.conf.d/")
    return [user_config_dir, system_config_dir, executable_config_dir]


def config_files_from_variant():
    variant = extract_variant_from_argv()
    return [
        defaultdir +
        variant +
        ".conf" for defaultdir in default_config_directories()]


def add_common_arguments(cap):
    """ Insert common arguments into the configargparse object """
    # Even though the variant is actually sucked out of the command line by
    # parsing the sys.argv directly, we put it into the configargparse to get
    # the help.
    cap.add(
        "--variant",
        help="Specifies which variant of the config should be used. Use the config name without the .conf",
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
    """ Insert the arguments that control what targets get created into the configargparse singleton """
    cap.add("filename", nargs="*", help="File to compile to an executable")
    cap.add(
        "--dynamic",
        nargs='*',
        help="File to compile to an dynamic library")
    cap.add(
        "--static",
        nargs='*',
        help="File to compile to an dynamic library")


def unsupplied_replacement(variable, default_variable, verbose, variable_str):
    """ If a given variable has the letters "unsupplied" in it, return the given default variable """
    replacement = variable
    if "unsupplied" in variable:
        replacement = default_variable
        if verbose >= 3:
            print(" ".join([variable_str,
                            "was unsupplied. Changed to use ",
                            default_variable]))
    return replacement


def common_substitutions(args):
    """ If certain arguments have not been specified but others have then there are some obvious substitutions to make """

    # If C PreProcessor variables (and the same for the LD*) are not set but CXX ones are set then
    # just use the CXX equivalents
    args.CPP = unsupplied_replacement(args.CPP, args.CXX, args.verbose, "CPP")
    args.CPPFLAGS = unsupplied_replacement(
        args.CPPFLAGS, args.CXXFLAGS, args.verbose, "CPPFLAGS")
    try:
        args.LD = unsupplied_replacement(args.LD, args.CXX, args.verbose, "LD")
    except:
        pass
    try:
        args.LDFLAGS = unsupplied_replacement(
            args.LDFLAGS, args.CXXFLAGS, args.verbose, "LDFLAGS")
    except:
        pass

    # Unless turned off, the git root will be added to the list of include
    # paths
    if args.git_root and hasattr(args, 'filename'):
        filename = None
        # The filename/s in args could be either a string or a list
        try:
            filename = args.filename[0]
        except AttributeError:
            filename = args.filename
        except:
            pass
        finally:
            args.include.append(git_utils.find_git_root(filename))

    # Add all the include paths to all three compile flags
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


def setattr_args(obj):
    """ Add the common arguments to the configargparse,
        parse the args, then add the created args object
        as a member of the given object
    """
    cap = configargparse.getArgumentParser()
    add_common_arguments(cap)
    # parse_known_args returns a tuple.  The properly parsed arguments are in
    # the zeroth element.
    args = cap.parse_known_args()
    if args[0]:
        common_substitutions(args[0])
        setattr(obj, 'args', args[0])


def verbose_print_args(args):
    if args.verbose >= 2:
        print(args)
    if args.verbose >= 3:
        cap = configargparse.getArgumentParser()
        cap.print_values()


class Namer:

    """ From source filenames, calculate names like executable name, object name, etc """

    def __init__(self, cap, variant):
        add_output_directory_arguments(cap, variant)
        # self.args will exist after this call
        setattr_args(self)

    @memoize
    def object_dir(self, source_filename):
        """ Put objects into a directory structure that starts with the command line objdir
            but then replicates the project directory structure.  This way we can separate
            object files that have the same name but different paths
        """
        project_pathname = git_utils.strip_git_root(source_filename)
        return "".join([self.args.objdir, "/", dirname(project_pathname)])

    @memoize
    def object_name(self, source_filename):
        """ Return the name (not the path) of the object file for the given source """
        name = os.path.split(source_filename)[1]
        basename = os.path.splitext(name)[0]
        return "".join([basename, ".o"])

    @memoize
    def object_pathname(self, source_filename):
        return "".join(
            [self.object_dir(source_filename), "/", self.object_name(source_filename)])

    @memoize
    def executable_dir(self, source_filename):
        """ Put the binaries into a directory structure that starts with the command line bindir
            but then replicates the project directory structure.  This way we can separate
            executable files that have the same name but different paths
        """
        project_pathname = git_utils.strip_git_root(source_filename)
        return "".join([self.args.bindir, "/", dirname(project_pathname)])

    @memoize
    def executable_name(self, source_filename):
        name = os.path.split(source_filename)[1]
        return os.path.splitext(name)[0]

    @memoize
    def executable_pathname(self, source_filename):
        return "".join([self.executable_dir(source_filename),
                        "/",
                        self.executable_name(source_filename)])


class OrderedSet(collections.MutableSet):

    """ Set that remembers original insertion order.  https://code.activestate.com/recipes/576694/ """

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
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

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
