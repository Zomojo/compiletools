from __future__ import print_function
from __future__ import unicode_literals

import configargparse
import ct.utils

def _cpus():
    with open("/proc/cpuinfo") as ff:
        proclines = [
            line for line in ff.readlines() if line.startswith("processor")]
    if 0 == len(proclines):
        return 1
    else:
        return len(proclines)

def add_arguments(cap):
    cap.add(
        "-j",
        "--jobs",
        "--CAKE_PARALLEL",
        "--parallel",
        dest='parallel',
        type=int,
        default=2*_cpus(),
        help="Sets the number of CPUs to use in parallel for a build.  Defaults to 2 * all cpus.")
        

def main(argv=None):
    cap = configargparse.getArgumentParser()
    ct.utils.add_base_arguments(cap)
    add_arguments(cap)
    args = cap.parse_args(args=argv)
    ct.utils.verbose_print_args(cap, args)
    print(args.parallel)

    return 0
