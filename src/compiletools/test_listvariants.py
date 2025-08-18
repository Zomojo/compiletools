import os
import textwrap
import compiletools.testhelper as uth
import compiletools.listvariants


def test_none_found():
    # This test doesn't need the config file from CompileToolsTestContext, 
    # only temp directory and parser reset
    with uth.TempDirContextWithChange() as tempdir:
        with uth.ParserContext():
            # Create temp config with variant aliases
            compiletools.testhelper.create_temp_ct_conf(tempdir)
            
            # These values are deliberately chosen so that we can know that
            # no config files will be found except those in the temp directory
            ucd = "/home/dummy/.config/ct"
            scd = "/usr/lib"
            ecd = uth.cakedir()
            expected_output = textwrap.dedent("""\
                Variant aliases are:
                {{'dbg':'foo.debug', 'rls':'foo.release'}}
                From highest to lowest priority configuration directories, the possible variants are:
                {0}
                    ct
                /home/dummy/.config/ct
                    None found
                /usr/lib
                    None found
                {1}
                    None found
                """).format(
                tempdir,
                os.path.join(ecd, "ct", "ct.conf.d"),
            )

            output = compiletools.listvariants.find_possible_variants(
                user_config_dir=ucd, system_config_dir=scd, exedir=ecd, verbose=9, gitroot=tempdir
            )
            assert expected_output == output

