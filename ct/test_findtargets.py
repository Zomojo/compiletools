import os
import unittest
import configargparse

import ct.unittesthelper as uth
import ct.utils
import ct.findtargets


class TestFindTargetsModule(unittest.TestCase):
    def setUp(self):
        uth.reset()

    def _find_samples_targets(self, disable_tests, disable_exes=False):
        relativeexpectedexes = {
            "dottypaths/dottypaths.cpp",
            "library/main.cpp",
            "lotsofmagic/lotsofmagic.cpp",
            "magicinclude/main.cpp",
            "magicpkgconfig/main.cpp",
            "magicsourceinheader/main.cpp",
            "movingheaders/main.cpp",
            "nestedconfig/nc.cpp",
            "nestedconfig/subdir/nc.cpp",
            "pkgconfig/main.cpp",
            "simple/helloworld_c.c",
            "simple/helloworld_cpp.cpp",
        }
        relativeexpectedtests = {
            "cross_platform/test_source.cpp",
            "factory/test_factory.cpp",
            "numbers/test_direct_include.cpp",
            "numbers/test_library.cpp",
            "simple/test_cflags.c",
        }

        expectedexes = set()
        if not disable_exes:
            expectedexes = {
                os.path.realpath(os.path.join(uth.samplesdir(), exe))
                for exe in relativeexpectedexes
            }
        expectedtests = set()
        if not disable_tests:
            expectedtests = {
                os.path.realpath(os.path.join(uth.samplesdir(), tt))
                for tt in relativeexpectedtests
            }

        config_files = ct.configutils.config_files_from_variant(
            exedir=uth.cakedir(), argv=[]
        )
        cap = configargparse.getArgumentParser(
            description="TestFindTargetsModule",
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            default_config_files=config_files,
            args_for_setting_config_path=["-c", "--config"],
            ignore_unknown_config_file_keys=True,
        )
        ct.findtargets.add_arguments(cap)
        argv = ["--shorten"]
        if disable_tests:
            argv.append("--disable-tests")
        if disable_exes:
            argv.append("--disable-exes")
        args = ct.apptools.parseargs(cap, argv=argv)
        findtargets = ct.findtargets.FindTargets(args, exedir=uth.cakedir())
        executabletargets, testtargets = findtargets(path=uth.cakedir())
        self.assertSetEqual(expectedexes, set(executabletargets))
        self.assertSetEqual(expectedtests, set(testtargets))

    def test_samples(self):
        self._find_samples_targets(disable_tests=False)

    def test_disable_tests(self):
        self._find_samples_targets(disable_tests=True)

    def test_tests_only(self):
        self._find_samples_targets(disable_tests=False, disable_exes=True)

    def tearDown(self):
        uth.reset()
