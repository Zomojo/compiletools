from __future__ import print_function
import configargparse
import os

def delete_existing_parsers():
    """ The singleton parsers supplied by configargparse 
        don't play well with the unittest framework.  
        This function will delete them so you are 
        starting with a clean slate
    """
    configargparse._parsers = {}

def is_executable(filename):
    return os.path.isfile(filename) and os.access(filename,os.X_OK)
