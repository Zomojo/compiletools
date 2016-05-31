#! /usr/bin/env python

from __future__ import print_function
import unittest
import configargparse


def add_to_parser_in_func(recursion_depth=0):
    if recursion_depth < 6:
        cap = configargparse.getArgumentParser()
        cap.add(
            "-v",
            "--verbose",
            help="Output verbosity. Add more v's to make it more verbose",
            action="count",
            default=0)
        args = cap.parse_known_args()
        cap.add(
            "-c",
            "--config",
            is_config_file=True,
            help="Manually specify the config file path if you want to override the variant default")
        add_to_parser_in_func(recursion_depth+1)
        args = cap.parse_known_args()

class TestConfigArgParse(unittest.TestCase):

    def test_multiple_parse_known_args(self):
        non_existent_config_files = ['/blah/foo.conf','/usr/bin/ba.conf']
        cap = configargparse.getArgumentParser(
            description='unit testing',
            formatter_class=configargparse.DefaultsRawFormatter,
            default_config_files=non_existent_config_files)

        cap.add(
            "--variant",
            help="Specifies which variant of the config should be used. Use the config name without the .conf",
            default="debug")
        args = cap.parse_known_args()

        add_to_parser_in_func()

        cap.add(
            "-c",
            "--config",
            is_config_file=True,
            help="Manually specify the config file path if you want to override the variant default")
        args = cap.parse_known_args()
        
if __name__ == '__main__':
    unittest.main()
