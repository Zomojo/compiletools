import compiletools.apptools
import compiletools.unittesthelper as uth
import compiletools.uth_reload as uthr
import os
import argparse  # Used for the parse_args test
import configargparse

from importlib import reload


class FakeNamespace(object):
    def __init__(self):
        self.n1 = "v1_noquotes"
        self.n2 = '"v2_doublequotes"'
        self.n3 = "'v3_singlequotes'"
        self.n4 = '''"''v4_lotsofquotes''"'''

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


class TestFuncs:
    def test_strip_quotes(self):
        fns = FakeNamespace()
        compiletools.apptools._strip_quotes(fns)
        assert fns.n1 == "v1_noquotes"
        assert fns.n2 == "v2_doublequotes"
        assert fns.n3 == "v3_singlequotes"
        assert fns.n4 == "v4_lotsofquotes"

    def test_parse_args_strips_quotes(self):
        cmdline = [
            "--append-CPPFLAGS",
            '"-DNEWPROTOCOL -DV172"',
            "--append-CXXFLAGS",
            '"-DNEWPROTOCOL -DV172"',
        ]
        ap = argparse.ArgumentParser()
        ap.add_argument("--append-CPPFLAGS", action="append")
        ap.add_argument("--append-CXXFLAGS", action="append")
        args = ap.parse_args(cmdline)

        compiletools.apptools._strip_quotes(args)
        assert args.append_CPPFLAGS == ["-DNEWPROTOCOL -DV172"]
        assert args.append_CXXFLAGS == ["-DNEWPROTOCOL -DV172"]


class TestConfig:
    def setup_method(self):
        uth.reset()

    def _test_variable_handling_method(self, variable_handling_method):
        """If variable_handling_method is set to "override" (default as at 20240917) then
        command-line values override environment variables which override config file values which override defaults.
        If variable_handling_method is set to "append" then variables are appended.
        """
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.apptools)

        with uth.TempDirContext(), uth.EnvironmentContext(
            {"CXXFLAGS": "-fdiagnostics-color=always -DVARFROMENV"}
        ):
            uth.create_temp_ct_conf(os.getcwd(), extralines=[f"variable-handling-method={variable_handling_method}"])
            cfgfile = "foo.dbg.conf"
            uth.create_temp_config(os.getcwd(), cfgfile, extralines=['CXXFLAGS="-DVARFROMFILE"'])
            with open(cfgfile, "r") as ff:
                print(ff.read())
            argv = ["--config=foo.dbg.conf", "-v"]
            variant = compiletools.configutils.extract_variant(argv=argv, gitroot=os.getcwd())
            config_files = compiletools.configutils.config_files_from_variant(variant=variant, argv=argv, gitroot=os.getcwd())

            cap = configargparse.getArgumentParser(
                description="Test environment overrides config",
                formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
                auto_env_var_prefix="",
                default_config_files=["ct.conf"],
                args_for_setting_config_path=["-c", "--config"],
                ignore_unknown_config_file_keys=True,
            )
            compiletools.apptools.add_common_arguments(cap)
            compiletools.apptools.add_link_arguments(cap)
            # print(cap.format_help())
            args = compiletools.apptools.parseargs(cap, argv)
            # print(args)
            # Check that the environment variable overrode the config file
            assert variable_handling_method == args.variable_handling_method
            if variable_handling_method == "override":
                assert "-DVARFROMENV" in args.CXXFLAGS
                assert "-DVARFROMFILE" not in args.CXXFLAGS
            elif variable_handling_method == "append":
                assert "-DVARFROMENV" in args.CXXFLAGS
                assert "-DVARFROMFILE" in args.CXXFLAGS
            else:
                assert not "Unknown variable handling method.  Must be override or append."

    def test_environment_overrides_config(self):
        self._test_variable_handling_method(variable_handling_method="override")

    def test_environment_appends_config(self):
        self._test_variable_handling_method(variable_handling_method="append")

    def test_user_config_append_cxxflags(self):
        with uth.EnvironmentContext({"CTCACHE": "None"}):
            reload(compiletools.dirnamer)
            reload(compiletools.apptools)

        with uth.TempDirContext():
            uth.create_temp_ct_conf(os.getcwd())
            cfgfile = "foo.dbg.conf"
            uth.create_temp_config(os.getcwd(), cfgfile, extralines=['append-CXXFLAGS="-fdiagnostics-color=always"'])
            with open(cfgfile, "r") as ff:
                print(ff.read())
            argv = ["--config=" + cfgfile, "-v"]
            variant = compiletools.configutils.extract_variant(argv=argv, gitroot=os.getcwd())
            config_files = compiletools.configutils.config_files_from_variant(variant=variant, argv=argv, gitroot=os.getcwd())

            cap = configargparse.getArgumentParser(
                description="Test reading and overriding configs",
                formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
                auto_env_var_prefix="",
                default_config_files=["ct.conf"],
                args_for_setting_config_path=["-c", "--config"],
                ignore_unknown_config_file_keys=True,
            )
            compiletools.apptools.add_common_arguments(cap)
            compiletools.apptools.add_link_arguments(cap)
            # print(cap.format_help())
            args = compiletools.apptools.parseargs(cap, argv)
            # print(args)
            # Check that the append-CXXFLAGS argument made its way into the CXXFLAGS
            assert "-fdiagnostics-color=always" in args.CXXFLAGS


