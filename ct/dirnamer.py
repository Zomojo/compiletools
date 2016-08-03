""" Wrapper around appdirs that intercepts user_cache_dir 
    and uses the CTBUILD environment variable 
"""
import os
import appdirs

user_data_dir = appdirs.user_data_dir
user_config_dir = appdirs.user_config_dir
site_config_dir = appdirs.site_config_dir

def user_cache_dir(appname='ct', appauthor=None, version=None, opinion=True, args=None):
    if args is None:
        verbose = 0
    else:
        verbose = args.verbose

    try:            
        cachedir = os.environ['CTCACHE']
        if cachedir == 'None':
            if verbose > 0:
                print("Environment variable CTCACHE is None.  Disk caching is disabled.")
        else:
            if verbose > 0:
                print("".join(["Environment variable CTCACHE is ", cachedir, ". Using this as the cache directory."]))

    except KeyError:
        cachedir = appdirs.user_cache_dir(appname, appauthor, version, opinion)
        if verbose > 0:
            print("Environment variable CTCACHE doesn't exist.  Falling back to python-appdirs (which on linux wraps XDG variables) " + cachedir)

    return cachedir
