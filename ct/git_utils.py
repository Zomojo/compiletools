import os
import subprocess

from ct.memoize import memoize


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
    try:
        # Redirect stderr to stdout (which is captured) rather than
        # have it spew over the console
        git_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.STDOUT,
            universal_newlines=True).strip('\n')
    except subprocess.CalledProcessError:
        # An exception means we aren't in a real git repository.
        # But are we in a fake git repository? (i.e., there exists a dummy .git
        # file)
        trialgitroot = directory

        while (trialgitroot != "/"):
            if (os.path.exists(trialgitroot + "/.git")):
                git_root = trialgitroot
                break
            trialgitroot = os.path.dirname(trialgitroot)
    finally:
        os.chdir(original_cwd)
    return git_root


@memoize
def strip_git_root(filename):
    size = len(find_git_root(filename)) + 1
    return filename[size:]


class NameAdjuster(object):

    """ Conditionally remove the git root from a given filename """

    def __init__(self, strip_git_root):
        self.strip_git_root = strip_git_root

    def adjust(self, name):
        if self.strip_git_root:
            return strip_git_root(name)
        else:
            return name
