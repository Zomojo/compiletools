from __future__ import unicode_literals
from __future__ import print_function
import unittest
import ct.unittesthelper as uth
import ct.listvariants


class TestListVariants(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def test_none_found(self):
        # These values are deliberately chosen so that we can know that
        # no config files will be found except those in the git repo
        ucd = "/home/dummy/.config/ct"
        scd = "/usr/lib"
        ecd = uth.cakedir()
        expected_output = [
            'Variant aliases are:',
            "{'debug':'gcc.debug', 'release':'gcc.release'}",
            '\nFrom highest to lowest priority configuration directories, the possible variants are: ',
            '/home/dummy/.config/ct',
            '\tNone found',
            '/usr/lib',
            '\tNone found',
            '/data/home/geoff/compiletools/ct.conf.d',
            '\tgcc61.debug',
            '\tclang.debug',
            '\tclang.release',
            '\tgcc61.release',
            '\tct',
            '\tgcc.debug',
            '\tgcc.release']
        output = ct.listvariants.find_possible_variants(
            user_config_dir=ucd,
            system_config_dir=scd,
            exedir=ecd, verbose=9)
        self.assertEqual(expected_output, output)

    def tearDown(self):
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()
