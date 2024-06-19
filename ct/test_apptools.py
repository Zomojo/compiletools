import unittest
import ct.apptools
import ct.unittesthelper as uth
import ct.uth_reload as uthr
import os
import argparse  # Used for the parse_args test
import configargparse


class FakeNamespace(object):
    def __init__(self):
        self.n1 = "v1_noquotes"
        self.n2 = '"v2_doublequotes"'
        self.n3 = "'v3_singlequotes'"
        self.n4 = '''"''v4_lotsofquotes''"'''

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


class TestFuncs(unittest.TestCase):
    def test_strip_quotes(self):
        fns = FakeNamespace()
        ct.apptools._strip_quotes(fns)
        self.assertEqual(fns.n1, "v1_noquotes")
        self.assertEqual(fns.n2, "v2_doublequotes")
        self.assertEqual(fns.n3, "v3_singlequotes")
        self.assertEqual(fns.n4, "v4_lotsofquotes")

    def test_parse_args_strips_quotes(self):
        cmdline = [
            '--append-CPPFLAGS="-DNEWPROTOCOL -DV172"',
            '--append-CXXFLAGS="-DNEWPROTOCOL -DV172"',
        ]
        ap = argparse.ArgumentParser()
        ap.add_argument("--append-CPPFLAGS", action="append")
        ap.add_argument("--append-CXXFLAGS", action="append")
        args = ap.parse_args(cmdline)
        ct.apptools._strip_quotes(args)
        self.assertEqual(args.append_CPPFLAGS, ["-DNEWPROTOCOL -DV172"])
        self.assertEqual(args.append_CXXFLAGS, ["-DNEWPROTOCOL -DV172"])


class TestConfig(unittest.TestCase):
    def test_user_config_append_cxxflags(self):
        uthr.reload_ct("None")

        with uth.TempDirContext():
            uth.create_temp_ct_conf(os.getcwd())
            cfgfile = "foo.dbg.conf"
            uth.create_temp_config(os.getcwd(), cfgfile, extralines=['APPEND_CXXFLAGS="-fdiagnostics-color=always"', 'append_CXXFLAGS="-fdiagnostics-color=always"'])
            with open(cfgfile, "r") as ff:
                print(ff.read())
            argv = ["--config=foo.dbg.conf", "-vvvvvvvvvv"]
            #variant = ct.configutils.extract_variant(argv=argv)
            #print(f"{variant=}")
            #config_files = ct.configutils.config_files_from_variant(variant=variant, argv=argv)
            #print(config_files)



            cap = configargparse.getArgumentParser(
                description="Test reading and overriding configs",
                formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
                auto_env_var_prefix="",
                default_config_files=["ct.conf"],
                args_for_setting_config_path=["-c", "--config"],
                ignore_unknown_config_file_keys=True,
            )
            ct.apptools.add_common_arguments(cap)
            ct.apptools.add_link_arguments(cap)
            print(cap.format_help())
            args = ct.apptools.parseargs(cap, argv)
            print(args)


if __name__ == "__main__":
    unittest.main()
