import unittest
import os
import shutil
import tempfile
import ct.unittesthelper as uth
import ct.listvariants


class TestListVariants(unittest.TestCase):
    def setUp(self):
        uth.reset()

    def test_none_found(self):
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)
        # These values are deliberately chosen so that we can know that
        # no config files will be found except those in the git repo
        ucd = "/home/dummy/.config/ct"
        scd = "/usr/lib"
        ecd = uth.cakedir()
        expected_output = """\
Variant aliases are:
{{'debug':'gcc.debug', 'release':'gcc.release'}}
From highest to lowest priority configuration directories, the possible variants are:
{0}
    None found
{1}
    None found
/home/dummy/.config/ct
    None found
/usr/lib
    None found
{2}
    blank
    clang.debug
    clang.release
    ct
    gcc.debug
    gcc.release
""".format(
            tempdir,
            os.path.join(tempdir, "ct.conf.d"),
            os.path.join(uth.cakedir(), "ct", "ct.conf.d"),
        )

        output = ct.listvariants.find_possible_variants(
            user_config_dir=ucd, system_config_dir=scd, exedir=ecd, verbose=9
        )
        self.assertEqual(expected_output, output)

        os.chdir(origdir)
        shutil.rmtree(tempdir, ignore_errors=True)

    def tearDown(self):
        uth.reset()


if __name__ == "__main__":
    unittest.main()
