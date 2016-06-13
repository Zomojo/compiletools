import sys
import argparse
import fnmatch
import os
import ct.utils


def find_possible_variants(
        user_home_dir=None,
        system_config_dir=None,
        argv=None):
    output = [
        "From highest to lowest priority configuration directories, the possible variants are: "]
    for cfg_dir in ct.utils.default_config_directories(
            user_home_dir=user_home_dir,
            system_config_dir=system_config_dir,
            argv=argv):
        output.append(cfg_dir)
        try:
            for cfg_file in os.listdir(cfg_dir):
                if fnmatch.fnmatch(cfg_file, '*.conf'):
                    output.append("\t" + os.path.splitext(cfg_file)[0])
        except:
            output.append("\tNone found")

    return output
