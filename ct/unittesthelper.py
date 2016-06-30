from __future__ import print_function
import configargparse

def delete_existing_parsers():
    """ The singleton parsers supplied by configargparse 
        don't play well with the unittest framework.  
        This function will delete them so you are 
        starting with a clean slate
    """
    configargparse._parsers = {}
