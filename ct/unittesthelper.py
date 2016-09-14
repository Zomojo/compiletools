from __future__ import unicode_literals
from __future__ import print_function
import configargparse
import os
import ct.apptools

def reset():
    delete_existing_parsers()
    ct.apptools.resetcallbacks()

def delete_existing_parsers():
    """ The singleton parsers supplied by configargparse
        don't play well with the unittest framework.
        This function will delete them so you are
        starting with a clean slate
    """
    configargparse._parsers = {}


def ctdir():
    return os.path.dirname(os.path.realpath(__file__))

def cakedir():
    return os.path.realpath(os.path.join(ctdir(), ".."))

def samplesdir():
    return os.path.realpath(os.path.join(ctdir(), "../samples"))
