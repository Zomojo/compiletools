import configargparse
import ct.apptools
import os
import platform


def _determine_system():
    system = platform.system().lower()
    if platform.system() == "Linux":
        try:
            # A Termux fingerprint is that it
            # doesn't have permissions for /proc/stat
            os.stat("/proc/stat")
        except PermissionError:
            system = "termux"
    return system


def _cpus_linux():
    import psutil

    thisprocess = psutil.Process()
    return len(thisprocess.cpu_affinity())


def _cpus_termux():
    # Termux can't import psutil without double exceptions
    # which is why we use nproc
    import subprocess

    return subprocess.run(
        ["nproc"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    ).stdout.rstrip()


def _cpus_darwin():
    # psutil isn't supported on Darwin and
    # nproc isn't installed by default
    import subprocess

    return subprocess.run(
        ["sysctl", "-n", "hw.ncpu"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    ).stdout.rstrip()


def _cpu_count():
    try:
        cpu_func = globals()["_".join(["_cpus", _determine_system()])]
        return cpu_func()
    except KeyError:
        # A safe-ish default even for phones
        return 4


def add_arguments(cap):
    cap.add(
        "-j",
        "--jobs",
        "--CAKE_PARALLEL",
        "--parallel",
        dest="parallel",
        type=int,
        default=_cpu_count(),
        help="Sets the number of CPUs to use in parallel for a build.",
    )


def main(argv=None):
    cap = configargparse.getArgumentParser()
    ct.apptools.add_base_arguments(cap)
    add_arguments(cap)
    args = cap.parse_args(args=argv)
    if args.verbose >= 2:
        ct.apptools.verbose_print_args(args)
    print(args.parallel)

    return 0
