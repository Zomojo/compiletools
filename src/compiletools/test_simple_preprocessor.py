import sys
import os

# Add the parent directory to sys.path so we can import ct modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from compiletools.simple_preprocessor import SimplePreprocessor


class TestSimplePreprocessor:
    """Unit tests for the SimplePreprocessor class"""

    def setup_method(self):
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
        assert self.processor._evaluate_expression('1') == 1
        assert self.processor._evaluate_expression('0') == 0
        assert self.processor._evaluate_expression('1 + 1') == 2
        
    def test_expression_evaluation_comparisons(self):
        """Test comparison operators"""
        # Test == operator
        assert self.processor._evaluate_expression('1 == 1') == 1
        assert self.processor._evaluate_expression('1 == 0') == 0
        
        # Test != operator (this is the problematic one)
        assert self.processor._evaluate_expression('1 != 0') == 1
        assert self.processor._evaluate_expression('1 != 1') == 0
        
        # Test > operator
        assert self.processor._evaluate_expression('2 > 1') == 1
        assert self.processor._evaluate_expression('1 > 2') == 0
        
    def test_expression_evaluation_logical(self):
        """Test logical operators"""
        # Test && operator
        assert self.processor._evaluate_expression('1 && 1') == 1
        assert self.processor._evaluate_expression('1 && 0') == 0
        assert self.processor._evaluate_expression('0 && 1') == 0
        
        # Test || operator  
        assert self.processor._evaluate_expression('1 || 0') == 1
        assert self.processor._evaluate_expression('0 || 1') == 1
        assert self.processor._evaluate_expression('0 || 0') == 0
        
    def test_expression_evaluation_complex(self):
        """Test complex expressions combining operators"""
        # Test combinations
        assert self.processor._evaluate_expression('1 != 0 && 2 > 1') == 1
        assert self.processor._evaluate_expression('1 == 0 || 2 == 2') == 1
        assert self.processor._evaluate_expression('(1 + 1) == 2') == 1
        
    def test_macro_expansion(self):
        """Test macro expansion in expressions"""
        # Test simple macro expansion
        assert self.processor._evaluate_expression('TEST_MACRO') == 1
        assert self.processor._evaluate_expression('VERSION') == 3
        
        # Test macro in comparisons
        assert self.processor._evaluate_expression('VERSION == 3') == 1
        assert self.processor._evaluate_expression('VERSION != 2') == 1
        assert self.processor._evaluate_expression('COUNT > 3') == 1
        
    def test_defined_expressions(self):
        """Test defined() expressions"""
        # Test defined() function
        assert self.processor._evaluate_expression('defined(TEST_MACRO)') == 1
        assert self.processor._evaluate_expression('defined(UNDEFINED_MACRO)') == 0
        
        # Test defined() in complex expressions
        assert self.processor._evaluate_expression('defined(TEST_MACRO) && TEST_MACRO == 1') == 1
        assert self.processor._evaluate_expression('defined(VERSION) && VERSION > 2') == 1
        
    def test_conditional_compilation_ifdef(self):
        """Test #ifdef handling"""
        text = '''
#ifdef TEST_MACRO
#include "test.h"
#endif
'''
        result = self.processor.process(text)
        assert '#include "test.h"' in result
        
    def test_conditional_compilation_ifndef(self):
        """Test #ifndef handling"""
        text = '''
#ifndef UNDEFINED_MACRO
#include "test.h"
#endif
'''
        result = self.processor.process(text)
        assert '#include "test.h"' in result
        
    def test_conditional_compilation_if_simple(self):
        """Test simple #if handling"""
        text = '''
#if VERSION == 3
#include "version3.h"
#endif
'''
        result = self.processor.process(text)
        assert '#include "version3.h"' in result
        
    def test_conditional_compilation_if_complex(self):
        """Test complex #if expressions"""
        text = '''
#if defined(VERSION) && VERSION > 2
#include "advanced.h"
#endif
'''
        result = self.processor.process(text)
        assert '#include "advanced.h"' in result
        
    def test_conditional_compilation_if_with_not_equal(self):
        """Test #if with != operator (the problematic case)"""
        text = '''
#if COUNT != 0
#include "nonzero.h"
#endif
'''
        result = self.processor.process(text)
        assert '#include "nonzero.h"' in result
        
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
        assert '#include "test_v3.h"' in result
        
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
        assert '#include "defined.h"' in result
        assert '#include "undefined.h"' not in result
        
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
        assert '#include "version3.h"' in result
        assert '#include "version1.h"' not in result
        assert '#include "version2.h"' not in result
        assert '#include "default.h"' not in result
        
    def test_macro_define_and_use(self):
        """Test #define and subsequent use"""
        text = '''
#define NEW_MACRO 42
#if NEW_MACRO == 42
#include "forty_two.h"
#endif
'''
        result = self.processor.process(text)
        assert '#include "forty_two.h"' in result
        
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
        assert '#include "before_undef.h"' in result
        assert '#include "after_undef.h"' not in result


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
        assert '#include "linux_epoll_threading.hpp"' in result
        assert '#include "numa_threading.hpp"' in result

    def test_recursive_macro_expansion(self):
        """Test recursive macro expansion functionality"""
        # Test simple case
        result = self.processor._recursive_expand_macros('VERSION')
        assert result == '3'
        
        # Test recursive expansion
        processor_with_recursive = SimplePreprocessor({
            'A': 'B',
            'B': 'C', 
            'C': '42'
        }, verbose=0)
        
        result = processor_with_recursive._recursive_expand_macros('A')
        assert result == '42'
        
        # Test max iterations protection (prevent infinite loops)
        processor_with_loop = SimplePreprocessor({
            'X': 'Y',
            'Y': 'X'
        }, verbose=0)
        
        result = processor_with_loop._recursive_expand_macros('X', max_iterations=5)
        # Should stop after max_iterations and return last value
        assert result in ['X', 'Y']  # Could be either depending on iteration count

    def test_comment_stripping(self):
        """Test C++ style comment stripping from expressions"""
        # Test basic comment stripping
        result = self.processor._strip_comments('1 + 1 // this is a comment')
        assert result == '1 + 1'
        
        # Test expression without comments
        result = self.processor._strip_comments('1 + 1')
        assert result == '1 + 1'
        
        # Test comment at beginning
        result = self.processor._strip_comments('// comment only')
        assert result == ''

    def test_platform_macros(self):
        """Test platform-specific macro addition"""
        processor = SimplePreprocessor({}, verbose=0)
        processor.add_platform_macros()
        
        # At least one platform macro should be defined based on current platform
        import sys
        if sys.platform.startswith('linux'):
            assert '__linux__' in processor.macros
            assert processor.macros['__linux__'] == '1'
        elif sys.platform.startswith('win'):
            assert '_WIN32' in processor.macros
            assert processor.macros['_WIN32'] == '1'
        elif sys.platform.startswith('darwin'):
            assert '__APPLE__' in processor.macros
            assert processor.macros['__APPLE__'] == '1'

    def test_if_with_comments(self):
        """Test #if directive with C++ style comments"""
        text = '''
#if 1 // this should be true
    included_line
#endif
'''
        result = self.processor.process(text)
        assert 'included_line' in result

    def test_block_comment_stripping(self):
        """Test that block comments do not break expression parsing"""
        text = '''
#if /* block */ 1 /* more */
ok
#endif
'''
        result = self.processor.process(text)
        assert 'ok' in result

    def test_numeric_literal_parsing(self):
        """Test hex, binary, and octal numeric literals in expressions"""
        assert self.processor._evaluate_expression('0x10 == 16') == 1
        assert self.processor._evaluate_expression('0b1010 == 10') == 1
        assert self.processor._evaluate_expression('010 == 8') == 1  # octal
        assert self.processor._evaluate_expression('0 == 0') == 1

    def test_bitwise_operators(self):
        """Test bitwise and shift operators in expressions"""
        assert self.processor._evaluate_expression('1 & 1') == 1
        assert self.processor._evaluate_expression('1 | 0') == 1
        assert self.processor._evaluate_expression('1 ^ 1') == 0
        assert self.processor._evaluate_expression('~0 == -1') == 1
        assert self.processor._evaluate_expression('(1 << 3) == 8') == 1
        assert self.processor._evaluate_expression('(8 >> 2) == 2') == 1


