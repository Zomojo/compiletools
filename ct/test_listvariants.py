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
        uhd = "/home/dummy"
        scd = "/usr/lib"
        argv = ["/usr/bin/python"]
        expected_output = [
            'From highest to lowest priority configuration directories, the possible variants are: ',
            '/home/dummy/.config/ct/',
            '\tNone found',
            '/usr/lib/ct.conf.d/',
            '\tNone found',
            '/usr/bin/ct.conf.d/',
            '\tNone found']
        output = ct.listvariants.find_possible_variants(
            user_home_dir=uhd,
            system_config_dir=scd,
            argv=argv)
        self.assertEqual(expected_output, output)

if __name__ == '__main__':
    unittest.main()
