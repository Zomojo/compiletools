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


def memoize_false(func):
    """ For a function that can only return true or false, memoize the false results """
    cache = set()

    @functools.wraps(func)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key in cache:
            return False
        else:
            result = func(*args, **kwargs)
            if not result:
                cache.add(key)
            return result

    return memoizer
