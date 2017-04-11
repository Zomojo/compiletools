import functools
import os
from io import open

try:
    import cPickle as pickle
except ImportError:
    import pickle

import ct.dirnamer
from ct.memoize import memoize_false
from ct.memoize import memoize
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
        
    # Keep track of the instances so we can clear the cache
    _instances = {}

    def __init__(self, cache_identifier, deps_mode=False, magic_mode=False):
        self.cache_identifier = cache_identifier
        self.deps_mode = deps_mode
        self.magic_mode = magic_mode
        self.cachedir = ct.dirnamer.user_cache_dir(appname='ct')
        if self.cachedir != 'None':
            ct.wrappedos.makedirs(self.cachedir)

        # Keep a copy of the cachefile in memory to reduce disk IO
        # Call it "cache" to match the memoizer "cache" (for ease of clearing)
        self.cache = {}

    def _cachefile(self, filename):
        """ What cachefile corresponds to the given filename """
        # Note that we can't use os.path.join because it 
        # THROWS AWAY self.cachedir due to filename being an absolute path.
        # That _feature_ cost me half a day.
        return ct.wrappedos.realpath(''.join([self.cachedir, os.sep, filename, '.', self.cache_identifier]))

    def _deps_cachefile(self, filename):
        """ What deps cachefile corresponds to the given filename """
        return ct.wrappedos.realpath(''.join([self.cachedir, os.sep, filename, '.deps']))

    def cached_cachefile(self, cachefile):
        """ Rather than using @memoize, keep the cache so that 
            we can manually prepopulate it.
        """
        if cachefile not in self.cache:
            with open(cachefile, mode='rb') as cf:
                self.cache[cachefile] = pickle.load(cf)
                if self.deps_mode:
                    # Verify that each of the files in the pickled disk cache still exists
                    for filename in self.cache[cachefile]:
                        if not os.path.exists(filename):
                            # Somehow the diskcache refers to a non-existent file.  Remove the diskcache and alert the user
                            os.remove(cachefile)
                            self.cache[cachefile] = None
                            diskcache.clear_cache()
                            raise IOError("Diskcache " + cachefile + " refered to nonexistent " + filename)

        return self.cache[cachefile]

    @memoize_false
    def _any_changes(self, filename, cachefile):
        """ Has this file changed since the cachefile was modified? """
        # Watch out for the user moving files around on disk.  It happens.
        if not os.path.exists(filename) or not os.path.exists(cachefile):
            self.cache[cachefile] = None
            return True

        try:
            # Can't use the memoized getmtime for cachefile because
            # _refresh_cache may update it.
            if ct.wrappedos.getmtime(filename) > os.path.getmtime(cachefile):
                return True

        except OSError:
            return True

        return False

    @memoize_false
    def _recursive_any_changes(self, filename, cachefile, originalcachefile=None):
        """ Has this file (or any [recursive] dependency) changed? """

        if originalcachefile is not None:
            if self._any_changes(filename, originalcachefile):
                return True

        if self._any_changes(filename, cachefile):
            return True

        if not self.deps_mode:
            return False

        # Since there is a modification time for the cachefile
        # we know that the cachefile exists.  So we can open
        # it and find out what dependencies also need to be
        # checked
        for dep in self.cached_cachefile(cachefile):
            if self._recursive_any_changes(dep, self._cachefile(dep), cachefile):
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
        for dep in self.cached_cachefile(deps_cachefile):
            # Note that cachefile is the cachefile corresponding to
            # filename that came in the function the argument
            # not the dep we are currently processing
            if self._any_changes(dep, cachefile):
                return True
        else:
            return False

    @staticmethod
    def clear_cache():
        for func, obj in diskcache._instances.items():
            try:
                obj.cache.clear()
                obj._any_changes.cache.clear()
                obj._recursive_any_changes.cache.clear()
                obj._recursive_any_changes.cache.clear()
                obj._magic_mode_any_changes.cache.clear()
            except AttributeError:
                pass

    def _refresh_cache(self, filename, cachefile, func, *args):
        """ If there are changes to the file
            then update the cache (potentially recursively)
        """
        # Files may have been deleted while their cachefile still exists
        # This will help in the cleanup
        # Note that (unlike cache files) source files are not allowed
        # to magically appear (or disappear) during the middle of a build.
        if not ct.wrappedos.isfile(filename):
            try:
                os.remove(cachefile)
                self.cache[cachefile] = None
            except OSError:
                pass
            return

        if self._any_changes(filename, cachefile):
            # args must have some sort of filename as the last argument
            # So we strip that off and replace it with the filename
            # that we are currently interested in.
            newargs = args[:-1] + (filename,)
            result = func(*newargs)
            ct.wrappedos.makedirs(ct.wrappedos.dirname(cachefile))
            with open(cachefile, mode='wb') as cf:
                pickle.dump(result, cf)
            self.cache[cachefile] = result
        else:
            # Prepopulate the in memory cache
            dummy = self.cached_cachefile(cachefile)

        if self.deps_mode:
            for dep in self.cached_cachefile(cachefile):
                # Due to the recursive nature of this function
                # you have to recheck if there are any changes.
                depcachefile = self._cachefile(dep)
                if self._any_changes(dep, depcachefile):
                    self._refresh_cache(dep, depcachefile, func, *args)

    def __call__(self, func):
        try:            
            if ct.dirnamer.user_cache_dir() == 'None':
                @functools.wraps(func)
                @memoize
                def memcacher(*args):
                    diskcache._instances[func] = self
                    return func(*args)

                # Return for __call__
                return memcacher
        except KeyError:
            pass

        @functools.wraps(func)
        def diskcacher(*args):
            """ The function that diskcache wraps must have a single
                argument which is a realpath of a file. Internally
                we call getmtime on that realpath. *args is used
                to accomodate the "self" if we are caching a member function
            """
            diskcache._instances[func] = self
            filename = args[-1]
            cachefile = self._cachefile(filename)
            if not os.path.exists(cachefile):
                self.cache[cachefile] = None
                self._refresh_cache(filename, cachefile, func, *args)
                
            if not self.deps_mode and not self.magic_mode and self._any_changes(
                    filename,
                    cachefile):
                self._refresh_cache(filename, cachefile, func, *args)

            if self.deps_mode and self._recursive_any_changes(
                    filename,
                    cachefile):
                self._refresh_cache(filename, cachefile, func, *args)

            if self.magic_mode and self._magic_mode_any_changes(
                    filename,
                    cachefile):
                self._refresh_cache(filename, cachefile, func, *args)

            return self.cached_cachefile(cachefile)

        # Return for __call__
        return diskcacher
