"""Tests for file_analyzer module ensuring behavioral equivalence between implementations."""

import os
import tempfile
import pytest
from textwrap import dedent
from unittest.mock import patch, MagicMock

from compiletools.file_analyzer import (
    FileAnalysisResult, 
    LegacyFileAnalyzer, 
    StringZillaFileAnalyzer,
    create_file_analyzer
)


class TestFileAnalysisResult:
    """Test FileAnalysisResult dataclass."""
    
    def test_dataclass_creation(self):
        result = FileAnalysisResult(
            text="test content",
            include_positions=[10, 20],
            magic_positions=[5],
            directive_positions={"include": [10, 20], "define": [30]},
            bytes_analyzed=100,
            was_truncated=False
        )
        
        assert result.text == "test content"
        assert result.include_positions == [10, 20]
        assert result.magic_positions == [5]
        assert result.directive_positions == {"include": [10, 20], "define": [30]}
        assert result.bytes_analyzed == 100
        assert result.was_truncated is False


class TestFileAnalyzerImplementations:
    """Test both file analyzer implementations for behavioral equivalence."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_files = {}
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_test_file(self, filename, content):
        """Create a temporary test file with given content."""
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        self.test_files[filename] = filepath
        return filepath
        
    def test_simple_include_file(self):
        """Test both implementations on a simple file with includes."""
        content = dedent('''
            #include <stdio.h>
            #include "local.h"
            // Comment with #include "ignored.h"
            int main() {
                return 0;
            }
        ''').strip()
        
        filepath = self.create_test_file("simple.c", content)
        
        legacy = LegacyFileAnalyzer(filepath, max_read_size=0, verbose=0)
        legacy_result = legacy.analyze()
        
        # Test that both implementations produce identical results
        # Note: StringZillaFileAnalyzer will fall back to LegacyFileAnalyzer when StringZilla unavailable
        stringzilla = None
        try:
            stringzilla = StringZillaFileAnalyzer(filepath, max_read_size=0, verbose=0)
            stringzilla_result = stringzilla.analyze()
            
            # Compare results
            assert legacy_result.text == stringzilla_result.text
            assert legacy_result.include_positions == stringzilla_result.include_positions
            assert legacy_result.magic_positions == stringzilla_result.magic_positions
            assert legacy_result.directive_positions == stringzilla_result.directive_positions
            assert legacy_result.bytes_analyzed == stringzilla_result.bytes_analyzed
            assert legacy_result.was_truncated == stringzilla_result.was_truncated
            
        except ImportError:
            # StringZilla not available, just test that legacy works
            assert "stdio.h" in legacy_result.text
            assert "local.h" in legacy_result.text
            # Note: commented includes appear in text but not in include_positions
            assert len(legacy_result.include_positions) >= 2
            
    def test_raw_file_analysis(self):
        """Test that FileAnalyzer returns raw file content without preprocessing."""
        content = dedent('''
            #define FEATURE_A 1
            #ifdef FEATURE_A
            #include "feature_a.h"
            #endif
            #ifdef FEATURE_B
            #include "feature_b.h"
            #endif
            //#LIBS=somelib
            int main() { return 0; }
        ''').strip()
        
        filepath = self.create_test_file("conditional.c", content)
        
        legacy = LegacyFileAnalyzer(filepath, max_read_size=0, verbose=0)
        legacy_result = legacy.analyze()
        
        try:
            stringzilla = StringZillaFileAnalyzer(filepath, max_read_size=0, verbose=0)
            stringzilla_result = stringzilla.analyze()
            
            # Both should produce identical results
            assert legacy_result.text == stringzilla_result.text
            assert legacy_result.include_positions == stringzilla_result.include_positions
            assert legacy_result.magic_positions == stringzilla_result.magic_positions
            
        except ImportError:
            # StringZilla not available, verify legacy behavior
            # FileAnalyzer returns raw text with all conditional sections
            assert "#define FEATURE_A 1" in legacy_result.text
            assert "#ifdef FEATURE_A" in legacy_result.text
            assert "feature_a.h" in legacy_result.text
            assert "feature_b.h" in legacy_result.text  # Both present in raw text
            assert "#ifdef FEATURE_B" in legacy_result.text
            assert len(legacy_result.magic_positions) >= 1  # Should find //#LIBS
            
    def test_magic_flags(self):
        """Test magic flag detection."""
        content = dedent('''
            // Some header comment
            //#LIBS=pthread m
            //#CFLAGS=-O2 -g
            #include <stdio.h>
            // Regular comment
            //#LDFLAGS=-static
            int main() { return 0; }
        ''').strip()
        
        filepath = self.create_test_file("magic.c", content)
        
        legacy = LegacyFileAnalyzer(filepath, max_read_size=0, verbose=0)
        legacy_result = legacy.analyze()
        
        try:
            stringzilla = StringZillaFileAnalyzer(filepath, max_read_size=0, verbose=0)
            stringzilla_result = stringzilla.analyze()
            
            assert legacy_result.magic_positions == stringzilla_result.magic_positions
            assert len(legacy_result.magic_positions) == 3  # LIBS, CFLAGS, LDFLAGS
            
        except ImportError:
            # Verify magic flag detection in legacy
            assert len(legacy_result.magic_positions) == 3
            
    def test_max_read_size_limits(self):
        """Test that max_read_size is respected."""
        large_content = "#include <stdio.h>\n" + "// filler\n" * 1000 + "#include <stdlib.h>\n"
        
        filepath = self.create_test_file("large.c", large_content)
        
        # Test with small read size
        legacy_small = LegacyFileAnalyzer(filepath, max_read_size=100, verbose=0)
        result_small = legacy_small.analyze()
        
        # Test with large read size
        legacy_large = LegacyFileAnalyzer(filepath, max_read_size=0, verbose=0)
        result_large = legacy_large.analyze()
        
        # Small read should be truncated
        assert result_small.was_truncated or result_small.bytes_analyzed <= 100
        
        # Large read should get more content
        assert result_large.bytes_analyzed > result_small.bytes_analyzed
        
    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        filepath = os.path.join(self.temp_dir, "nonexistent.c")
        
        legacy = LegacyFileAnalyzer(filepath, max_read_size=0, verbose=0)
        result = legacy.analyze()
        
        assert result.text == ""
        assert result.include_positions == []
        assert result.magic_positions == []
        assert result.directive_positions == {}
        assert result.bytes_analyzed == 0
        assert result.was_truncated is False
        
    def test_empty_file(self):
        """Test handling of empty files."""
        filepath = self.create_test_file("empty.c", "")
        
        legacy = LegacyFileAnalyzer(filepath, max_read_size=0, verbose=0)
        result = legacy.analyze()
        
        assert result.text == ""
        assert result.include_positions == []
        assert result.magic_positions == []
        assert result.bytes_analyzed == 0
        assert result.was_truncated is False


class TestFileAnalyzerFactory:
    """Test the factory function."""
    
    def test_factory_fallback_when_stringzilla_unavailable(self):
        """Test factory falls back to legacy when StringZilla unavailable."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write("#include <stdio.h>")
            filepath = f.name
            
        try:
            analyzer = create_file_analyzer(filepath, 0, 0)
            
            # Should get some kind of analyzer
            assert analyzer is not None
            result = analyzer.analyze()
            assert isinstance(result, FileAnalysisResult)
            
        finally:
            os.unlink(filepath)
            
    @patch('compiletools.file_analyzer.StringZillaFileAnalyzer')
    def test_factory_uses_stringzilla_when_available(self, mock_stringzilla):
        """Test factory uses StringZilla when available."""
        # Mock StringZilla to be available
        mock_instance = MagicMock()
        mock_stringzilla.return_value = mock_instance
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write("#include <stdio.h>")
            filepath = f.name
            
        try:
            analyzer = create_file_analyzer(filepath, 0, 0)
            
            # Should have tried to create StringZilla analyzer
            mock_stringzilla.assert_called_once_with(filepath, 0, 0)
            assert analyzer == mock_instance
            
        finally:
            os.unlink(filepath)


