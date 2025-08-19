"""Test to verify macro state dependency fix"""

import configargparse
from pathlib import Path
from compiletools.testhelper import samplesdir

import compiletools.headerdeps as headerdeps
import compiletools.apptools

def test_macro_state_dependency_with_different_macros():
    """Test that the same file processed with different macros gives different results"""
    sample_dir = Path(samplesdir()) / "macro_state_dependency"
    test_cpp = Path(sample_dir) / "sample.cpp"
    
    print("Testing macro state dependency with different macros...")
    print(f"Using sample directory: {sample_dir}\n")
    
    # Test 1: Process without DEBUG
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
    
    # Test 2: Process WITH DEBUG using a fresh instance and command-line flag
    print("\nTest 2: Processing WITH DEBUG macro (new instance)...")
    
    # Create a new instance with DEBUG defined via command-line
    cap2 = configargparse.getArgumentParser()
    compiletools.headerdeps.add_arguments(cap2)
    compiletools.apptools.add_common_arguments(cap2)
    
    argv2 = [
        f"--CPPFLAGS=-I{sample_dir} -DDEBUG",
        "-q"
    ]
    args2 = compiletools.apptools.parseargs(cap2, argv2)
    deps2 = headerdeps.DirectHeaderDeps(args2)
    
    # Process the same file again
    includes2 = set(deps2.process(str(test_cpp)))
    
    has_release2 = any("release.h" in str(inc) for inc in includes2)
    has_debug2 = any("debug.h" in str(inc) for inc in includes2)
    
    print(f"  Includes release.h: {has_release2}")
    print(f"  Includes debug.h: {has_debug2}")
    
    # Verify results
    print("\n" + "="*50)
    assert has_release and not has_debug and has_debug2 and not has_release2, (
        "Macro state dependency issue detected or unexpected result: "
        f"has_release={has_release}, has_debug={has_debug}, "
        f"has_release2={has_release2}, has_debug2={has_debug2}"
    )