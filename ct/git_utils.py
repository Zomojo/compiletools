from __future__ import print_function
from __future__ import unicode_literals

import os
import subprocess

from ct.memoize import memoize
import ct.utils

def find_git_root(filename=None):
    """ Return the absolute path of .git for the given filename """
    # Note: You can't memoize this one since the None parameter will
    # return different results as the cwd changes
    if filename:
        directory = os.path.dirname(os.path.realpath(filename))
    else:
        directory = os.getcwd()
    return _find_git_root(directory)


@memoize
def _find_git_root(directory):
    """ Internal function to find the git root but cache it against the given directory """
    original_cwd = os.getcwd()
    os.chdir(directory)

    # Define the git root of a project that isn't under version control to be be cwd
    gitroot = original_cwd
    try:
        # Redirect stderr to stdout (which is captured) rather than
        # have it spew over the console
        gitroot = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.STDOUT,
            universal_newlines=True).strip('\n')
    except (subprocess.CalledProcessError, OSError) as err:
        # A CalledProcessError exception means we aren't in a real git repository.
        # An OSError probably means git isn't installed on this machine.
        # But are we in a fake git repository? (i.e., there exists a dummy .git
        # file)
        trialgitroot = directory

        while (trialgitroot != "/"):
            if (os.path.exists(trialgitroot + "/.git")):
                gitroot = trialgitroot
                break
            trialgitroot = os.path.dirname(trialgitroot)
    finally:
        os.chdir(original_cwd)
    return gitroot


@memoize
def _strip_git_root(filename):
    size = len(find_git_root(filename)) + 1
    return filename[size:]


class Project(object):
    def __init__(self, args):
        self._args = args

    def pathname(self, filename):        
        """ Return the project part of the given filename """
        if self._args.git_root:
            return _strip_git_root(filename)
        else:
            return ct.utils.removemount(filename)


class NameAdjuster(object):

    """ Conditionally remove the git root from a given filename """

    def __init__(self, args):
        self._args = args

    @staticmethod
    def add_arguments(cap):
        ct.utils.add_flag_argument(
            cap,
            "shorten",
            'strip_git_root',
            default=False,
            help="Strip the git root from the filenames")

    def adjust(self, name):
        if self._args.strip_git_root:
            return _strip_git_root(name)
        else:
            return name
