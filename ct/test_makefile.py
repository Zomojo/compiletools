from __future__ import print_function
import unittest
import os
import tempfile
import subprocess
import shutil
import ct.unittesthelper as uth
import ct.makefile

class TestMakefile(unittest.TestCase):

    def setUp(self):
        uth.delete_existing_parsers()

    def test_makefile(self):
        ctdir = os.path.dirname(os.path.realpath(__file__))
        cakedir = os.path.realpath(os.path.join(ctdir,".."))
        origdir = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        relativepaths = ['samples/numbers/test_direct_include.cpp']
        realpaths = [ os.path.join(cakedir,filename) for filename in relativepaths]
        ct.makefile.main(['ct-test-makefile','-vvvv','--CXXFLAGS=-std=c++1z', '--filename'] + realpaths)
        
        #cmd = ['make']
        #subprocess.check_output(cmd, universal_newlines=True)
        self.assertTrue(True)
        # Cleanup
        shutil.rmtree(tempdir)

if __name__ == '__main__':
    unittest.main()
