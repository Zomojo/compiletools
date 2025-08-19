#!/usr/bin/env python3
"""Test demonstrating the header dependency macro state dependency fix"""

import sys
import os
from pathlib import Path
import configargparse

# Add parent directories to path for testing
sys.path.insert(0, '/home/gericksson/compiletools/src')

import compiletools.headerdeps as headerdeps
import compiletools.apptools

def test_macro_state_dependency_is_fixed():
    """Demonstrate that different macro states produce different results"""
    
    # Get the directory containing this test file
    sample_dir = Path(__file__).parent.absolute()
    test_cpp = sample_dir / "sample.cpp"
    
    print("Testing header dependency macro state dependency fix...")
    print(f"Sample directory: {sample_dir}\n")
    
    # Test 1: Process without DEBUG macro
    print("Test 1: Processing without DEBUG macro...")
    cap = configargparse.getArgumentParser()
    compiletools.headerdeps.add_arguments(cap)
    compiletools.apptools.add_common_arguments(cap)
    
    argv = [
        f"--CPPFLAGS=-I{sample_dir}",
        "-q"
    ]
    args = compiletools.apptools.parseargs(cap, argv)
    headerdeps.HeaderDepsBase.clear_cache()
    
    deps1 = headerdeps.DirectHeaderDeps(args)
    includes1 = set(deps1.process(str(test_cpp)))
    
    has_release = any("release.h" in str(inc) for inc in includes1)
    has_debug = any("debug.h" in str(inc) for inc in includes1)
    
    print(f"  Includes release.h: {has_release}")
    print(f"  Includes debug.h: {has_debug}")
    
    # Test 2: Process WITH DEBUG macro using fresh instance
    print("\nTest 2: Processing WITH DEBUG macro...")
    
    cap2 = configargparse.getArgumentParser()
    compiletools.headerdeps.add_arguments(cap2)
    compiletools.apptools.add_common_arguments(cap2)
    
    argv2 = [
        f"--CPPFLAGS=-I{sample_dir} -DDEBUG",
        "-q"
    ]
    args2 = compiletools.apptools.parseargs(cap2, argv2)
    deps2 = headerdeps.DirectHeaderDeps(args2)
    
    includes2 = set(deps2.process(str(test_cpp)))
    
    has_release2 = any("release.h" in str(inc) for inc in includes2)
    has_debug2 = any("debug.h" in str(inc) for inc in includes2)
    
    print(f"  Includes release.h: {has_release2}")
    print(f"  Includes debug.h: {has_debug2}")
    
    # Verify expected behavior
    print("\n" + "="*60)
    print("Macro State Dependency Fix Verification:")
    print("="*60)
    
    if has_release and not has_debug and has_debug2 and not has_release2:
        print("✓ SUCCESS: Different macro states produce different results!")
        print("  Without DEBUG -> includes release.h")
        print("  With DEBUG    -> includes debug.h")
        print("\nThe macro state dependency issue has been fixed! Before the fix, both cases")
        print("would have included release.h due to cached results.")
        assert True  # Test passes
    else:
        print("❌ FAILURE: Expected behavior not observed")
        print(f"  Test 1 (no DEBUG): release={has_release}, debug={has_debug}")
        print(f"  Test 2 (with DEBUG): release={has_release2}, debug={has_debug2}")
        assert False  # Test fails

if __name__ == "__main__":
    try:
        test_macro_state_dependency_is_fixed()
        sys.exit(0)
    except AssertionError:
        sys.exit(1)