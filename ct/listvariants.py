from __future__ import print_function
from __future__ import unicode_literals

import sys
import argparse
import fnmatch
import os
import ct.configutils
import ct.utils
from ct.version import __version__


def add_arguments(parser):
    parser.add(
        "-v",
        "--verbose",
        help="Output verbosity. Add more v's to make it more verbose",
        action="count",
        default=0)
    parser.add(
        "-q",
        "--quiet",
        help="Decrement verbosity. Useful in apps where the default verbosity > 0.",
        action="count",
        default=0)
    parser.add(
        "--version",
        action="version",
        version=__version__)
    parser.add(
        "-?",
        action='help',
        help='Help')

    ct.utils.add_boolean_argument(
          parser
        , "repoonly"
        , default=False
        , help="Restrict the results to the local repository config files")

    
    # Figure out what style classes are available and add them to the command
    # line options
    styles = [st[:-5].lower()
              for st in dict(globals()) if st.endswith('Style')]
    parser.add(
        '--style',
        choices=styles,
        default='pretty',
        help="Output formatting style")

class PrettyStyle(object):
    def __init__(self):
        self.output = ""

    def append_text(self, text):
        self.output += text + '\n'

    def append_variant(self, variant):
        self.output += '\t' + variant + '\n'



class FlatStyle(object):
    def __init__(self):
        self.output = ""

    def append_text(self, text):
        pass

    def append_variant(self, variant):
        self.output += variant + ' '


def find_possible_variants(
        user_config_dir=None,
        system_config_dir=None,
        exedir=None,
        args=None,
        verbose=0):

    stylename = "Pretty"
    if args and args.style:
        stylename = args.style
    styleclass = globals()[stylename.title() + 'Style']
    style = styleclass()

    style.append_text("Variant aliases are:")
    style.append_text(
        ct.configutils.extract_item_from_ct_conf(
            key='variantaliases',
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir,
            verbose=verbose))
    style.append_text(
        "\nFrom highest to lowest priority configuration directories, the possible variants are: ")

    if args and args.repoonly:
        search_directories = ct.utils.OrderedSet([os.getcwd(), ct.git_utils.find_git_root()])
    else:
        search_directories = ct.configutils.default_config_directories(
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir,
            verbose=verbose)

    for cfg_dir in search_directories:
        found = False
        style.append_text(cfg_dir)
        try:
            for cfg_file in os.listdir(cfg_dir):
                if fnmatch.fnmatch(cfg_file, '*.conf'):
                    style.append_variant(os.path.splitext(cfg_file)[0])
                    found = True
        except OSError:
            pass

        if not found:
            style.append_text("\tNone found")

    return style.output
