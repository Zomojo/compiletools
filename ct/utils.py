import collections
import os
import sys
import inspect
import functools
import ct.wrappedos


def is_nonstr_iter(obj):
    """ A python 3 only method for deciding if the given variable
        is a non-string iterable
    """
    if isinstance(obj, str):
        return False
    return hasattr(obj, "__iter__")

@functools.lru_cache(maxsize=None)
def isheader(filename):
    """ Internal use.  Is filename a header file?"""
    return filename.split(".")[-1].lower() in ["h", "hpp", "hxx", "hh", "inl"]


@functools.lru_cache(maxsize=None)
def issource(filename):
    """ Internal use. Is the filename a source file?"""
    return filename.split(".")[-1].lower() in ["cpp", "cxx", "cc", "c"]


def isexecutable(filename):
    return os.path.isfile(filename) and os.access(filename, os.X_OK)


@functools.lru_cache(maxsize=None)
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


@functools.lru_cache(maxsize=None)
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


def clear_cache():
    isheader.cache_clear()
    issource.cache_clear()
    implied_source.cache_clear()
    impliedheader.cache_clear()


def extractinitargs(args, classname):
    """ Extract the arguments that classname.__init__ needs out of args """
    # Build up the appropriate arguments to pass to the __init__ of the object.
    # For each argument given on the command line, check if it matches one for
    # the __init__
    kwargs = {}
    function_args = inspect.getfullargspec(classname.__init__).args
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
        "--" + name,
        metavar="",
        nargs="?",
        dest=dest,
        default=default,
        const=True,
        type=tobool,
        help=bool_help,
    )
    group.add_argument("--no-" + name, dest=dest, action="store_false")


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
        "--" + name, dest=dest, default=default, action="store_true", help=bool_help
    )
    group.add_argument(
        "--no-" + name, dest=dest, action="store_false", default=not default
    )


def removemount(absolutepath):
    """ Remove the '/' on unix and (TODO) 'C:\' on Windows """
    return absolutepath[1:]


def ordered_unique(iterable):
    """Return unique items from iterable preserving insertion order.
    
    This replaces OrderedSet for the common case of deduplicating
    while preserving order. Uses dict.fromkeys() which is guaranteed
    to preserve insertion order in Python 3.7+.
    """
    return list(dict.fromkeys(iterable))


class OrderedSet(collections.abc.MutableSet):
    """Set that preserves insertion order using Python 3.7+ dict ordering.
    
    Much simpler than the previous implementation since we can rely on
    dict.fromkeys() to handle ordering and uniqueness.
    """

    def __init__(self, iterable=None):
        self._data = {}
        if iterable is not None:
            self.update(iterable)

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __reversed__(self):
        return reversed(list(self._data))

    def __repr__(self):
        if not self:
            return f"{self.__class__.__name__}()"
        return f"{self.__class__.__name__}({list(self)!r})"

    def add(self, key):
        self._data[key] = None

    def discard(self, key):
        self._data.pop(key, None)

    def append(self, iterable):
        """Add all items from iterable, maintaining order"""
        for item in iterable:
            self.add(item)

    def update(self, iterable):
        """Add all items from iterable (alias for append)"""
        self.append(iterable)

    def difference(self, iterable):
        """Return new OrderedSet with items not in iterable"""
        result = OrderedSet()
        iterable_set = set(iterable) if not isinstance(iterable, set) else iterable
        for key in self._data:
            if key not in iterable_set:
                result.add(key)
        return result

    def intersection(self, iterable):
        """Return new OrderedSet with items also in iterable"""
        result = OrderedSet()
        iterable_set = set(iterable) if not isinstance(iterable, set) else iterable
        for key in self._data:
            if key in iterable_set:
                result.add(key)
        return result

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    def __or__(self, other):
        """Union operation (|)"""
        result = OrderedSet(self)
        result.update(other)
        return result

    def __ior__(self, other):
        """In-place union operation (|=)"""
        self.update(other)
        return self

    def __sub__(self, other):
        """Difference operation (-)"""
        return self.difference(other)

    def __isub__(self, other):
        """In-place difference operation (-=)"""
        for item in other:
            self.discard(item)
        return self
