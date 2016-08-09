import sys
import argparse
import fnmatch
import os
import ct.configutils


def find_possible_variants(
        user_config_dir=None,
        system_config_dir=None,
        exedir=None):
    output = [
        "From highest to lowest priority configuration directories, the possible variants are: "]
    for cfg_dir in ct.configutils.default_config_directories(
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir):
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
            output.extend(cfgs)

    return output
