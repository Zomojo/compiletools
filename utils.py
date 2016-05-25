import subprocess
import configargparse
import git_utils


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


def add_boolean_argument(parser, name, dest, default=False, help=None):
    """Add a boolean argument to an ArgumentParser instance."""
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


def common_substitutions(args):
    """ If certain arguments have not been specified but others have then there are some obvious substitutions to make """

    # If C PreProcessor variables are not set but CXX ones are set then
    # just use the CXX equivalents
    if args.CPP is "unsupplied_implies_use_CXX":
        args.CPP = args.CXX
        if args.verbose >= 3:
            print("CPP has been set to use CXX.  CPP=" + args.CPP)
    if args.CPPFLAGS is "unsupplied_implies_use_CXXFLAGS":
        args.CPPFLAGS = args.CXXFLAGS
        if args.verbose >= 3:
            print(
                "CPPFLAGS has been set to use CXXFLAGS.  CPPFLAGS=" +
                args.CPPFLAGS)

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
            print("Extra include paths have been appended to FLAGS")
            print("CPPFLAGS=" + args.CPPFLAGS)
            print("CFLAGS=" + args.CFLAGS)
            print("CXXFLAGS=" + args.CXXFLAGS)


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


class OrderedSet:

    """A set that preserves the order of insertion"""

    def __init__(self, init=()):
        self.ordered = []
        self.unordered = {}

        for s in init:
            self.insert(s)

    def add(self, e):
        if e in self.unordered:
            return
        self.ordered.append(e)
        self.unordered[e] = True

    def __repr__(self):
        return repr(self.ordered)

    def __contains__(self, e):
        return self.unordered.__contains__(e)

    def __len__(self):
        return self.ordered.__len__()

    def __iter__(self):
        return self.ordered.__iter__()

    def __or__(self, other):
        newset = self
        for element in other:
            newset.add(element)
        return newset
