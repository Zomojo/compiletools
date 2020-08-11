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
    return os.path.realpath(os.path.join(ctdir(), "samples"))


def ctconfdir():
    return os.path.realpath(os.path.join(ctdir(), "ct.conf.d"))


def create_temp_config(tempdir=None, filename=None):
    """ User is responsible for removing the config file when 
        they are finished 
    """
    try:
        CC = os.environ["CC"]
        CXX = os.environ["CXX"]
    except KeyError:
        CC = "gcc"
        CXX = "g++"

    if not filename:
        tf_handle, filename = tempfile.mkstemp(suffix=".conf", text=True, dir=tempdir)

    with open(filename, "w") as ff:
        ff.write("ID=GNU\n")
        ff.write("CC=" + CC + "\n")
        ff.write("CXX=" + CXX + "\n")
        ff.write('CPPFLAGS="-std=c++11"\n')

    return filename


def create_temp_ct_conf(tempdir, defaultvariant="debug"):
    """ User is responsible for removing the config file when 
        they are finished 
    """
    with open(os.path.join(tempdir, "ct.conf"), "w") as ff:
        # ff.write('CTCACHE = ' + os.path.join(tempdir,'ct-unittest-cache' + '\n'))
        # ff.write('CTCACHE = None' + '\n')
        ff.write(" ".join(["variant =", defaultvariant, "\n"]))
        ff.write("variantaliases = {'dbg':'foo.debug', 'rls':'foo.release'}\n")
        ff.write("exemarkers = [main]" + "\n")
        ff.write("testmarkers = unit_test.hpp" + "\n")
