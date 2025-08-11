import os
import shutil
import tempfile
import compiletools.unittesthelper as uth
import compiletools.listvariants


def test_none_found():
    uth.reset()
    
    origdir = os.getcwd()
    tempdir = tempfile.mkdtemp()
    
    try:
        os.chdir(tempdir)
        
        # Create temp config with variant aliases
        compiletools.unittesthelper.create_temp_ct_conf(tempdir)
        
        # These values are deliberately chosen so that we can know that
        # no config files will be found except those in the temp directory
        ucd = "/home/dummy/.config/ct"
        scd = "/usr/lib"
        ecd = uth.cakedir()
        expected_output = """\
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
""".format(
            tempdir,
            os.path.join(ecd, "ct", "ct.conf.d"),
        )

        output = compiletools.listvariants.find_possible_variants(
            user_config_dir=ucd, system_config_dir=scd, exedir=ecd, verbose=9, gitroot=tempdir
        )
        assert expected_output == output
        
    finally:
        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)
        uth.reset()


