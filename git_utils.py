import os
import subprocess
from memoize import memoize


def find_git_root(filename=None):
    """ Return the absolute path of .git for the given filename """
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
    git_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip('\n')
    os.chdir(original_cwd)
    return git_root


@memoize
def strip_git_root(filename):
    size = len(find_git_root(filename)) + 1
    return filename[size:]
