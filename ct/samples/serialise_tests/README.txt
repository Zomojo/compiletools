The objective of this test is to pass when "--serialise-tests" is used and fail if the tests are run in parallel.
It works by having 2 tests.  They both try to obtain a lock on the same file and throw if they cant.

# This should fail
ct-cake --auto 

# This should pass
ct-cake --auto -j1

# This should pass
ct-cake --auto --serialise-tests