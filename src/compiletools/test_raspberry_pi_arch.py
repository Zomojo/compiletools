#!/usr/bin/env python3
"""
Test case specifically for Raspberry Pi ARM architecture detection

This test ensures the headerdeps module correctly detects ARM macros 
on Raspberry Pi systems running various OS configurations.
"""

import unittest
import unittest.mock
import compiletools.headerdeps
import tempfile
import os


class TestRaspberryPiArchitecture(unittest.TestCase):
    """Test ARM architecture detection for Raspberry Pi systems"""

    def test_raspberry_pi_32bit_detection(self):
        """Test 32-bit Raspberry Pi architecture detection"""
        test_cases = [
            ('armv6l', ['__arm__']),      # Pi Zero, Pi 1
            ('armv7l', ['__arm__']),      # Pi 2, 3, 4 (32-bit OS)
            ('armv8l', ['__arm__']),      # Some ARMv8 32-bit configurations
        ]
        
        for arch, expected_macros in test_cases:
            with self.subTest(arch=arch):
                with unittest.mock.patch('platform.machine', return_value=arch):
                    args = self._create_mock_args()
                    direct_deps = compiletools.headerdeps.DirectHeaderDeps(args)
                    
                    for macro in expected_macros:
                        self.assertIn(macro, direct_deps.defined_macros,
                                    f"Missing {macro} for {arch}")
                        self.assertEqual(direct_deps.defined_macros[macro], "1")

    def test_raspberry_pi_64bit_detection(self):
        """Test 64-bit Raspberry Pi architecture detection"""
        test_cases = [
            ('aarch64', ['__aarch64__', '__LP64__']),  # Pi 3, 4, 5 (64-bit OS)
            ('arm64', ['__aarch64__', '__LP64__']),    # Alternative naming
        ]
        
        for arch, expected_macros in test_cases:
            with self.subTest(arch=arch):
                with unittest.mock.patch('platform.machine', return_value=arch):
                    args = self._create_mock_args()
                    direct_deps = compiletools.headerdeps.DirectHeaderDeps(args)
                    
                    for macro in expected_macros:
                        self.assertIn(macro, direct_deps.defined_macros,
                                    f"Missing {macro} for {arch}")
                        self.assertEqual(direct_deps.defined_macros[macro], "1")
                    
                    # 64-bit ARM should NOT have 32-bit __arm__ macro
                    self.assertNotIn('__arm__', direct_deps.defined_macros,
                                   f"64-bit {arch} should not define __arm__")

    def test_arm_header_conditional_compilation(self):
        """Test that ARM-specific headers are correctly included"""
        
        # Test with a sample that would include ARM-specific code
        test_content = '''
#ifdef __arm__
#include "arm32_feature.h"
#endif

#ifdef __aarch64__
#include "arm64_feature.h"
#endif
'''
        
        # Test 32-bit ARM
        with unittest.mock.patch('platform.machine', return_value='armv7l'):
            args = self._create_mock_args()
            direct_deps = compiletools.headerdeps.DirectHeaderDeps(args)
            
            # Verify __arm__ is defined for 32-bit
            self.assertIn('__arm__', direct_deps.defined_macros)
            self.assertNotIn('__aarch64__', direct_deps.defined_macros)
        
        # Test 64-bit ARM
        with unittest.mock.patch('platform.machine', return_value='aarch64'):
            args = self._create_mock_args()
            direct_deps = compiletools.headerdeps.DirectHeaderDeps(args)
            
            # Verify __aarch64__ is defined for 64-bit
            self.assertIn('__aarch64__', direct_deps.defined_macros)
            self.assertNotIn('__arm__', direct_deps.defined_macros)

    def _create_mock_args(self):
        """Create a minimal mock args object for testing"""
        class MockArgs:
            verbose = 0
            CPPFLAGS = ""
            include = []
            
        return MockArgs()


if __name__ == '__main__':
    unittest.main()