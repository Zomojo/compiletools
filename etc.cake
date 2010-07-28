CAKE_CC = ccache g++ -I . -I deps/3rdparty/lwip -I ./deps/3rdparty/lwip/lwip/src/include/ -I ./deps/3rdparty/lwip/lwip/src/include/ipv4/

CAKE_CXXFLAGS=-fPIC -g
CAKE_LINKFLAGS=-fPIC

CAKE_DEBUG_CC = $CAKE_CC
CAKE_DEBUG_CXXFLAGS=$CAKE_CXXFLAGS -Wall
CAKE_DEBUG_LINKFLAGS=$CAKE_LINKFLAGS -Wall

CAKE_RELEASE_CC = $CAKE_CC
CAKE_RELEASE_CXXFLAGS=-fPIC -O3 -DNDEBUG -Wall -finline-functions -Wno-inline
CAKE_RELEASE_LINKFLAGS=-O3 -Wall

CAKE_PROFILE_CC = $CAKE_CC
CAKE_PROFILE_CXXFLAGS=$CAKE_RELEASE_CXXFLAGS -pg -g
CAKE_PROFILE_LINKFLAGS=-O3 -Wall -pg -g

CAKE_COVERAGE_CC = g++
CAKE_COVERAGE_CXXFLAGS=-fPIC -O0 -fno-inline -Wall -g -fprofile-arcs -ftest-coverage
CAKE_COVERAGE_LINKFLAGS=-fPIC -O0 -fno-inline -Wall -g -fprofile-arcs -ftest-coverage
