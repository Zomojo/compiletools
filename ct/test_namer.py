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
        uth.reset()

    @unittest.skipUnless(
        int(sys.version[0]) < 3, "The hardcoded hash value is only valid on python 2")
    def test_executable_pathname(self):
        config_dir = os.path.join(uth.cakedir(),'ct.conf.d')
        config_files = [os.path.join(config_dir,'gcc.debug.conf')]
        cap = configargparse.getArgumentParser(
            description='TestNamer',
            formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
            default_config_files=config_files,
            args_for_setting_config_path=["-c", "--config"],
            ignore_unknown_config_file_keys=True)
        argv = ['--no-git-root']
        ct.apptools.add_common_arguments(
            cap=cap,
            argv=argv,
            variant="gcc.debug")
        ct.namer.Namer.add_arguments(cap=cap, argv=argv, variant="gcc.debug")
        args = ct.apptools.parseargs(cap, argv)
        namer = ct.namer.Namer(args, argv=argv, variant="gcc.debug")
        exename = namer.executable_pathname('/home/user/code/my.cpp')
        self.assertEqual(
            exename,
            os.path.join(
                os.getcwd(),
                'bin/gcc.debug/home/user/code/my'))
    def tearDown(self):
        uth.reset()

if __name__ == '__main__':
    unittest.main()
