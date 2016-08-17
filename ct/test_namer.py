from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import unittest
import configargparse
import ct.unittesthelper as uth
import ct.namer
import ct.configutils
import ct.apptools

class TestNamer(unittest.TestCase):
    def setUp(self):
        uth.delete_existing_parsers()

    @unittest.skipUnless(int(sys.version[0]) < 3, "The hardcoded hash value is only valid on python 2")
    def test_executable_pathname(self):
        config_files = ct.configutils.config_files_from_variant(exedir=uth.cakedir())
        cap = configargparse.getArgumentParser(
            description='TestNamer',
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            default_config_files=config_files,
            args_for_setting_config_path=["-c","--config"],
            ignore_unknown_config_file_keys=True)
        argv = ['--no-git-root']
        ct.apptools.add_common_arguments(cap=cap, argv=argv, exedir=uth.cakedir())
        ct.namer.Namer.add_arguments(cap=cap, argv=argv, exedir=uth.cakedir())
        args = ct.apptools.parseargs(cap, argv)
        namer = ct.namer.Namer(args, argv=argv, exedir=uth.cakedir())
        exename = namer.executable_pathname('/home/user/code/my.cpp')
        self.assertEqual(
            exename,
            os.path.join(
                os.getcwd(),
                'bin/gcc.debug.a4fa5f97/home/user/code/my'))
        
    def tearDown(self):
        uth.delete_existing_parsers()

if __name__ == '__main__':
    unittest.main()
