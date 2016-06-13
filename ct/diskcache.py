import os
import functools
import cPickle as pickle
import ct.wrappedos


class diskcache:

    """ If a function takes a filename for its sole argument,
        then this diskcache decorator
        will use pickle to store the output of the function.
        The cachefile is judged to be valid/invalid by comparing
        the modification time against filename's modification.

        Usage:
        @diskcache('my_id1')
        def my_func( foo, bar )
    """
    # Bruce Eckel argues that this class based decorator with argument
    # approach is easier to understand and maintain over the
    # decorator function with decorator argument approach. See
    # http://www.artima.com/weblogs/viewpost.jsp?thread=240845

    def __init__(self, cache_identifier):
        self.cache_identifier = cache_identifier

        # TODO: use the python xdg module to make this more robust
        self.cachedir = os.path.join(os.path.expanduser("~"), ".cache/ct")
        ct.wrappedos.makedirs(self.cachedir)

    def __call__(self, func):
        @functools.wraps(func)
        def diskcacher(*args):
            """ The function that diskcache wraps must have a single
                argument which is a realpath of a file. Internally
                we call getmtime on that realpath. *args is used
                to accomodate the "self" if we are caching a member function
            """
            filename = args[-1]
            cachefile = ''.join(
                [self.cachedir, filename, '.', self.cache_identifier])
            recalc = True
            try:
                if ct.wrappedos.getmtime(
                        filename) < ct.wrappedos.getmtime(cachefile):
                    recalc = False
            except OSError:
                pass

            if recalc:
                result = func(*args)
                ct.wrappedos.makedirs(ct.wrappedos.dirname(cachefile))
                with open(cachefile, 'w') as cf:
                    pickle.dump(result, cf)
            else:
                with open(cachefile, 'r') as cf:
                    result = pickle.load(cf)

            return result

        return diskcacher
