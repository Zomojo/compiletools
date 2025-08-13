import sys
import configargparse
import fnmatch
import os
import compiletools.configutils
import compiletools.utils
from compiletools.version import __version__


def add_arguments(parser):
    compiletools.utils.add_boolean_argument(
        parser,
        "configname",
        default=False,
        help="Print the .conf at the end of the variant",
    )

    compiletools.utils.add_boolean_argument(
        parser,
        "repoonly",
        default=False,
        help="Restrict the results to the local repository config files",
    )

    compiletools.utils.add_boolean_argument(
        parser,
        "shorten",
        default=True,
        help="Shorten from the full path to the config filenames to only the variant name",
    )

    # Figure out what style classes are available and add them to the command
    # line options
    styles = [st[:-5].lower() for st in dict(globals()) if st.endswith("Style")]
    parser.add(
        "--style", choices=styles, default="pretty", help="Output formatting style"
    )


class PrettyStyle(object):
    def __init__(self):
        self.output = ""

    def append_text(self, text):
        if text is None:
            text = ""
        self.output += text + "\n"

    def append_variants(self, variants):
        if not variants:
            self.output += "    None found\n"
        else:
            for vv in sorted(variants):
                self.output += "    " + vv + "\n"


class FlatStyle(object):
    def __init__(self):
        self.output = ""

    def append_text(self, text):
        pass

    def append_variants(self, variants):
        for vv in sorted(variants):
            self.output += vv + " "


class FilelistStyle(object):
    def __init__(self):
        self.output = ""

    def append_text(self, text):
        pass

    def append_variants(self, variants):
        for vv in sorted(variants):
            self.output += vv + "\n"


def find_possible_variants(
    user_config_dir=None, system_config_dir=None, exedir=None, args=None, verbose=0, gitroot=None
):

    stylename = "Pretty"
    if args and args.style:
        stylename = args.style
    styleclass = globals()[stylename.title() + "Style"]
    style = styleclass()

    shorten = True
    if args and not args.shorten:
        shorten = False

    repoonly = False
    if args:
        repoonly = args.repoonly

    confext = ""
    if args:
        if args.configname:
            confext = ".conf"
            removeconf = ""
        else:
            removeconf = ".conf"

    style.append_text("Variant aliases are:")
    style.append_text(
        compiletools.configutils.extract_item_from_ct_conf(
            key="variantaliases",
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir,
            verbose=verbose,
            gitroot=gitroot,
        )
    )
    style.append_text(
        "From highest to lowest priority configuration directories, the possible variants are:"
    )

    search_directories = compiletools.configutils.default_config_directories(
        user_config_dir=user_config_dir,
        system_config_dir=system_config_dir,
        exedir=exedir,
        repoonly=repoonly,
        verbose=verbose,
        gitroot=gitroot,
    )

    for cfg_dir in search_directories:
        found = []
        style.append_text(cfg_dir)
        try:
            for cfg_file in os.listdir(cfg_dir):
                if fnmatch.fnmatch(cfg_file, "*.conf"):
                    if shorten:
                        if repoonly:
                            found.append(
                                compiletools.git_utils.strip_git_root(
                                    os.path.join(
                                        cfg_dir, cfg_file.replace(removeconf, "")
                                    )
                                )
                            )
                        else:
                            found.append(os.path.splitext(cfg_file)[0] + confext)
                    else:
                        found.append(os.path.join(cfg_dir, cfg_file))

        except OSError:
            pass

        style.append_variants(found)

    return style.output

def main(argv=None):
    cap = compiletools.apptools.create_parser("List available build variants", argv=argv, include_config=False)
    add_arguments(cap)
    args = cap.parse_args(args=argv)
    print(compiletools.listvariants.find_possible_variants(args=args, verbose=args.verbose))
    return 0
