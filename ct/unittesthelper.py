from __future__ import unicode_literals
from __future__ import print_function
import configargparse
import os
from io import open
import tempfile
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

def create_temp_config(tempdir=None):
    """ User is responsible for removing the config file when 
        they are finished 
    """
    try:
        CC=os.environ['CC']
        CXX=os.environ['CXX']
    except KeyError:
        CC='gcc'
        CXX='g++'
        
    tf_handle, tf_name = tempfile.mkstemp(suffix=".conf", text=True, dir=tempdir)
    with open(tf_name,'w') as ff:
        ff.write('ID=GNU\n')
        ff.write('CC=' + CC + '\n')
        ff.write('CXX=' + CXX + '\n')
        ff.write('CPPFLAGS="-std=c++11"\n')
    return tf_name

