import os
import unittest
import shutil
import configargparse
import tempfile

try:
    # This call to reload is simply to test
    # that reload is in the current namespace
    reload(unittest)
except NameError:
    from importlib import reload

import ct.unittesthelper as uth
import ct.dirnamer
import ct.apptools
import ct.headerdeps
import ct.magicflags
from ct.utils import OrderedSet


def _reload_ct(cache_home):
    """ Set the CTCACHE environment variable to cache_home
        and reload the ct.* modules
    """
    os.environ["CTCACHE"] = cache_home
    reload(ct.dirnamer)
    reload(ct.apptools)
    reload(ct.headerdeps)
    reload(ct.magicflags)


class TestMagicFlagsModule(unittest.TestCase):
    def setUp(self):
        uth.reset()

    def _createmagicparser(self, extraargs=None, cache_home="None", tempdir=None):
        if not extraargs:
            extraargs = []
        temp_config_name = ct.unittesthelper.create_temp_config(tempdir)
        argv = ["--config=" + temp_config_name] + extraargs
        _reload_ct(cache_home)
        config_files = ct.configutils.config_files_from_variant(
            argv=argv, exedir=uth.cakedir()
        )
        cap = configargparse.getArgumentParser(
            description="TestMagicFlagsModule",
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            default_config_files=config_files,
            args_for_setting_config_path=["-c", "--config"],
            ignore_unknown_config_file_keys=True,
        )
        ct.apptools.add_common_arguments(cap)
        ct.dirnamer.add_arguments(cap)
        ct.headerdeps.add_arguments(cap)
        ct.magicflags.add_arguments(cap)
        args = ct.apptools.parseargs(cap, argv)
        headerdeps = ct.headerdeps.create(args)
        return ct.magicflags.create(args, headerdeps)

    def test_parsing_CFLAGS(self):
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        relativepath = "simple/test_cflags.c"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(tempdir=tempdir)
        # magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            set(magicparser.parse(realpath).get("CFLAGS")), set(["-std=gnu99"])
        )

        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)

    def test_SOURCE_direct(self):
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        relativepath = "cross_platform/cross_platform.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(["--magic", "direct"], tempdir=tempdir)
        # magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            set(magicparser.parse(realpath).get("SOURCE")),
            {
                os.path.join(samplesdir, "cross_platform/cross_platform_lin.cpp"),
                os.path.join(samplesdir, "cross_platform/cross_platform_win.cpp"),
            },
        )

        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)

    def test_SOURCE_cpp(self):
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        relativepath = "cross_platform/cross_platform.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(["--magic", "cpp"], tempdir=tempdir)
        # magicparser._headerdeps.process(realpath)
        self.assertSetEqual(
            set(magicparser.parse(realpath).get("SOURCE")),
            {os.path.join(samplesdir, "cross_platform/cross_platform_lin.cpp")},
        )

        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)

    def test_lotsofmagic(self):
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        relativepath = "lotsofmagic/lotsofmagic.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(["--magic", "cpp"], tempdir=tempdir)

        expected = {
            "LDFLAGS": {"-lm"},
            "F1": {"1"},
            "LINKFLAGS": {"-lpcap"},
            "F2": {"2"},
            "F3": {"3"},
        }
        self.assertEqual(magicparser.parse(realpath), expected)

        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)

    def test_SOURCE_in_header(self):
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        relativepath = "magicsourceinheader/main.cpp"
        samplesdir = uth.samplesdir()
        realpath = os.path.join(samplesdir, relativepath)
        magicparser = self._createmagicparser(["--magic", "cpp"], tempdir=tempdir)
        expected = {
            "LDFLAGS": OrderedSet(["-lm"]),
            "SOURCE": OrderedSet(
                [
                    os.path.join(
                        samplesdir,
                        "magicsourceinheader/include_dir/sub_dir/the_code_lin.cpp",
                    )
                ]
            ),
        }
        self.assertEqual(magicparser.parse(realpath), expected)

        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()
