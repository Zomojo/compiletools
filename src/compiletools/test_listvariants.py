import unittest
import os
import shutil
import tempfile
import compiletools.unittesthelper as uth
import compiletools.listvariants


class TestListVariants(unittest.TestCase):
    def setUp(self):
        uth.reset()

    def test_none_found(self):
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
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
{1}
    None found
/home/dummy/.config/ct
    None found
/usr/lib
    None found
{2}
    None found
""".format(
            tempdir,
            os.path.join(tempdir, "src", "compiletools", "ct.conf.d"),
            os.path.join(ecd, "ct", "ct.conf.d"),
        )

        output = compiletools.listvariants.find_possible_variants(
            user_config_dir=ucd, system_config_dir=scd, exedir=ecd, verbose=9, gitroot=tempdir
        )
        self.assertEqual(expected_output, output)

        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
