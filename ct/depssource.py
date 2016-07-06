from __future__ import print_function
import sys
import configargparse
import ct.wrappedos
import ct.utils
from ct.hunter import Hunter


def main(argv=None):
    if argv is None:
        argv = sys.argv

    cap = configargparse.getArgumentParser()
    cap.add(
        "filename",
        help='File to find source dependencies for."',
        nargs='+')
    hunter = Hunter(argv)

    myargs = cap.parse_known_args(args=argv[1:])
    ct.utils.verbose_print_args(myargs[0])

    for filename in myargs[0].filename:
        print(filename)
        for source in hunter.required_source_files(ct.wrappedos.realpath(filename)):
            print("\t",source)

    return 0
