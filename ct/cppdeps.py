from __future__ import unicode_literals
from __future__ import print_function
import sys
import configargparse
import ct.wrappedos
import ct.utils
from ct.hunter import HeaderDependencies


def main(argv=None):
    if argv is None:
        argv = sys.argv
    cap = configargparse.getArgumentParser()
    cap.add(
        "-c",
        "--config",
        is_config_file=True,
        help="Manually specify the config file path if you want to override the variant default")
    cap.add(
        "filename",
        help='File to use in "$CPP $CPPFLAGS -MM filename"',
        nargs='+')

    # This will add the common arguments as a side effect
    HeaderDependencies.add_arguments(cap)
    hh = HeaderDependencies(argv)
    myargs = cap.parse_known_args(argv[1:])
    ct.utils.verbose_print_args(myargs[0])

    if not ct.wrappedos.isfile(myargs[0].filename[0]):
        sys.stderr.write(
            "The supplied filename ({0}) isn't a file. "
            " Did you spell it correctly?  "
            "Another possible reason is that you didn't supply a filename and "
            "that configargparse has picked an unused positional argument from "
            "the config file.\n".format(
                myargs[0].filename[0]))
        return 1

    results = set()
    for fname in myargs[0].filename:
        results |= hh.process(fname)

    for dep in results:
        print(dep)

    return 0
