from __future__ import print_function
from __future__ import unicode_literals

import configargparse
import ct.apptools
import psutil

def _cpus():
    thisprocess = psutil.Process()
    return len(thisprocess.cpu_affinity())

def add_arguments(cap):
    cap.add(
        "-j",
        "--jobs",
        "--CAKE_PARALLEL",
        "--parallel",
        dest='parallel',
        type=int,
        default=_cpus(),
        help="Sets the number of CPUs to use in parallel for a build.")
        

def main(argv=None):
    cap = configargparse.getArgumentParser()
    ct.apptools.add_base_arguments(cap)
    add_arguments(cap)
    args = cap.parse_args(args=argv)
    if args.verbose >= 2:
        ct.apptools.verbose_print_args(args)
    print(args.parallel)

    return 0
