import functools

def memoize(obj):
    """ memoize is a simple decorator to memoize results.
        When python2 is no longer a target, switch to using
        functools.lru_cache(maxsize=None) rather than our custom memoize
    """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer

