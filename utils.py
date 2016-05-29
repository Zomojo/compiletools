import subprocess
import configargparse
import git_utils
import collections
import os.path
from memoize import memoize


@memoize
def isfile(trialpath):
    """ Just a cached version of os.path.isfile """
    return os.path.isfile(trialpath)


@memoize
def realpath(trialpath):
    """ Just a cached version of os.path.realpath """
    return os.path.realpath(trialpath)


@memoize
def executable_name(source_filename):
    # TODO: Stop assuming exe files go into "bin"
    name = os.path.split(source_filename)[1]
    basename = os.path.splitext(name)[0]
    return "".join(["bin/", basename])

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


def add_common_arguments():
    """ Insert common arguments into the configargparse singleton """
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

def add_link_arguments():
    """ Insert the link arguments into the configargparse singleton """
    cap = configargparse.getArgumentParser()
    cap.add(
        "--LD",
        help="Linker",
        default="unsupplied_implies_use_CXX")
    cap.add(
        "--LDFLAGS",
        help="Linker flags",
        default="unsupplied_implies_use_CXXFLAGS")

def add_target_arguments(): 
    """ Insert the arguments that control what targets get created into the configargparse singleton """
    cap = configargparse.getArgumentParser()
    cap.add("-c", "--config", is_config_file=True, help="config file path")
    cap.add("filename", nargs='*', help="File to compile to an executable")
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
    if args.git_root:
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
            print("Extra include paths have been appended to the *FLAG variables:")
            print("\tCPPFLAGS=" + args.CPPFLAGS)
            print("\tCFLAGS=" + args.CFLAGS)
            print("\tCXXFLAGS=" + args.CXXFLAGS)


def setattr_args(obj):
    """ Add the common arguments to the configargparse,
        parse the args, then add the created args object
        as a member of the given object
    """
    add_common_arguments()
    cap = configargparse.getArgumentParser()
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
