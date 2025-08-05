#!/usr/bin/env python3
import sys
import configargparse
import compiletools.utils
import compiletools.cake
import compiletools.apptools
import compiletools.configutils


def main(argv=None):
    cap = configargparse.getArgumentParser()
    compiletools.cake.Cake.add_arguments(cap)
    if argv is None:
        # Output of stdout is done via increasing the verbosity
        sys.argv.append("-vvv")
    args = compiletools.apptools.parseargs(cap, argv)

    # Note that when the "--write-out-config-file" is in effect that
    # we never get to this print.  configargparse exits before this which is
    # annoying.
    print()
    return 0


if __name__ == "__main__":
    config_files = compiletools.configutils.config_files_from_variant()
    cap = configargparse.getArgumentParser(
        description="Helper tool for examining how config files, command line "
        "arguments and environment variables are combined. "
        "Write the config to file with -w.",
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        auto_env_var_prefix="",
        default_config_files=config_files,
        args_for_setting_config_path=["-c", "--config"],
        ignore_unknown_config_file_keys=True,
        args_for_writing_out_config_file=["-w", "--write-out-config-file"],
    )
    sys.exit(main())