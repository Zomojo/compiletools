from __future__ import print_function
from __future__ import unicode_literals

import subprocess
import sys
import ct.utils


class PreProcessor(object):

    """ Make it easy to call the C Pre Processor """

    def __init__(self, args):
        self.args = args

    @staticmethod
    def add_arguments(cap):
        ct.apptools.add_common_arguments(cap)

    def process(self, realpath, extraargs, redirect_stderr_to_stdout=False):
        cmd = self.args.CPP.split() + self.args.CPPFLAGS.split() + \
            extraargs.split()
        if ct.utils.isheader(realpath):
            # Use /dev/null as the dummy source file.
            cmd.extend(["-include", realpath, "-x", "c++", "/dev/null"])
        else:
            cmd.append(realpath)

        if self.args.verbose >= 3:
            print(" ".join(cmd))

        try:
            kwargs = {'universal_newlines': True}
            if redirect_stderr_to_stdout:
                kwargs['stderr'] = subprocess.STDOUT

            output = subprocess.check_output(cmd, **kwargs)
            if self.args.verbose >= 5:
                print(output)
        except OSError as err:
            print(
                " ".join(["Failed to preprocess", filename, " error=", err]), file=sys.stderr)
            exit()
        return output
