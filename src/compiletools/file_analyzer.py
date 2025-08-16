"""File analysis module for efficient pattern detection in source files.

This module provides SIMD-optimized file analysis with StringZilla when available,
falling back to traditional regex-based analysis for compatibility.
"""

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from io import open

import compiletools.wrappedos


@dataclass
class FileAnalysisResult:
    """Standardized result from file analysis containing pattern positions and content."""
    text: str                               # Actual text content (respects max_read_size)
    include_positions: List[int]            # Positions of #include statements  
    magic_positions: List[int]              # Positions of //#KEY= patterns
    directive_positions: Dict[str, List[int]]  # All preprocessor directive positions by type
    bytes_analyzed: int                     # How much of file was actually processed
    was_truncated: bool                     # Whether file was larger than max_read_size


class FileAnalyzer(ABC):
    """Base class for file analysis implementations.
    
    Ensures both StringZilla and Legacy implementations produce identical structured data.
    """
    
    def __init__(self, filepath: str, max_read_size: int = 0, verbose: int = 0):
        """Initialize file analyzer.
        
        Args:
            filepath: Path to file to analyze
            max_read_size: Maximum bytes to read (0 = entire file)
            verbose: Verbosity level for debugging
        """
        self.filepath = compiletools.wrappedos.realpath(filepath)
        self.max_read_size = max_read_size
        self.verbose = verbose
        
    @abstractmethod
    def analyze(self) -> FileAnalysisResult:
        """Analyze file and return structured results.
        
        Returns:
            FileAnalysisResult with all pattern positions and content
        """
        pass
        
    def _should_read_entire_file(self, file_size: Optional[int] = None) -> bool:
        """Determine if entire file should be read based on configuration."""
        if self.max_read_size == 0:
            return True
        if file_size and file_size <= self.max_read_size:
            return True
        return False


class LegacyFileAnalyzer(FileAnalyzer):
    """Reference implementation using traditional regex/string operations."""
    
    def analyze(self) -> FileAnalysisResult:
        """Analyze file using regex patterns for compatibility."""
        if not os.path.exists(self.filepath):
            return FileAnalysisResult(
                text="", include_positions=[], magic_positions=[],
                directive_positions={}, bytes_analyzed=0, was_truncated=False
            )
            
        try:
            file_size = os.path.getsize(self.filepath)
            read_entire_file = self._should_read_entire_file(file_size)
            
            with open(self.filepath, encoding="utf-8", errors="ignore") as f:
                if read_entire_file:
                    text = f.read()
                    bytes_analyzed = len(text.encode('utf-8'))
                    was_truncated = False
                else:
                    text = f.read(self.max_read_size)
                    bytes_analyzed = len(text.encode('utf-8'))
                    was_truncated = bytes_analyzed >= self.max_read_size
                    
        except (IOError, OSError):
            return FileAnalysisResult(
                text="", include_positions=[], magic_positions=[],
                directive_positions={}, bytes_analyzed=0, was_truncated=False
            )
            
        # Find pattern positions in the raw text (before preprocessing)
        # Note: Conditional compilation should be handled by the caller
        include_positions = self._find_include_positions(text)
        magic_positions = self._find_magic_positions(text)
        directive_positions = self._find_directive_positions(text)
        
        return FileAnalysisResult(
            text=text,
            include_positions=include_positions,
            magic_positions=magic_positions,
            directive_positions=directive_positions,
            bytes_analyzed=bytes_analyzed,
            was_truncated=was_truncated
        )
        
    def _find_include_positions(self, text: str) -> List[int]:
        """Find positions of all #include statements."""
        positions = []
        # Pattern matches #include statements but not commented ones
        pattern = re.compile(
            r'/\*.*?\*/|//.*?$|^[\s]*#include[\s]*["<][\s]*([\S]*)[\s]*[">]',
            re.MULTILINE | re.DOTALL
        )
        
        for match in pattern.finditer(text):
            if match.group(1):  # Only if we captured an include filename
                positions.append(match.start())
                
        return positions
        
    def _find_magic_positions(self, text: str) -> List[int]:
        """Find positions of all //#KEY=value patterns."""
        positions = []
        # Pattern must match the exact behavior of magicflags.py regex:
        # ^[\s]*//#([\S]*?)[\s]*=[\s]*(.*)
        # This means optional whitespace at start, then //#, then key=value
        pattern = re.compile(r'^[\s]*//#([A-Za-z_][A-Za-z0-9_-]*)\s*=', re.MULTILINE)
        
        for match in pattern.finditer(text):
            positions.append(match.start())
            
        return positions
        
    def _find_directive_positions(self, text: str) -> Dict[str, List[int]]:
        """Find positions of all preprocessor directives by type."""
        directive_positions = {}
        
        # Pattern to match preprocessor directives
        pattern = re.compile(r'^(\s*)#\s*([a-zA-Z_]+)', re.MULTILINE)
        
        for match in pattern.finditer(text):
            directive_name = match.group(2)
            if directive_name not in directive_positions:
                directive_positions[directive_name] = []
            # Position should be at the # character, not at start of whitespace
            hash_position = match.start() + len(match.group(1))  # Skip leading whitespace
            directive_positions[directive_name].append(hash_position)
            
        return directive_positions


