import sys
import os
import shutil
import tempfile
import unittest
import configargparse

import ct.unittesthelper as uth
import ct.configutils
import ct.apptools


class TestVariant(unittest.TestCase):
    def setUp(self):
        uth.reset()
        self._tmpdir = None

    def test_extract_value_from_argv(self):
        argv = ['/usr/bin/ct-config', '--pkg-config=fig', '-vvvvv']

        value = ct.configutils.extract_value_from_argv("pkg-config", argv)
        self.assertEqual(value, "fig")

        value = ct.configutils.extract_value_from_argv("config", argv)
        self.assertEqual(value, None)


    def test_extract_variant(self):
        self.assertEqual("abc", ct.configutils.extract_variant("--variant=abc".split()))
        self.assertEqual("abc", ct.configutils.extract_variant("--variant abc".split()))
        self.assertEqual(
            "abc.123",
            ct.configutils.extract_variant(
                "-a -b -x --blah --variant=abc.123 -a -b -z --blah".split()
            ),
        )
        self.assertEqual(
            "abc.123",
            ct.configutils.extract_variant(
                "-a -b -x --blah --variant abc.123 -a -b -cz--blah".split()
            ),
        )

        # Note the -c overrides the --variant
        self.assertEqual(
            "blah",
            ct.configutils.extract_variant(
                "-a -b -c blah.conf --variant abc.123 -a -b -cz--blah".split()
            ),
        )

    def test_extract_variant_from_ct_conf(self):
        # Should find the one in the git repo ct.conf.d/ct.conf
        origdir = self._setup_and_chdir_temp_dir()
        variant = ct.configutils.extract_item_from_ct_conf(
            key="variant",
            user_config_dir="/var",
            system_config_dir="/var",
            exedir=uth.cakedir(),
        )
        self.assertEqual("debug", variant)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_extract_variant_from_blank_argv(self):
        # Force to find the git repo ct.conf.d/ct.conf
        origdir = self._setup_and_chdir_temp_dir()
        variant = ct.configutils.extract_variant(
            user_config_dir="/var",
            system_config_dir="/var",
            exedir=uth.cakedir(),
            verbose=0,
        )
        self.assertEqual("gcc.debug", variant)

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _setup_and_chdir_temp_dir(self):
        """ Returns the original working directory so you can chdir back to that at the end """
        origdir = os.getcwd()
        self._tmpdir = tempfile.mkdtemp()
        os.chdir(self._tmpdir)
        return origdir

    def test_default_configs(self):
        origdir = self._setup_and_chdir_temp_dir()
        local_ct_conf = ct.unittesthelper.create_temp_ct_conf(self._tmpdir)
        local_config_name = ct.unittesthelper.create_temp_config(self._tmpdir)

        configs = ct.configutils.defaultconfigs(
            user_config_dir="/var",
            system_config_dir="/var",
            exedir=uth.cakedir(),
            verbose=0,
        )

        self.assertListEqual(
            [
                os.path.join(uth.ctconfdir(), "ct.conf"),
                os.path.join(self._tmpdir, "ct.conf"),
            ],
            configs,
        )

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_config_files_from_variant(self):
        origdir = self._setup_and_chdir_temp_dir()
        local_ct_conf = ct.unittesthelper.create_temp_ct_conf(self._tmpdir)
        # Deliberately call the next config gcc.debug.conf to verify that
        # the hierarchy of directories is working
        local_config_name = ct.unittesthelper.create_temp_config(
            self._tmpdir, "gcc.debug.conf"
        )

        configs = ct.configutils.config_files_from_variant(
            variant="gcc.debug",
            argv=[],
            user_config_dir="/var",
            system_config_dir="/var",
            exedir=uth.cakedir(),
            verbose=0,
        )

        self.assertListEqual(
            [
                os.path.join(uth.ctconfdir(), "ct.conf"),
                os.path.join(self._tmpdir, "ct.conf"),
                os.path.join(uth.ctconfdir(), "gcc.debug.conf"),
                os.path.join(self._tmpdir, "gcc.debug.conf"),
            ],
            configs,
        )

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
