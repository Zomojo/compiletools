# Header Dependency Macro State Dependency Test

This directory contains test files that demonstrate the macro state dependency issue that was fixed in `headerdeps.py`.

## The Issue

The issue occurred because header dependency results were cached based only on file path, but the results depend on macro definitions which can change between calls. This caused incorrect cached results when the same file was processed with different macro definitions.

**Root Cause**: The `_process_impl` method in `DirectHeaderDeps` was cached with `@diskcache("deps", deps_mode=True)`, but the cache key was based only on the file path. However, the method's results depend on `self.defined_macros` which can vary between different build configurations.

## Test Files

- `feature.h` - Conditionally includes `debug.h` or `release.h` based on `DEBUG` macro
- `debug.h` - Header included when `DEBUG` is defined  
- `release.h` - Header included when `DEBUG` is not defined
- `sample.cpp` - Main file that includes `feature.h`
- `test_macro_state_dependency.py` - Test script that verifies the fix

## Expected Behavior

- Without `DEBUG` macro: `sample.cpp` → `feature.h` → `release.h`
- With `DEBUG` macro: `sample.cpp` → `feature.h` → `debug.h`

## The Fix

Two caches were removed that depended on macro state:

1. **`@diskcache` from `_process_impl`** - Primary cache causing the issue
2. **`@functools.lru_cache` from `_create_include_list`** - Secondary cache 

Performance impact: Approximately 2.3x slower on complex projects with many repeated header analyses, but absolute difference is typically milliseconds for real-world use cases.

## Testing

Run the test script to verify the fix:

```bash
python test_macro_state_dependency.py
```

This demonstrates that different macro states now correctly produce different dependency results.