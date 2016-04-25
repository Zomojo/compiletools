#!/bin/sh

set -e

#
# What sort of config should we use for these tests
#
CONFIG=$(./cake-config-chooser)

counter=0
#
# Test cpp compilation (debug and release)
#

./cake --quiet tests/helloworld_cpp.cpp --config=$CONFIG "$@"

result=$(bin/helloworld_cpp)
((++counter))
if [ "$result" != "debug 1" ]; then
    echo test $counter: Incorrect variant: $result
    exit 1
fi

./cake --quiet tests/helloworld_cpp.cpp --variant=release --config=$CONFIG "$@"

result=$(bin/helloworld_cpp)
((++counter))
if [ "$result" != "release 1" ]; then
    echo test $counter: Incorrect variant: $result
    exit 1
fi

result=$(bin/helloworld_cpp extra args)
((++counter))
if [ "$result" != "release 3" ]; then
    echo test $counter: Incorrect args: $result
    exit 1
fi


#
# Test c compilation  (debug and release)
#

./cake --quiet tests/helloworld_c.c --config=$CONFIG "$@"

result=$(bin/helloworld_c)
((++counter))
if [ "$result" != "debug 1" ]; then
    echo test $counter: Incorrect variant: $result
    exit 1
fi

./cake --quiet tests/helloworld_c.c --variant=release --config=$CONFIG "$@"

result=$(bin/helloworld_c)
((++counter))
if [ "$result" != "release 1" ]; then
    echo test $counter: Incorrect variant: $result
    exit 1
fi

result=$(bin/helloworld_c extra args)
((++counter))
if [ "$result" != "release 3" ]; then
    echo test $counter: Incorrect args: $result
    exit 1
fi

#
# Test that c compilation picks up //#CFLAGS
#
./cake --quiet tests/test_cflags.c --config=$CONFIG "$@"
((++counter))
if [ $? != 0 ]; then
    echo test $counter: cake does not detect the //#CFLAGS in a c file
    exit 1
fi

#
# Test a slightly deeper chain of include files
#
rm -rf bin/*
./cake tests/test_direct_include.cpp --config=$CONFIG "$@"
result=$(bin/test_direct_include)
((++counter))
if [ "$result" != "2 1" ]; then
    echo test $counter: Incorrect result from test_direct_incude: $result
    exit 1
fi

#
# Test static library compilation
#
rm -rf bin/*
./cake --static-library tests/get_numbers.cpp --config=$CONFIG "$@"
./cake tests/test_library.cpp --config=$CONFIG "$@"
result=$(bin/test_library)
((++counter))
if [ "$result" != "1 2" ]; then
    echo test $counter: Incorrect result from static library test: $result
    exit 1
fi

#
# Test dynamic library compilation
#
rm -rf bin/*
./cake --dynamic-library tests/get_numbers.cpp --config=$CONFIG "$@"
LD_LIBRARY_PATH=bin
export LD_LIBRARY_PATH
./cake tests/test_library.cpp --config=$CONFIG "$@"
result=$(bin/test_library)
unset LD_LIBRARY_PATH
((++counter))
if [ "$result" != "1 2" ]; then
    echo test $counter: Incorrect result from dynamic library test: $result
    exit 1
fi

#
# Test the explict adding of extra source files via the //#SOURCE flag
#
rm -rf bin/* 
CAKE_PREPROCESS=True ./cake tests/test_source.cpp  --config=$CONFIG "$@"
result=$(bin/test_source)
((++counter))
if [ "$result" != "hello world from lin" ]; then
    echo test $counter: Incorrect result from the SOURCE test: $result
    exit 1
fi


#
# Test the interaction of PREPROCESS and //#SOURCE flag
# Expected result is that if PREPROCESS is true then the preprocessor 
# runs before the //# magic flags are looked for.
#
rm -rf bin/* 
result=$(CAKE_PREPROCESS=True ./cake --file-list --quiet tests/test_source.cpp  --config=$CONFIG "$@" | tr '\n' ' ')
((++counter))
if [ "$result" != "tests/test_source.cpp tests/cross_platform.cpp tests/cross_platform_lin.cpp tests/cross_platform.hpp " ]; then
    echo test $counter: Incorrect result from the SOURCE + PREPROCESS=True test: $result
    exit 1
fi

rm -rf bin/* 
result=$(CAKE_PREPROCESS=False ./cake --file-list --quiet tests/test_source.cpp  --config=$CONFIG "$@" | tr '\n' ' ')
((++counter))
if [ "$result" != "tests/test_source.cpp tests/cross_platform.cpp tests/cross_platform_lin.cpp tests/cross_platform_win.cpp tests/cross_platform.hpp " ]; then
    echo test $counter: Incorrect result from the SOURCE + PREPROCESS=False test: $result
    exit 1
fi
