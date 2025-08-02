import sys
import configargparse
import ct.wrappedos
import ct.utils
import ct.headerdeps


def main(argv=None):
    cap = configargparse.getArgumentParser()
    cap.add("filename", help='File to use in "$CPP $CPPFLAGS -MM filename"', nargs="+")

    # This will add the common arguments as a side effect
    ct.headerdeps.add_arguments(cap)
    args = ct.apptools.parseargs(cap, argv)
    hh = ct.headerdeps.CppHeaderDeps(args)

    if not ct.wrappedos.isfile(args.filename[0]):
        sys.stderr.write(
            "The supplied filename ({0}) isn't a file. "
            " Did you spell it correctly?  "
            "Another possible reason is that you didn't supply a filename and "
            "that configargparse has picked an unused positional argument from "
            "the config file.\n".format(args.filename[0])
        )
        return 1

    results = []
    for fname in args.filename:
        results.extend(hh.process(fname))
    results = ct.utils.ordered_unique(results)

    for dep in results:
        print(dep)

    return 0
