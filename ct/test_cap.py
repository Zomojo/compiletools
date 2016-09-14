from __future__ import print_function
from __future__ import unicode_literals

import unittest

import configargparse

import ct.unittesthelper as uth


def add_to_parser_in_func(recursion_depth=0):
    if recursion_depth < 6:
        cap = configargparse.getArgumentParser()
        cap.add(
            "-v",
            "--verbose",
            help="Output verbosity. Add more v's to make it more verbose",
            action="count",
            default=0)
        parsed_args = cap.parse_known_args(args=["-v"])

        # Note that is_config_file is False
        # The unit test fails if it is set to True
        # I wanted this knowledge to be written down somewhere
        # hence the reason for this unit tests existence
        cap.add(
            "-c",
            "--cfg",
            is_config_file=False,
            help="Manually specify the config file path if you want to override the variant default")
        add_to_parser_in_func(recursion_depth + 1)
        parsed_args = cap.parse_known_args(args=["-v"])


class TestConfigArgParse(unittest.TestCase):
    def setUp(self):
        uth.reset()

    def test_multiple_parse_known_args(self):
        non_existent_config_files = ['/blah/foo.conf', '/usr/bin/ba.conf']
        cap = configargparse.getArgumentParser(
            prog='UnitTest',
            description='unit testing',
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            default_config_files=non_existent_config_files,
            args_for_setting_config_path=["-c","--config"])

        cap.add(
            "--variant",
            help="Specifies which variant of the config should be used. Use the config name without the .conf",
            default="debug")
        parsed_args = cap.parse_known_args()

        add_to_parser_in_func()

        cap.add(
            "-c",
            "--cfg",
            is_config_file=True,
            help="Manually specify the config file path if you want to override the variant default")
        parsed_args = cap.parse_known_args(args=['--variant', 'release'])

    def tearDown(self):
        uth.reset()


if __name__ == '__main__':
    unittest.main()
