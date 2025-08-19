"""Test demonstrating the header dependency macro state dependency fix"""

import os
from pathlib import Path
import configargparse

import compiletools.headerdeps as headerdeps
import compiletools.hunter as hunter
import compiletools.magicflags as magicflags
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
    
    # Assert expected behavior: without DEBUG should include release.h, with DEBUG should include debug.h
    assert has_release and not has_debug, f"Test 1 should include release.h only, got release={has_release}, debug={has_debug}"
    assert has_debug2 and not has_release2, f"Test 2 should include debug.h only, got release={has_release2}, debug={has_debug2}"
    
    print("✓ SUCCESS: Different macro states produce different results!")
    print("  Without DEBUG -> includes release.h")
    print("  With DEBUG    -> includes debug.h")
    print("\nThe macro state dependency issue has been fixed! Before the fix, both cases")
    print("would have included release.h due to cached results.")


def test_hunter_respects_macro_state_changes():
    """Test that Hunter correctly handles macro state changes (regression test)
    
    This test prevents regression of the macro state dependency bug where Hunter
    would return cached results that didn't account for changed macro definitions.
    
    The bug occurred when @functools.lru_cache was used on Hunter methods - the cache
    key was based only on filename, but results depend on macro state in headerdeps/magicparser.
    """
    
    # Get the directory containing this test file
    sample_dir = Path(__file__).parent.absolute()
    test_cpp = sample_dir / "sample.cpp"
    
    def create_hunter_with_macros(debug_enabled=False):
        """Helper to create Hunter instance with specified macro configuration"""
        cap = configargparse.getArgumentParser()
        compiletools.headerdeps.add_arguments(cap)
        compiletools.magicflags.add_arguments(cap)
        hunter.add_arguments(cap)
        compiletools.apptools.add_common_arguments(cap)
        
        cppflags = f"-I{sample_dir}"
        if debug_enabled:
            cppflags += " -DDEBUG"
            
        argv = [f"--CPPFLAGS={cppflags}", "-q"]
        args = compiletools.apptools.parseargs(cap, argv)
        
        deps = headerdeps.DirectHeaderDeps(args)
        magic = magicflags.create(args, deps)
        return hunter.Hunter(args, deps, magic)
    
    # Test 1: Without DEBUG macro should include release.h
    hunter.Hunter.clear_cache()
    hunter_no_debug = create_hunter_with_macros(debug_enabled=False)
    files_no_debug = set(hunter_no_debug.required_files(str(test_cpp)))
    
    has_release_no_debug = any("release.h" in str(f) for f in files_no_debug)
    has_debug_no_debug = any("debug.h" in str(f) for f in files_no_debug)
    
    assert has_release_no_debug and not has_debug_no_debug, \
        f"Without DEBUG macro should include release.h only, got release={has_release_no_debug}, debug={has_debug_no_debug}"
    
    # Test 2: With DEBUG macro should include debug.h  
    hunter_with_debug = create_hunter_with_macros(debug_enabled=True)
    files_with_debug = set(hunter_with_debug.required_files(str(test_cpp)))
    
    has_release_with_debug = any("release.h" in str(f) for f in files_with_debug)
    has_debug_with_debug = any("debug.h" in str(f) for f in files_with_debug)
    
    assert has_debug_with_debug and not has_release_with_debug, \
        f"With DEBUG macro should include debug.h only, got release={has_release_with_debug}, debug={has_debug_with_debug}"
    
    # Test 3: Same Hunter instance with changed dependencies (the critical regression test)
    # This test would fail if someone reintroduced @lru_cache decorators
    hunter_instance = create_hunter_with_macros(debug_enabled=False)
    
    # First call without DEBUG
    files1 = set(hunter_instance.required_files(str(test_cpp)))
    has_release1 = any("release.h" in str(f) for f in files1)
    has_debug1 = any("debug.h" in str(f) for f in files1)
    
    assert has_release1 and not has_debug1, \
        f"Initial call should include release.h, got release={has_release1}, debug={has_debug1}"
    
    # Change the Hunter instance's dependencies to include DEBUG
    hunter_with_debug_deps = create_hunter_with_macros(debug_enabled=True)
    hunter_instance.args = hunter_with_debug_deps.args
    hunter_instance.headerdeps = hunter_with_debug_deps.headerdeps  
    hunter_instance.magicparser = hunter_with_debug_deps.magicparser
    
    # Second call with changed macro state - this is the regression test
    files2 = set(hunter_instance.required_files(str(test_cpp)))
    has_release2 = any("release.h" in str(f) for f in files2)
    has_debug2 = any("debug.h" in str(f) for f in files2)
    
    # This assertion will fail if the cache bug is reintroduced
    assert has_debug2 and not has_release2, \
        f"Hunter must respect macro state changes. Expected debug.h with DEBUG macro, " \
        f"got release={has_release2}, debug={has_debug2}. " \
        f"This suggests cached results from previous macro state (cache regression bug)."
        