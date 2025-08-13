#!/usr/bin/env python3
import sys
import configargparse
import compiletools.utils
import compiletools.cake
import compiletools.apptools
import compiletools.configutils


def main(argv=None):
    cap = compiletools.apptools.create_parser("Configuration examination tool", argv=argv, include_config=False)
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
    cap = compiletools.apptools.create_parser(
        "Helper tool for examining how config files, command line "
        "arguments and environment variables are combined. "
        "Write the config to file with -w.",
        include_write_config=True
    )
    sys.exit(main())