# When python2 is no longer a target, switch to using functools.lru_cache(maxsize=None) rather than our custom memoize

class memoize(dict):
    def __init__(self, func):
        self.func = func

    def __call__(self, *args):
        return self[args]

    def __missing__(self, key):
        result = self[key] = self.func(*key)
        return result

