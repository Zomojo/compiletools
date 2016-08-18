from __future__ import print_function
from __future__ import unicode_literals

import collections
import os
import inspect
from ct.memoize import memoize
import ct.wrappedos

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

    raise ValueError("Don't know how to convert " + str(value) + " to boolean.")


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

def add_flag_argument(parser, name, dest=None, default=False, help=None):
    """ Add a flag argument to an ArgumentParser instance.
        Either the --flag is present or the --no-flag is present.
        No trying to convert boolean values like the add_boolean_argument
    """
    if not dest:
        dest = name
    group = parser.add_mutually_exclusive_group()
    bool_help = help + " Use --no-" + name + " to turn the feature off."
    group.add_argument(
        '--' + name,
        dest=dest,
        default=default,
        action='store_true',
        help=bool_help)
    group.add_argument('--no-' + name, dest=dest, action='store_false')

def removemount(absolutepath):
    """ Remove the '/' on unix and (TODO) 'C:\' on Windows """
    return absolutepath[1:]


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
