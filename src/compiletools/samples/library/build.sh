#!/usr/bin/bash

# Build a static library in the subdiretory
# If you would like to do a dynamic library (i.e., .so)
# then use --dynamic rather than --static
pushd mylib >/dev/null
ct-cake --static get_numbers.cpp "$@"
popd

# Now build the main.cpp linking against the static library
ct-cake --auto "$@"

