import compiletools.dirnamer
import compiletools.apptools
import compiletools.headerdeps
import compiletools.magicflags
import os

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload


def reload_ct(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the compiletools.* modules
    """
    os.environ["CTCACHE"] = cache_home
    reload(compiletools.dirnamer)
    reload(compiletools.apptools)
    reload(compiletools.headerdeps)
    reload(compiletools.magicflags)