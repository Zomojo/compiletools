"""Dynamic compiler macro detection module.

This module queries compilers for their predefined macros rather than
hardcoding them, allowing automatic adaptation to new compiler versions.
"""

import subprocess
from functools import lru_cache
from typing import Dict


@lru_cache(maxsize=32)
def get_compiler_macros(compiler_path: str, verbose: int = 0) -> Dict[str, str]:
    """Query a compiler for its predefined macros.
    
    Args:
        compiler_path: Path to the compiler executable (e.g., 'gcc', 'clang')
        verbose: Verbosity level for debug output
        
    Returns:
        Dictionary of macro names to their values
    """
    if not compiler_path:
        if verbose >= 2:
            print("No compiler specified, returning empty macro dict")
        return {}
    
    try:
        # Use -dM to dump macros, -E to preprocess only, - to read from stdin
        result = subprocess.run(
            [compiler_path, '-dM', '-E', '-'],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            if verbose >= 4:
                print(f"Compiler {compiler_path} returned non-zero exit code: {result.returncode}")
            return {}
        
        macros = {}
        for line in result.stdout.splitlines():
            # Parse lines like: #define __GNUC__ 11
            if line.startswith('#define '):
                parts = line[8:].split(None, 1)  # Split after '#define '
                if parts:
                    macro_name = parts[0]
                    macro_value = parts[1] if len(parts) > 1 else "1"
                    # Remove surrounding quotes if present
                    if macro_value.startswith('"') and macro_value.endswith('"'):
                        macro_value = macro_value[1:-1]
                    macros[macro_name] = macro_value
        
        if verbose >= 3:
            print(f"Queried {len(macros)} macros from {compiler_path}")
            if verbose >= 8:
                import pprint
                print("Sample of detected macros:")
                pprint.pprint(dict(sorted(macros.items())[:20]))  # Show first 20
        
        return macros
        
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        if verbose >= 3:
            print(f"Failed to query macros from {compiler_path}: {e}")
        return {}


def clear_cache():
    """Clear the LRU cache for get_compiler_macros."""
    get_compiler_macros.cache_clear()