import sys
import os
import shutil
import tempfile
import unittest
import configargparse

import compiletools.unittesthelper as uth
import compiletools.configutils
import compiletools.apptools


class TestVariant(unittest.TestCase):
    def setUp(self):
        uth.reset()
        self._tmpdir = None

    def test_extract_value_from_argv(self):
        argv = ['/usr/bin/ct-config', '--pkg-config=fig', '-v']

        value = compiletools.configutils.extract_value_from_argv("pkg-config", argv)
        assert value == "fig"

        value = compiletools.configutils.extract_value_from_argv("config", argv)
        assert value == None


    def test_extract_variant(self):
        assert "abc" == compiletools.configutils.extract_variant("--variant=abc".split())
        assert "abc" == compiletools.configutils.extract_variant("--variant abc".split())
        assert "abc.123" == \
            compiletools.configutils.extract_variant(
                "-a -b -x --blah --variant=abc.123 -a -b -z --blah".split()
            )
        assert "abc.123" == \
            compiletools.configutils.extract_variant(
                "-a -b -x --blah --variant abc.123 -a -b -cz--blah".split()
            )

        # Note the -c overrides the --variant
        assert "blah" == \
            compiletools.configutils.extract_variant(
                "-a -b -c blah.conf --variant abc.123 -a -b -cz--blah".split()
            )

    def test_extract_variant_from_ct_conf(self):
        # Should find the one in the temp directory ct.conf
        origdir = self._setup_and_chdir_temp_dir()
        local_ct_conf = compiletools.unittesthelper.create_temp_ct_conf(self._tmpdir)
        variant = compiletools.configutils.extract_item_from_ct_conf(
            key="variant",
            user_config_dir="/var",
            system_config_dir="/var",
            exedir=uth.cakedir(),
            gitroot=self._tmpdir,
        )
        assert "debug" == variant

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_extract_variant_from_blank_argv(self):
        # Force to find the temp directory ct.conf
        origdir = self._setup_and_chdir_temp_dir()
        local_ct_conf = compiletools.unittesthelper.create_temp_ct_conf(self._tmpdir)
        variant = compiletools.configutils.extract_variant(
            user_config_dir="/var",
            system_config_dir="/var",
            exedir=uth.cakedir(),
            verbose=0,
            gitroot=self._tmpdir,
        )
        assert "debug" == variant

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
        local_ct_conf = compiletools.unittesthelper.create_temp_ct_conf(self._tmpdir)
        local_config_name = compiletools.unittesthelper.create_temp_config(self._tmpdir)

        configs = compiletools.configutils.defaultconfigs(
            user_config_dir="/var",
            system_config_dir="/var",
            exedir=uth.cakedir(),
            verbose=0,
            gitroot=self._tmpdir,
        )

        assert [
                os.path.join(self._tmpdir, "ct.conf"),
            ] == \
            configs

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_config_files_from_variant(self):
        origdir = self._setup_and_chdir_temp_dir()
        local_ct_conf = compiletools.unittesthelper.create_temp_ct_conf(self._tmpdir)
        # Deliberately call the next config gcc.debug.conf to verify that
        # the hierarchy of directories is working
        local_config_name = compiletools.unittesthelper.create_temp_config(
            self._tmpdir, "gcc.debug.conf"
        )

        configs = compiletools.configutils.config_files_from_variant(
            variant="gcc.debug",
            argv=[],
            user_config_dir="/var",
            system_config_dir="/var",
            exedir=uth.cakedir(),
            verbose=0,
            gitroot=self._tmpdir,
        )

        assert [
                os.path.join(self._tmpdir, "ct.conf"),
                os.path.join(self._tmpdir, "gcc.debug.conf"),
            ] == \
            configs

        # Cleanup
        os.chdir(origdir)
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
