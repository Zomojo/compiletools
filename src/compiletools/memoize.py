import functools

def memoize_false(func):
    """ For a function that can only return true or false, memoize the false results """
    cache = func.cache = set()

    @functools.wraps(func)
    def memoizer(*args, **kwargs):
        # Using a tuple to represent the key since it's hashable and can store both args and kwargs
        # This avoids the need to convert args and kwargs to strings
        key = (args, tuple(sorted(kwargs.items())))
        if key in cache:
            return False
        result = func(*args, **kwargs)
        if not result:
            cache.add(key)
        return result

    return memoizer
