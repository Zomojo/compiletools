#!/bin/sh

set -e

result=`./cake --quiet --CXXFLAGS="-DNDEBUG -O3" tests/1.cpp`
if [[ $result != "release 1" ]]; then
    echo test 1: Incorrect variant: $result
    exit 1
fi
sleep 1

result=`./cake --quiet tests/1.cpp`
if [[ $result != "debug 1" ]]; then
    echo test 2: Incorrect variant: $result
    exit 1
fi

result=`./cake --quiet tests/1.cpp hello world`
if [[ $result != "debug 3" ]]; then
    echo test 3: Incorrect args: $result
    exit 1
fi
