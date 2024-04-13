import ct.dirnamer
import ct.apptools
import ct.headerdeps
import ct.magicflags
import os

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload


def reload_ct(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the ct.* modules
    """
    os.environ["CTCACHE"] = cache_home
    reload(ct.dirnamer)
    reload(ct.apptools)
    reload(ct.headerdeps)
    reload(ct.magicflags)