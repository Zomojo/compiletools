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
        # Use existing sample that has includes and commented includes
        import os
        # Get path relative to this test file  
        test_dir = os.path.dirname(__file__)
        filepath = os.path.join(test_dir, "samples", "simple", "helloworld_c.c")
        
        legacy = LegacyFileAnalyzer(filepath, max_read_size=0, verbose=0)
        legacy_result = legacy.analyze()
        
        # Test that both implementations produce identical results
        # Note: StringZillaFileAnalyzer will fall back to LegacyFileAnalyzer when StringZilla unavailable
        stringzilla = None
        try:
            stringzilla = StringZillaFileAnalyzer(filepath, max_read_size=0, verbose=0)
            stringzilla_result = stringzilla.analyze()
            
            # Compare results - they must be identical
            assert legacy_result.text == stringzilla_result.text
            assert legacy_result.include_positions == stringzilla_result.include_positions
            assert legacy_result.magic_positions == stringzilla_result.magic_positions
            assert legacy_result.directive_positions == stringzilla_result.directive_positions
            assert legacy_result.bytes_analyzed == stringzilla_result.bytes_analyzed
            assert legacy_result.was_truncated == stringzilla_result.was_truncated
            
        except ImportError:
            # StringZilla not available, just test that legacy works
            assert "stdio.h" in legacy_result.text
            assert "stdlib.h" in legacy_result.text
            # Note: commented includes appear in text but not in include_positions
            assert len(legacy_result.include_positions) == 2  # stdlib.h and stdio.h only
            
    def test_raw_file_analysis(self):
        """Test that FileAnalyzer returns raw file content without preprocessing."""
        # Use existing macro_deps sample which has conditional compilation
        import os
        test_dir = os.path.dirname(__file__)
        filepath = os.path.join(test_dir, "samples", "macro_deps", "main.cpp")
        
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
            assert "#define USE_FEATURE_X" in legacy_result.text
            assert "#include \"feature_header.hpp\"" in legacy_result.text
            assert "int main()" in legacy_result.text
            assert len(legacy_result.include_positions) == 1  # One include in main.cpp
            assert len(legacy_result.magic_positions) == 0  # No magic flags in main.cpp itself
            
    def test_magic_flags(self):
        """Test magic flag detection."""
        # Use existing lotsofmagic sample which has multiple magic flags
        import os
        test_dir = os.path.dirname(__file__)
        filepath = os.path.join(test_dir, "samples", "lotsofmagic", "lotsofmagic.cpp")
        
        legacy = LegacyFileAnalyzer(filepath, max_read_size=0, verbose=0)
        legacy_result = legacy.analyze()
        
        try:
            stringzilla = StringZillaFileAnalyzer(filepath, max_read_size=0, verbose=0)
            stringzilla_result = stringzilla.analyze()
            
            assert legacy_result.magic_positions == stringzilla_result.magic_positions
            assert len(legacy_result.magic_positions) == 6  # LINKFLAGS, F1, F2, F3, LDFLAGS, PKG-CONFIG
            
        except ImportError:
            # Verify magic flag detection in legacy
            assert len(legacy_result.magic_positions) == 6  # LINKFLAGS, F1, F2, F3, LDFLAGS, PKG-CONFIG
            
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
        # Use existing helloworld_c.c which now has commented includes
        import os
        test_dir = os.path.dirname(__file__)
        filepath = os.path.join(test_dir, "samples", "simple", "helloworld_c.c")
        analyzer = LegacyFileAnalyzer(filepath, 0, 0)
        result = analyzer.analyze()
        
        # Should only find the real, uncommented includes
        assert len(result.include_positions) == 2  # stdlib.h and stdio.h
        assert "stdio.h" in result.text
        assert "stdlib.h" in result.text
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
        assert any('stdlib.h' in line for line in include_lines)
        assert any('stdio.h' in line for line in include_lines)
        assert not any('commented_out.h' in line for line in include_lines)
        assert not any('block_commented.h' in line for line in include_lines)
        
    def test_magic_flag_pattern_accuracy(self):
        """Test that magic flag patterns are detected accurately."""
        # Use existing lotsofmagic sample which has various magic flag patterns
        import os
        test_dir = os.path.dirname(__file__)
        filepath = os.path.join(test_dir, "samples", "lotsofmagic", "lotsofmagic.cpp")
        
        analyzer = LegacyFileAnalyzer(filepath, 0, 0)
        result = analyzer.analyze()
        
        # Should find exactly 6 valid magic flags in lotsofmagic.cpp
        # Valid: LINKFLAGS, F1, F2, F3, LDFLAGS, PKG-CONFIG
        assert len(result.magic_positions) == 6
        
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
        
        # Verify expected valid patterns are found
        assert '//#LINKFLAGS=-lpcap' in magic_lines
        assert '//#PKG-CONFIG=zlib' in magic_lines
        assert '//#LDFLAGS=-lm' in magic_lines
        
        # Verify invalid patterns are not detected
        # These appear in the file text but should not be in magic_positions
        assert '// #LIBS=not_magic (space before #)' in result.text
        assert '/* //#LIBS=commented_out */' in result.text
        # But they should not be in the detected magic positions
        invalid_patterns = ['// #LIBS=not_magic', '/* //#LIBS=commented_out */']
        for pattern in invalid_patterns:
            assert not any(pattern in line for line in magic_lines)
        
    def test_directive_position_accuracy(self):
        """Test that all preprocessor directives are found in raw text."""
        # Use existing conditional_ldflags_test.cpp which has conditional directives
        import os
        test_dir = os.path.dirname(__file__)
        filepath = os.path.join(test_dir, "samples", "ldflags", "conditional_ldflags_test.cpp")
        
        analyzer = LegacyFileAnalyzer(filepath, 0, 0)
        result = analyzer.analyze()
        
        # Should find directive types in raw text
        expected_directives = ["include", "ifndef", "else", "endif"]
        for directive in expected_directives:
            assert directive in result.directive_positions, f"Missing directive: {directive}"
            
        # Should have 1 include in raw text
        assert len(result.directive_positions["include"]) == 1
        
        # Should have correct counts for each directive type
        assert len(result.directive_positions["ifndef"]) == 2  # Two ifndef directives  
        assert len(result.directive_positions["else"]) == 2    # Two else directives
        assert len(result.directive_positions["endif"]) == 2   # Two endif directives
        
    def test_stringzilla_simd_pattern_detection(self):
        """Test StringZilla SIMD pattern detection when available."""
        # Use existing lotsofmagic sample which has multiple patterns to test SIMD performance
        import os
        test_dir = os.path.dirname(__file__)
        filepath = os.path.join(test_dir, "samples", "lotsofmagic", "lotsofmagic.cpp")
        
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
            
            # Verify expected pattern counts from lotsofmagic.cpp
            assert len(sz_result.include_positions) == 2  # cmath, iostream
            assert len(sz_result.magic_positions) == 6   # LINKFLAGS, F1, F2, F3, LDFLAGS, PKG-CONFIG
            assert "include" in sz_result.directive_positions
            
        except ImportError:
            # StringZilla not available - just verify legacy works
            legacy = LegacyFileAnalyzer(filepath, 0, 0)
            result = legacy.analyze()
            
            assert len(result.include_positions) == 2  # cmath, iostream
            assert len(result.magic_positions) == 6   # All valid magic flags in lotsofmagic.cpp
            assert "include" in result.directive_positions