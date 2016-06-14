import os
import functools
try:
    import cPickle as pickle
except ImportError:
    import pickle
from ct.memoize import memoize_false
import ct.wrappedos


class diskcache:

    """ If a function takes a filename for its sole argument,
        then this diskcache decorator
        will use pickle to store the output of the function.
        The cachefile is judged to be valid/invalid by comparing
        the modification time against filename's modification.

        If the cache is itself a cache of filenames
        that in turn must be checked, then use
        deps_mode=True

        If the cache depends on the previously updated deps then use
        magic_mode=True

        Usage:
        @diskcache('my_id1')
        def my_func(foo, bar):
            ....

        @diskcache('my_id2', deps_mode=True)
        def my_func_uses_deps(doh, ray):
            ....
    """
    # Bruce Eckel argues that this class based decorator with argument
    # approach is easier to understand and maintain over the
    # decorator function with decorator argument approach. See
    # http://www.artima.com/weblogs/viewpost.jsp?thread=240845

    def __init__(self, cache_identifier, deps_mode=False, magic_mode=False):
        self.cache_identifier = cache_identifier
        self.deps_mode = deps_mode
        self.magic_mode = magic_mode

        # TODO: use the python xdg module to make this more robust
        self.cachedir = os.path.join(os.path.expanduser("~"), ".cache/ct")
        ct.wrappedos.makedirs(self.cachedir)

    def _cachefile(self, filename):
        """ What cachefile corresponds to the given filename """
        return ''.join([self.cachedir, filename, '.', self.cache_identifier])

    def _deps_cachefile(self, filename):
        """ What deps cachefile corresponds to the given filename """
        return ''.join([self.cachedir, filename, '.deps'])

    @memoize_false
    def _any_changes(self, filename, cachefile):
        """ Has this file changed since the cachefile was modified? """
        try:
            # Can't use the memoized getmtime for cachefile because
            # _refresh_cache may update it.
            if ct.wrappedos.getmtime(filename) > os.path.getmtime(cachefile):
                return True
        except OSError:
            return True

        return False

    @memoize_false
    def _any_recursive_changes(self, filename, cachefile):
        """ Has this file (or any [recursive] dependency) changed? """
        if self._any_changes(filename, cachefile):
            return True

        if not self.deps_mode:
            return False

        # Since there is a modification time for the cachefile
        # we know that the cachefile exists.  So we can open
        # it and find out what dependencies also need to be
        # checked
        for dep in pickle.load(open(cachefile, 'rb')):
            if self._any_recursive_changes(dep, self._cachefile(dep)):
                return True
        else:
            return False

    @memoize_false
    def _magic_mode_any_changes(self, filename, cachefile):
        """ An alternate way to decide if there are any changes
            that make it time to refresh the cache
            TODO: Change the name.
        """
        if self._any_changes(filename, cachefile):
            return True

        deps_cachefile = self._deps_cachefile(filename)
        for dep in pickle.load(open(deps_cachefile, 'rb')):
            # Note that cachefile is the cachefile corresponding to
            # filename that came in the function the argument
            # not the dep we are currently processing
            if self._any_changes(dep, cachefile):
                return True
        else:
            return False

    def _refresh_cache(self, filename, func, *args):
        """ If there are changes to the file
            then update the cache (potentially recursively)
        """
        cachefile = self._cachefile(filename)
        if self._any_changes(filename, cachefile):
            newargs = args[:-1] + (filename,)
            result = func(*newargs)
            ct.wrappedos.makedirs(ct.wrappedos.dirname(cachefile))
            with open(cachefile, 'wb') as cf:
                pickle.dump(result, cf)

        if self.deps_mode:
            cachefile = self._cachefile(filename)
            for dep in pickle.load(open(cachefile, 'rb')):
                # Due to the recursive nature of this function
                # you have to recheck if there are any changes.
                if self._any_changes(dep, self._cachefile(dep)):
                    self._refresh_cache(dep, func, *args)

    def __call__(self, func):
        @functools.wraps(func)
        def diskcacher(*args):
            """ The function that diskcache wraps must have a single
                argument which is a realpath of a file. Internally
                we call getmtime on that realpath. *args is used
                to accomodate the "self" if we are caching a member function
            """
            filename = args[-1]
            cachefile = self._cachefile(filename)

            if not self.deps_mode and not self.magic_mode and self._any_changes(
                    filename,
                    cachefile):
                self._refresh_cache(filename, func, *args)

            if self.deps_mode and self._any_recursive_changes(
                    filename,
                    cachefile):
                self._refresh_cache(filename, func, *args)

            if self.magic_mode and self._magic_mode_any_changes(
                    filename,
                    cachefile):
                self._refresh_cache(filename, func, *args)

            return pickle.load(open(cachefile, 'rb'))

        # Return for __call__
        return diskcacher
