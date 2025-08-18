import sys
import os
import shutil
import tempfile
import configargparse

import compiletools.testhelper as uth
import compiletools.configutils
import compiletools.apptools


class TestVariant:
    def setup_method(self):
        uth.reset()

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
        with uth.TempDirContext() as ctx:
            local_ct_conf = compiletools.testhelper.create_temp_ct_conf(os.getcwd())
            variant = compiletools.configutils.extract_item_from_ct_conf(
                key="variant",
                user_config_dir="/var",
                system_config_dir="/var",
                exedir=uth.cakedir(),
                gitroot=os.getcwd(),
            )
            assert "debug" == variant

    def test_extract_variant_from_blank_argv(self):
        # Force to find the temp directory ct.conf
        with uth.TempDirContext() as ctx:
            local_ct_conf = compiletools.testhelper.create_temp_ct_conf(os.getcwd())
            variant = compiletools.configutils.extract_variant(
                argv=[],
                user_config_dir="/var",
                system_config_dir="/var",
                exedir=uth.cakedir(),
                verbose=0,
                gitroot=os.getcwd(),
            )
            assert "debug" == variant


    def test_default_configs(self):
        with uth.TempDirContext() as ctx:
            local_ct_conf = compiletools.testhelper.create_temp_ct_conf(os.getcwd())
            local_config_name = compiletools.testhelper.create_temp_config(os.getcwd())

            configs = compiletools.configutils.defaultconfigs(
                user_config_dir="/var",
                system_config_dir="/var",
                exedir=uth.cakedir(),
                verbose=0,
                gitroot=os.getcwd(),
            )

            assert [
                    os.path.join(os.getcwd(), "ct.conf"),
                ] == \
                configs

    def test_config_files_from_variant(self):
        with uth.TempDirContext() as ctx:
            local_ct_conf = compiletools.testhelper.create_temp_ct_conf(os.getcwd())
            # Deliberately call the next config gcc.debug.conf to verify that
            # the hierarchy of directories is working
            local_config_name = compiletools.testhelper.create_temp_config(
                os.getcwd(), "gcc.debug.conf"
            )

            configs = compiletools.configutils.config_files_from_variant(
                variant="gcc.debug",
                argv=[],
                user_config_dir="/var",
                system_config_dir="/var",
                exedir=uth.cakedir(),
                verbose=0,
                gitroot=os.getcwd(),
            )

            assert [
                    os.path.join(os.getcwd(), "ct.conf"),
                    os.path.join(os.getcwd(), "gcc.debug.conf"),
                ] == \
                configs

    def teardown_method(self):
        uth.reset()

