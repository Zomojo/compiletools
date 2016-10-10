""" Wrap and memoize a variety of os calls """
import os
import shutil
from ct.memoize import memoize


@memoize
def getmtime(realpath):
    """ Cached version of os.path.getmtime """
    return os.path.getmtime(realpath)


@memoize
def isfile(trialpath):
    """ Cached version of os.path.isfile """
    return os.path.isfile(trialpath)


@memoize
def isdir(trialpath):
    """ Cached version of os.path.isdir """
    return os.path.isdir(trialpath)


@memoize
def realpath(trialpath):
    """ Cache os.path.realpath """
    # Note: We can't raise an exception on file non-existence 
    # because this is sometimes called in order to create the file.
    rp = os.path.realpath(trialpath)
    return rp


@memoize
def dirname(trialpath):
    """ A cached verion of os.path.dirname """
    return os.path.dirname(trialpath)


def isc(trialpath):
    """ Is the given file a C file ? """
    return os.path.splitext(trialpath)[1] == ".c"


def makedirs(path):
    """ When we no longer have to support Python 2.7 use the following instead:
        os.makedirs(path, exist_ok=True)
    """
    if isdir(path):
        return
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise

def copy(src, dest):
    """ copy the src to the dest and print any errors """
    try:
        shutil.copy2(src, dest)
    except IOError as err:
        print("Unable to copy file {}".format(err))
