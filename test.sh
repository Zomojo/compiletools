#!/bin/sh

set -e

#
# Test cpp compilation (debug and release)
#

./cake --quiet tests/helloworld_cpp.cpp

result=$(bin/helloworld_cpp)
if [[ $result != "debug 1" ]]; then
    echo test 1: Incorrect variant: $result
    exit 1
fi

./cake --quiet tests/helloworld_cpp.cpp --variant=release

result=$(bin/helloworld_cpp)
if [[ $result != "release 1" ]]; then
    echo test 2: Incorrect variant: $result
    exit 1
fi

result=$(bin/helloworld_cpp extra args)
if [[ $result != "release 3" ]]; then
    echo test 3: Incorrect args: $result
    exit 1
fi


#
# Test c compilation  (debug and release)
#

./cake --quiet tests/helloworld_c.c

result=$(bin/helloworld_c)
if [[ $result != "debug 1" ]]; then
    echo test 4: Incorrect variant: $result
    exit 1
fi

./cake --quiet tests/helloworld_c.c --variant=release

result=$(bin/helloworld_c)
if [[ $result != "release 1" ]]; then
    echo test 5: Incorrect variant: $result
    exit 1
fi

result=$(bin/helloworld_c extra args)
if [[ $result != "release 3" ]]; then
    echo test 6: Incorrect args: $result
    exit 1
fi


#
# Test static library compilation
#
./cake --static-library tests/get_numbers.cpp
./cake tests/test_static_library.cpp
result=$(bin/test_static_library)
if [[ $result != "1 2" ]]; then
    echo test 5: Incorrect result from static library test: $result
    exit 1
fi

