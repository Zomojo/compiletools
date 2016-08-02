""" Wrapper around appdirs that intercepts user_cache_dir 
    and uses the CTBUILD environment variable 
"""
import os
import appdirs

user_data_dir = appdirs.user_data_dir
user_config_dir = appdirs.user_config_dir
site_config_dir = appdirs.site_config_dir

def user_cache_dir(appname='ct', appauthor=None, version=None, opinion=True):
    try:
        cachedir = os.environ['CTCACHE']
    except KeyError:
        cachedir = appdirs.user_cache_dir(appname, appauthor, version, opinion)
    return cachedir

