"""Tests for the compiler_macros module."""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
import compiletools.compiler_macros as cm


class TestCompilerMacros:
    """Test the dynamic compiler macro detection functionality."""
    
    def test_get_compiler_macros_no_compiler(self):
        """Test get_compiler_macros with no compiler specified."""
        # Clear cache first
        cm.get_compiler_macros.cache_clear()
        
        macros = cm.get_compiler_macros('', verbose=0)
        assert macros == {}
    
    def test_get_compiler_macros_success(self):
        """Test successful querying of compiler macros."""
        # Clear cache first
        cm.get_compiler_macros.cache_clear()
        
        # Mock successful subprocess call
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """#define __GNUC__ 11
#define __GNUC_MINOR__ 2
#define __GNUC_PATCHLEVEL__ 0
#define __VERSION__ "11.2.0"
#define __x86_64__ 1
#define __linux__ 1"""
        
        with patch('subprocess.run', return_value=mock_result):
            macros = cm.get_compiler_macros('gcc', verbose=0)
            assert '__GNUC__' in macros
            assert macros['__GNUC__'] == '11'
            assert '__GNUC_MINOR__' in macros
            assert macros['__GNUC_MINOR__'] == '2'
            assert '__linux__' in macros
            assert macros['__linux__'] == '1'
            assert '__VERSION__' in macros
            assert macros['__VERSION__'] == '11.2.0'
    
    def test_get_compiler_macros_with_quotes(self):
        """Test handling of macros with quoted values."""
        # Clear cache first
        cm.get_compiler_macros.cache_clear()
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '#define __VERSION__ "gcc version 11.2.0"'
        
        with patch('subprocess.run', return_value=mock_result):
            macros = cm.get_compiler_macros('gcc', verbose=0)
            assert macros['__VERSION__'] == 'gcc version 11.2.0'
    
    def test_get_compiler_macros_failure_nonzero_return(self):
        """Test handling of non-zero return code."""
        # Clear cache first
        cm.get_compiler_macros.cache_clear()
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        
        with patch('subprocess.run', return_value=mock_result):
            macros = cm.get_compiler_macros('bad-compiler', verbose=0)
            assert macros == {}
    
    def test_get_compiler_macros_failure_not_found(self):
        """Test handling of FileNotFoundError."""
        # Clear cache first
        cm.get_compiler_macros.cache_clear()
        
        with patch('subprocess.run', side_effect=FileNotFoundError("Compiler not found")):
            macros = cm.get_compiler_macros('nonexistent', verbose=0)
            assert macros == {}
    
    def test_get_compiler_macros_failure_timeout(self):
        """Test handling of timeout."""
        # Clear cache first
        cm.get_compiler_macros.cache_clear()
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 5)):
            macros = cm.get_compiler_macros('slow-compiler', verbose=0)
            assert macros == {}
    
    def test_lru_cache_functionality(self):
        """Test that the LRU cache is working properly."""
        # Clear cache first
        cm.get_compiler_macros.cache_clear()
        
        call_count = 0
        
        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.returncode = 0
            result.stdout = "#define __TEST__ 1"
            return result
        
        with patch('subprocess.run', side_effect=mock_run):
            # First call should query the compiler
            macros1 = cm.get_compiler_macros('gcc', verbose=0)
            assert call_count == 1
            
            # Second call with same args should use cache
            macros2 = cm.get_compiler_macros('gcc', verbose=0)
            assert call_count == 1  # Should not have increased
            
            # Results should be identical
            assert macros1 == macros2
            
            # Different compiler should trigger new query
            macros3 = cm.get_compiler_macros('clang', verbose=0)
            assert call_count == 2
    
    def test_clear_cache(self):
        """Test the cache clearing functionality."""
        # Populate cache
        cm.get_compiler_macros.cache_clear()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "#define __TEST__ 1"
            
            # First call
            cm.get_compiler_macros('gcc', verbose=0)
            assert mock_run.call_count == 1
            
            # Second call uses cache
            cm.get_compiler_macros('gcc', verbose=0)
            assert mock_run.call_count == 1
            
            # Clear cache
            cm.clear_cache()
            
            # Next call should query again
            cm.get_compiler_macros('gcc', verbose=0)
            assert mock_run.call_count == 2
    
    def test_real_gcc_if_available(self):
        """Test with real GCC compiler if available."""
        # Clear cache first
        cm.get_compiler_macros.cache_clear()
        
        # This test will only run if gcc is actually available
        try:
            subprocess.run(['gcc', '--version'], capture_output=True, check=True, timeout=1)
            has_gcc = True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            has_gcc = False
        
        if has_gcc:
            macros = cm.get_compiler_macros('gcc', verbose=0)
            # GCC should always define __GNUC__
            assert '__GNUC__' in macros
            # Should have many macros
            assert len(macros) > 50  # GCC typically defines 100+ macros