from __future__ import print_function
from __future__ import unicode_literals

import sys
import argparse
import fnmatch
import os
import ct.configutils


def find_possible_variants(
        user_config_dir=None,
        system_config_dir=None,
        exedir=None,
        args=None,
        verbose=0):
    output = ["Variant aliases are:"]
    output.append(
        ct.configutils.extract_item_from_ct_conf(
            key='variantaliases',
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir,
            verbose=verbose))
    output.append(
        "\nFrom highest to lowest priority configuration directories, the possible variants are: ")
    if args and args.repoonly:
        search_directories = [os.getcwd(), ct.git_utils.find_git_root()]
    else:
        search_directories = ct.configutils.default_config_directories(
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir,
            verbose=verbose)

    for cfg_dir in search_directories:
        output.append(cfg_dir)
        cfgs = []
        try:
            for cfg_file in os.listdir(cfg_dir):
                if fnmatch.fnmatch(cfg_file, '*.conf'):
                    cfgs.append("\t" + os.path.splitext(cfg_file)[0])
        except OSError:
            pass

        if not cfgs:
            output.append("\tNone found")
        else:
            output.extend(sorted(cfgs))
    return output
