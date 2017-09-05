#!/bin/bash

# Build a static library in the subdiretory
pushd mylib >/dev/null
ct-cake --static get_numbers.cpp
popd

# Now build the main.cpp linking against the static library
ct-cake --auto

