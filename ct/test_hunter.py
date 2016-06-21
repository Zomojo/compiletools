from __future__ import print_function
import unittest
import os
import ct.hunter


class TestHunter(unittest.TestCase):

    def test_implied_source_nonexistent_file(self):
        self.assertIsNone(ct.hunter.implied_source('nonexistent_file.hpp'))

    def test_implied_source(self):
        filename = 'samples/dottypaths/d2/d2.hpp'
        basename = os.path.splitext(filename)[0]
        expected = os.path.join(os.getcwd(),basename + '.cpp')
        result = ct.hunter.implied_source(filename)
        self.assertEqual(expected,result)

    def test_ht_and_hd_generate_same_results(self):
        filenames = ['samples/factory/test_factory.cpp', 'samples/numbers/test_direct_include.cpp']
        for filename in filenames:
            realpath = ct.wrappedos.realpath(filename)
            argv = ['ct-test',realpath]
            ht = ct.hunter.HeaderTree(argv)
            hd = ct.hunter.HeaderDependencies(argv)
            htresult = ht.process(realpath)
            hdresult = hd.process(realpath)
            self.assertSetEqual(htresult,hdresult)

    def test_ht_and_hd_generate_same_results_preprocess(self):
        filenames = ['samples/factory/test_factory.cpp', 'samples/numbers/test_direct_include.cpp']
        for filename in filenames:
            realpath = ct.wrappedos.realpath(filename)
            argv = ['ct-test',realpath,'--preprocess']
            ht = ct.hunter.HeaderTree(argv)
            hd = ct.hunter.HeaderDependencies(argv)
            htresult = ht.process(realpath)
            hdresult = hd.process(realpath)
            self.assertSetEqual(htresult,hdresult)

    def test_ht_and_hd_generate_same_results_directread(self):
        filenames = ['samples/factory/test_factory.cpp', 'samples/numbers/test_direct_include.cpp']
        for filename in filenames:
            realpath = ct.wrappedos.realpath(filename)
            argv = ['ct-test',realpath,'--directread']
            ht = ct.hunter.HeaderTree(argv)
            hd = ct.hunter.HeaderDependencies(argv)
            htresult = ht.process(realpath)
            hdresult = hd.process(realpath)
            self.assertSetEqual(htresult,hdresult)

if __name__ == '__main__':
    unittest.main()
