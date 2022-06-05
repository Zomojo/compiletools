import functools

def memoize_false(func):
    """ For a function that can only return true or false, memoize the false results """
    cache = func.cache = set()

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