class StringZillaFileAnalyzer(FileAnalyzer):
    """SIMD-optimized implementation using StringZilla when available."""
    
    def __init__(self, filepath: str, max_read_size: int = 0, verbose: int = 0):
        super().__init__(filepath, max_read_size, verbose)
        try:
            from stringzilla import Str, File
            self._stringzilla_available = True
        except ImportError:
            self._stringzilla_available = False
            raise ImportError("StringZilla not available, use LegacyFileAnalyzer")
    
    def analyze(self) -> FileAnalysisResult:
        """Analyze file using StringZilla SIMD optimization."""
        if not self._stringzilla_available:
            raise RuntimeError("StringZilla not available")
            
        if not os.path.exists(self.filepath):
            return FileAnalysisResult(
                text="", include_positions=[], magic_positions=[],
                directive_positions={}, bytes_analyzed=0, was_truncated=False
            )
            
        try:
            from stringzilla import Str, File
            
            file_size = os.path.getsize(self.filepath)
            read_entire_file = self._should_read_entire_file(file_size)
            
            if read_entire_file:
                # Memory-map entire file
                str_file = Str(File(self.filepath))
                text = str(str_file)
                bytes_analyzed = len(text.encode('utf-8'))
                was_truncated = False
            else:
                # Read limited amount
                with open(self.filepath, encoding="utf-8", errors="ignore") as f:
                    text = f.read(self.max_read_size)
                    bytes_analyzed = len(text.encode('utf-8'))
                    was_truncated = bytes_analyzed >= self.max_read_size
                    
        except (IOError, OSError):
            return FileAnalysisResult(
                text="", include_positions=[], magic_positions=[],
                directive_positions={}, bytes_analyzed=0, was_truncated=False
            )
            
        # Use StringZilla for fast pattern detection on raw text
        # Note: Conditional compilation should be handled by the caller
        str_text = Str(text)
        include_positions = self._find_include_positions_simd(str_text)
        magic_positions = self._find_magic_positions_simd(str_text)
        directive_positions = self._find_directive_positions_simd(str_text)
        
        return FileAnalysisResult(
            text=text,
            include_positions=include_positions,
            magic_positions=magic_positions,
            directive_positions=directive_positions,
            bytes_analyzed=bytes_analyzed,
            was_truncated=was_truncated
        )
        
    def _find_include_positions_simd(self, str_text) -> List[int]:
        """Find positions of all #include statements using StringZilla."""
        positions = []
        
        # Find all #include occurrences
        start = 0
        while True:
            pos = str_text.find('#include', start)
            if pos == -1:
                break
                
            # Verify this is a real include (not in comment)
            line_start = str_text.rfind('\n', 0, pos) + 1
            line_prefix = str(str_text[line_start:pos]).strip()
            
            # Check if line starts with // or is inside /* */
            if not line_prefix.startswith('//') and '/*' not in line_prefix:
                positions.append(pos)
                
            start = pos + 8  # len('#include')
            
        return positions
        
    def _find_magic_positions_simd(self, str_text) -> List[int]:
        """Find positions of all //#KEY=value patterns using StringZilla."""
        positions = []
        
        # Find all //# occurrences (must be immediately adjacent, no space between // and #)
        start = 0
        while True:
            pos = str_text.find('//#', start)
            if pos == -1:
                break
                
            # Check if this //# is at start of line (after optional whitespace)
            line_start = str_text.rfind('\n', 0, pos) + 1
            line_prefix = str(str_text[line_start:pos]).strip()
            
            if line_prefix == '':  # Only whitespace before //#
                # Look for KEY=value pattern after //#
                after_hash = pos + 3
                line_end = str_text.find('\n', after_hash)
                if line_end == -1:
                    line_end = len(str_text)
                    
                line_content = str(str_text[after_hash:line_end])
                if '=' in line_content:
                    # Verify it matches KEY=value pattern with valid identifier
                    key_part = line_content.split('=')[0].strip()
                    # Key must start with letter or underscore, contain only alphanumeric and underscores/dashes
                    if (key_part and 
                        (key_part[0].isalpha() or key_part[0] == '_') and 
                        all(c.isalnum() or c in '_-' for c in key_part)):
                        positions.append(pos)
                    
            start = pos + 3  # len('//#')
            
        return positions
        
    def _find_directive_positions_simd(self, str_text) -> Dict[str, List[int]]:
        """Find positions of all preprocessor directives using StringZilla."""
        directive_positions = {}
        
        # Find all # characters that could start directives
        start = 0
        while True:
            pos = str_text.find('#', start)
            if pos == -1:
                break
                
            # Check if this # is at start of line (ignoring whitespace)
            line_start = str_text.rfind('\n', 0, pos) + 1
            line_prefix = str(str_text[line_start:pos])
            
            if line_prefix.strip() == '':  # Only whitespace before #
                # Find the directive name
                directive_start = pos + 1
                while directive_start < len(str_text) and str_text[directive_start].isspace():
                    directive_start += 1
                    
                directive_end = directive_start
                while (directive_end < len(str_text) and 
                       (str_text[directive_end].isalnum() or str_text[directive_end] == '_')):
                    directive_end += 1
                    
                if directive_end > directive_start:
                    directive_name = str(str_text[directive_start:directive_end])
                    if directive_name not in directive_positions:
                        directive_positions[directive_name] = []
                    directive_positions[directive_name].append(pos)
                    
            start = pos + 1
            
        return directive_positions


def create_file_analyzer(filepath: str, max_read_size: int = 0, verbose: int = 0) -> FileAnalyzer:
    """Factory function to create appropriate FileAnalyzer implementation.
    
    Args:
        filepath: Path to file to analyze
        max_read_size: Maximum bytes to read (0 = entire file)
        verbose: Verbosity level for debugging
        
    Returns:
        StringZillaFileAnalyzer if available, otherwise LegacyFileAnalyzer
    """
    try:
        return StringZillaFileAnalyzer(filepath, max_read_size, verbose)
    except ImportError:
        if verbose >= 3:
            print("StringZilla not available, using legacy file analyzer")
        return LegacyFileAnalyzer(filepath, max_read_size, verbose)