class TestPatternDetectionAccuracy:
    """Test pattern detection accuracy and edge cases."""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_test_file(self, content):
        filepath = os.path.join(self.temp_dir, "test.c")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
        
    def test_commented_includes_ignored(self):
        """Test that commented includes are properly ignored in position detection."""
        content = dedent('''
            #include <stdio.h>
            // #include "commented_out.h"
            /* #include "block_commented.h" */
            #include "real.h"
            // Another comment with #include "also_ignored.h"
        ''').strip()
        
        filepath = self.create_test_file(content)
        analyzer = LegacyFileAnalyzer(filepath, 0, 0)
        result = analyzer.analyze()
        
        # Should only find the real, uncommented includes
        assert len(result.include_positions) == 2  # stdio.h and real.h
        assert "stdio.h" in result.text
        assert "real.h" in result.text
        assert "commented_out.h" in result.text  # Present in raw text
        assert "block_commented.h" in result.text  # Present in raw text
        
        # But positions should only point to uncommented includes
        include_lines = []
        lines = result.text.split('\n')
        for pos in result.include_positions:
            # Find which line this position is on
            char_count = 0
            for i, line in enumerate(lines):
                if char_count <= pos < char_count + len(line) + 1:  # +1 for newline
                    include_lines.append(line.strip())
                    break
                char_count += len(line) + 1
        
        # Should find only the real includes, not commented ones
        assert any('stdio.h' in line for line in include_lines)
        assert any('real.h' in line for line in include_lines)
        assert not any('commented_out.h' in line for line in include_lines)
        assert not any('block_commented.h' in line for line in include_lines)
        
    def test_magic_flag_pattern_accuracy(self):
        """Test that magic flag patterns are detected accurately."""
        content = dedent('''
            // Valid magic flags
            //#LIBS=pthread m
            //# CFLAGS = -O2 -g
            //#PKG-CONFIG=zlib
            
            // Invalid patterns that should NOT be detected  
            // #LIBS=not_magic (space before #)
            /* //#LIBS=commented_out */
            #LIBS=not_comment_magic
            //#INVALID PATTERN (no =)
            //#123=invalid_start_with_number
        ''').strip()
        
        filepath = self.create_test_file(content)
        analyzer = LegacyFileAnalyzer(filepath, 0, 0)
        result = analyzer.analyze()
        
        # Should find exactly 2 valid magic flags matching magicflags.py behavior
        # Valid: //#LIBS=pthread m, //#PKG-CONFIG=zlib  
        # Invalid: //# CFLAGS = -O2 -g (space after #), // #LIBS=not_magic (space before #), /* //#LIBS=commented_out */
        expected_count = 2  
        assert len(result.magic_positions) == expected_count
        
        # Verify which patterns were found
        magic_lines = []
        lines = result.text.split('\n')
        for pos in result.magic_positions:
            char_count = 0
            for i, line in enumerate(lines):
                if char_count <= pos < char_count + len(line) + 1:
                    magic_lines.append(line.strip())
                    break
                char_count += len(line) + 1
        
        assert '//#LIBS=pthread m' in magic_lines
        assert '//#PKG-CONFIG=zlib' in magic_lines
        # This should NOT be found due to space after #
        assert '//# CFLAGS = -O2 -g' not in magic_lines
        
    def test_directive_position_accuracy(self):
        """Test that all preprocessor directives are found in raw text."""
        content = dedent('''
            #include <stdio.h>
            #define TEST_MACRO 1
            #ifdef TEST_MACRO
            #include "conditional.h"
            #endif
            #undef TEST_MACRO
            #ifndef UNDEFINED_MACRO
            #include "another.h"
            #endif
        ''').strip()
        
        filepath = self.create_test_file(content)
        analyzer = LegacyFileAnalyzer(filepath, 0, 0)
        result = analyzer.analyze()
        
        # Should find all directive types in raw text
        expected_directives = ["include", "define", "ifdef", "endif", "undef", "ifndef"]
        for directive in expected_directives:
            assert directive in result.directive_positions, f"Missing directive: {directive}"
            
        # Should have 3 includes in raw text
        assert len(result.directive_positions["include"]) == 3
        
        # Should have correct counts for each directive type
        assert len(result.directive_positions["define"]) == 1
        assert len(result.directive_positions["ifdef"]) == 1
        assert len(result.directive_positions["endif"]) == 2  # Two endif directives
        assert len(result.directive_positions["undef"]) == 1
        assert len(result.directive_positions["ifndef"]) == 1
        
    def test_stringzilla_simd_pattern_detection(self):
        """Test StringZilla SIMD pattern detection when available."""
        content = dedent('''
            #include <stdio.h>
            //#LIBS=pthread math
            #define FEATURE 1
            #ifdef FEATURE
            //#CFLAGS=-O2
            #include "optimized.h"  
            #endif
            //#LDFLAGS=-static
        ''').strip()
        
        filepath = self.create_test_file(content)
        
        try:
            # Test StringZilla directly
            stringzilla = StringZillaFileAnalyzer(filepath, 0, 0)
            sz_result = stringzilla.analyze()
            
            # Test Legacy for comparison
            legacy = LegacyFileAnalyzer(filepath, 0, 0)
            legacy_result = legacy.analyze()
            
            # Both should produce identical results
            assert sz_result.text == legacy_result.text
            assert sz_result.include_positions == legacy_result.include_positions
            assert sz_result.magic_positions == legacy_result.magic_positions  
            assert sz_result.directive_positions == legacy_result.directive_positions
            assert sz_result.bytes_analyzed == legacy_result.bytes_analyzed
            assert sz_result.was_truncated == legacy_result.was_truncated
            
            # Verify expected pattern counts
            assert len(sz_result.include_positions) == 2  # stdio.h, optimized.h
            assert len(sz_result.magic_positions) == 3   # LIBS, CFLAGS, LDFLAGS (all valid format)
            assert "include" in sz_result.directive_positions
            assert "define" in sz_result.directive_positions
            assert "ifdef" in sz_result.directive_positions
            
        except ImportError:
            # StringZilla not available - just verify legacy works
            legacy = LegacyFileAnalyzer(filepath, 0, 0)
            result = legacy.analyze()
            
            assert len(result.include_positions) == 2
            assert len(result.magic_positions) == 3  # This content has valid magic flags
            assert "include" in result.directive_positions