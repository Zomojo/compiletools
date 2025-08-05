import sys
import configargparse
import compiletools.wrappedos
import compiletools.utils
import compiletools.headerdeps


def main(argv=None):
    cap = configargparse.getArgumentParser()
    cap.add("filename", help='File to use in "$CPP $CPPFLAGS -MM filename"', nargs="+")

    # This will add the common arguments as a side effect
    compiletools.headerdeps.add_arguments(cap)
    args = compiletools.apptools.parseargs(cap, argv)
    hh = compiletools.headerdeps.CppHeaderDeps(args)

    if not compiletools.wrappedos.isfile(args.filename[0]):
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
    results = compiletools.utils.ordered_unique(results)

    for dep in results:
        print(dep)

    return 0
