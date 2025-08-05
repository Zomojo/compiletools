import unittest
import sys
import os

# Add the parent directory to sys.path so we can import ct modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from compiletools.headerdeps import SimplePreprocessor


class TestSimplePreprocessor(unittest.TestCase):
    """Unit tests for the SimplePreprocessor class"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.macros = {
            'TEST_MACRO': '1',
            'FEATURE_A': '1', 
            'VERSION': '3',
            'COUNT': '5'
        }
        self.processor = SimplePreprocessor(self.macros, verbose=0)

    def test_expression_evaluation_basic(self):
        """Test basic expression evaluation"""
        # Test simple numeric expressions
        self.assertEqual(self.processor._evaluate_expression('1'), 1)
        self.assertEqual(self.processor._evaluate_expression('0'), 0)
        self.assertEqual(self.processor._evaluate_expression('1 + 1'), 2)
        
    def test_expression_evaluation_comparisons(self):
        """Test comparison operators"""
        # Test == operator
        self.assertEqual(self.processor._evaluate_expression('1 == 1'), 1)
        self.assertEqual(self.processor._evaluate_expression('1 == 0'), 0)
        
        # Test != operator (this is the problematic one)
        self.assertEqual(self.processor._evaluate_expression('1 != 0'), 1)
        self.assertEqual(self.processor._evaluate_expression('1 != 1'), 0)
        
        # Test > operator
        self.assertEqual(self.processor._evaluate_expression('2 > 1'), 1)
        self.assertEqual(self.processor._evaluate_expression('1 > 2'), 0)
        
    def test_expression_evaluation_logical(self):
        """Test logical operators"""
        # Test && operator
        self.assertEqual(self.processor._evaluate_expression('1 && 1'), 1)
        self.assertEqual(self.processor._evaluate_expression('1 && 0'), 0)
        self.assertEqual(self.processor._evaluate_expression('0 && 1'), 0)
        
        # Test || operator  
        self.assertEqual(self.processor._evaluate_expression('1 || 0'), 1)
        self.assertEqual(self.processor._evaluate_expression('0 || 1'), 1)
        self.assertEqual(self.processor._evaluate_expression('0 || 0'), 0)
        
    def test_expression_evaluation_complex(self):
        """Test complex expressions combining operators"""
        # Test combinations
        self.assertEqual(self.processor._evaluate_expression('1 != 0 && 2 > 1'), 1)
        self.assertEqual(self.processor._evaluate_expression('1 == 0 || 2 == 2'), 1)
        self.assertEqual(self.processor._evaluate_expression('(1 + 1) == 2'), 1)
        
    def test_macro_expansion(self):
        """Test macro expansion in expressions"""
        # Test simple macro expansion
        self.assertEqual(self.processor._evaluate_expression('TEST_MACRO'), 1)
        self.assertEqual(self.processor._evaluate_expression('VERSION'), 3)
        
        # Test macro in comparisons
        self.assertEqual(self.processor._evaluate_expression('VERSION == 3'), 1)
        self.assertEqual(self.processor._evaluate_expression('VERSION != 2'), 1)
        self.assertEqual(self.processor._evaluate_expression('COUNT > 3'), 1)
        
    def test_defined_expressions(self):
        """Test defined() expressions"""
        # Test defined() function
        self.assertEqual(self.processor._evaluate_expression('defined(TEST_MACRO)'), 1)
        self.assertEqual(self.processor._evaluate_expression('defined(UNDEFINED_MACRO)'), 0)
        
        # Test defined() in complex expressions
        self.assertEqual(self.processor._evaluate_expression('defined(TEST_MACRO) && TEST_MACRO == 1'), 1)
        self.assertEqual(self.processor._evaluate_expression('defined(VERSION) && VERSION > 2'), 1)
        
    def test_conditional_compilation_ifdef(self):
        """Test #ifdef handling"""
        text = '''
#ifdef TEST_MACRO
#include "test.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "test.h"', result)
        
    def test_conditional_compilation_ifndef(self):
        """Test #ifndef handling"""
        text = '''
#ifndef UNDEFINED_MACRO
#include "test.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "test.h"', result)
        
    def test_conditional_compilation_if_simple(self):
        """Test simple #if handling"""
        text = '''
#if VERSION == 3
#include "version3.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "version3.h"', result)
        
    def test_conditional_compilation_if_complex(self):
        """Test complex #if expressions"""
        text = '''
#if defined(VERSION) && VERSION > 2
#include "advanced.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "advanced.h"', result)
        
    def test_conditional_compilation_if_with_not_equal(self):
        """Test #if with != operator (the problematic case)"""
        text = '''
#if COUNT != 0
#include "nonzero.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "nonzero.h"', result)
        
    def test_conditional_compilation_nested(self):
        """Test nested conditional compilation"""
        text = '''
#ifdef TEST_MACRO
    #if VERSION >= 3
        #include "test_v3.h"
    #endif
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "test_v3.h"', result)
        
    def test_conditional_compilation_else(self):
        """Test #else handling"""
        text = '''
#ifdef UNDEFINED_MACRO
#include "undefined.h"
#else
#include "defined.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "defined.h"', result)
        self.assertNotIn('#include "undefined.h"', result)
        
    def test_conditional_compilation_elif(self):
        """Test #elif handling"""
        text = '''
#if VERSION == 1
#include "version1.h"
#elif VERSION == 2
#include "version2.h" 
#elif VERSION == 3
#include "version3.h"
#else
#include "default.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "version3.h"', result)
        self.assertNotIn('#include "version1.h"', result)
        self.assertNotIn('#include "version2.h"', result)
        self.assertNotIn('#include "default.h"', result)
        
    def test_macro_define_and_use(self):
        """Test #define and subsequent use"""
        text = '''
#define NEW_MACRO 42
#if NEW_MACRO == 42
#include "forty_two.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "forty_two.h"', result)
        
    def test_macro_undef(self):
        """Test #undef functionality"""
        text = '''
#ifdef TEST_MACRO
#include "before_undef.h"
#endif
#undef TEST_MACRO
#ifdef TEST_MACRO
#include "after_undef.h"
#endif
'''
        result = self.processor.process(text)
        self.assertIn('#include "before_undef.h"', result)
        self.assertNotIn('#include "after_undef.h"', result)


    def test_failing_scenario_use_epoll(self):
        """Test the exact scenario that's failing in the nested macros test"""
        # Set up macros exactly as in the failing test
        failing_macros = {
            'BUILD_CONFIG': '2',
            '__linux__': '1',
            'USE_EPOLL': '1', 
            'ENABLE_THREADING': '1',
            'THREAD_COUNT': '4',
            'NUMA_SUPPORT': '1'
        }
        processor = SimplePreprocessor(failing_macros, verbose=0)
        
        # Test the exact problematic condition
        text = '''
#if defined(USE_EPOLL) && USE_EPOLL != 0
    #ifdef ENABLE_THREADING
        #if defined(THREAD_COUNT) && THREAD_COUNT > 1
            #include "linux_epoll_threading.hpp"
            #ifdef NUMA_SUPPORT
                #if NUMA_SUPPORT == 1
                    #include "numa_threading.hpp"
                #endif
            #endif
        #endif
    #endif
#endif
'''
        result = processor.process(text)
        
        # These should be included
        self.assertIn('#include "linux_epoll_threading.hpp"', result)
        self.assertIn('#include "numa_threading.hpp"', result)


if __name__ == '__main__':
    unittest.main()