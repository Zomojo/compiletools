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
        # no config files will be found
        ucd = "/home/dummy/.config/ct"
        scd = "/usr/lib"
        expected_output = [
            'From highest to lowest priority configuration directories, the possible variants are: ',
            '/home/dummy/.config/ct',
            '\tNone found',
            '/usr/lib',
            '\tNone found',
            '/usr/bin/ct.conf.d',
            '\tNone found']
        output = ct.listvariants.find_possible_variants(
            user_config_dir=ucd,
            system_config_dir=scd,
            exedir='/usr/bin')
        self.assertEqual(expected_output, output)

    def tearDown(self):
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()
