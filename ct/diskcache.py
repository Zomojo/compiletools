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
        that in turn must be checked, then use the 
        deps_cache=True argument.

        Usage:
        @diskcache('my_id1')
        def my_func(foo, bar):
            ....

        @diskcache('my_id2', deps_cache=True)
        def my_func_uses_deps(doh, ray):
            ....
    """
    # Bruce Eckel argues that this class based decorator with argument
    # approach is easier to understand and maintain over the
    # decorator function with decorator argument approach. See
    # http://www.artima.com/weblogs/viewpost.jsp?thread=240845

    def __init__(self, cache_identifier, deps_cache=False):
        self.cache_identifier = cache_identifier
        self.deps_cache = deps_cache

        # TODO: use the python xdg module to make this more robust
        self.cachedir = os.path.join(os.path.expanduser("~"), ".cache/ct")
        ct.wrappedos.makedirs(self.cachedir)

    def _cachefile(self, filename):
        """ What cachefile corresponds to the given filename """
        return ''.join([self.cachedir, filename, '.', self.cache_identifier])

    @memoize_false
    def _any_changes(self, filename):
        """ Has this file changed since the cachefile was modified? """
        cachefile = self._cachefile(filename)
        try: 
            # Can't use the memoized getmtime for cachefile because 
            # _refresh_cache may update it.
            if ct.wrappedos.getmtime(filename) > os.path.getmtime(cachefile):
                return True
        except OSError:
            return True
      
        return False

    @memoize_false
    def _any_recursive_changes(self, filename):
        """ Has this file (or any [recursive] dependency) changed? """
        if self._any_changes(filename):
            return True

        if not self.deps_cache:
            return False

        # Since there is a modification time for the cachefile
        # we know that the cachefile exists.  So we can open
        # it and find out what dependencies also need to be
        # checked
        cachefile = self._cachefile(filename)
        for dep in pickle.load(open(cachefile, 'r')):
            if self._any_recursive_changes(dep):
                return True
        else:
            return False
    
    def _refresh_cache(self, filename, func, *args):
        """ If there are changes to the file
            then update the cache (potentially recursively) 
        """
        if self._any_changes(filename):
            newargs = args[:-1] + (filename,)
            result = func(*newargs)
            cachefile = self._cachefile(filename)
            ct.wrappedos.makedirs(ct.wrappedos.dirname(cachefile))
            with open(cachefile, 'w') as cf:
                pickle.dump(result, cf)

        if self.deps_cache:
            cachefile = self._cachefile(filename)
            for dep in pickle.load(open(cachefile, 'r')):
                # Due to the recursive nature of this function
                # you have to recheck if there are any changes.
                if self._any_changes(dep):
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

            if self._any_recursive_changes(filename):
                self._refresh_cache(filename,func,*args)

            cachefile = self._cachefile(filename)
            return pickle.load(open(cachefile, 'r'))

        # Return for __call__
        return diskcacher
