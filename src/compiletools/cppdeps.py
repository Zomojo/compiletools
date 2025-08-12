import sys
import configargparse
import compiletools.wrappedos
import compiletools.utils
import compiletools.headerdeps
import compiletools.configutils
import compiletools.apptools


def main(argv=None):
    variant = compiletools.configutils.extract_variant(argv=argv)
    config_files = compiletools.configutils.config_files_from_variant(variant=variant, argv=argv)
    cap = configargparse.getArgumentParser(
        description="Show C/C++ header dependencies using cpp -MM",
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        auto_env_var_prefix="",
        default_config_files=config_files,
        args_for_setting_config_path=["-c", "--config"],
        ignore_unknown_config_file_keys=True,
    )
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
