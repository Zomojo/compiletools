import subprocess
import sys
import compiletools.utils


class PreProcessor(object):
    """Make it easy to call the C Pre Processor"""

    def __init__(self, args):
        self.args = args

    @staticmethod
    def add_arguments(cap):
        compiletools.apptools.add_common_arguments(cap)

    def process(self, realpath, extraargs, redirect_stderr_to_stdout=False):
        cmd = self.args.CPP.split() + self.args.CPPFLAGS.split() + extraargs.split()
        if compiletools.utils.isheader(realpath):
            # Use /dev/null as the dummy source file.
            cmd.extend(["-include", realpath, "-x", "c++", "/dev/null"])
        else:
            cmd.append(realpath)

        if self.args.verbose >= 3:
            print(" ".join(cmd))

        try:
            kwargs = {"universal_newlines": True}
            if redirect_stderr_to_stdout:
                kwargs["stderr"] = subprocess.STDOUT

            output = subprocess.check_output(cmd, **kwargs)
            if self.args.verbose >= 5:
                print(output)
        except OSError as err:
            print(
                "Failed to preprocess {0}. Error={1}".format(realpath, err),
                file=sys.stderr,
            )
            raise err
        except subprocess.CalledProcessError as err:
            print(
                "Preprocessing failed for {0}. Return code={1}, Output={2}".format(
                    realpath, err.returncode, err.output
                ),
                file=sys.stderr,
            )
            raise err

        return output
