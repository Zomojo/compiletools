============
ct-cake
============

---------------------------------------------
Swiss army knife for building a C/C++ project
---------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2018-02-06
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-cake [compilation args] [--variant=<VARIANT>] filename.cpp

DESCRIPTION
===========
ct-cake is the Swiss army knife of build tools that combines many of the
compiletools into one uber-tool. For many C/C++ projects you can compile
simply using

    ``ct-cake --auto``

ct-cake will try to determine the correct source files to generate executables
from and also determine the tests to build and run. It works by spidering over
the source code to determine what implementation files to build, what libraries 
to link against and what compiler flags to set. Only build what you
need, and throw out your Makefiles.

The --auto flag tells ct-cake to search for files that will be the "main" file.  
From that set of files, ct-cake then uses the header includes to
determine what implementation (cpp) files are also required to be built and 
linked into the final executable/s.

Cake works off the same principles as Ruby on Rails. It will make your life
easy if you don't arbitrarily name things. The main rules are:

   * ct-cake only builds C and C++. Everything can be done just fine with 
     other tools, so there's no point reinventing them. Anyway, it's easy to 
     embed cake into other toolchains, see the last section.
   * All binaries end up in the bin directory, with the same base name as 
     their source filename. You can override this at the command-line, but it's 
     against the spirit of the tool.
   * The implementation file for point.hpp should be called point.cpp. This 
     is so ct-cake can compile it and recursively hunt down its dependencies.
   * If a header or implementation file will not work without being linked 
     with a certain flag, add a //#LDFLAGS=myflag directly to the source code.
   * Likewise, if a special compiler option is needed, use //#CXXFLAGS=myflag.
   * Minimise the use of "-I" include flags. They make it hard not only for 
     cake to generate dependencies, but also autocomplete tools like Eclipse  
     and ctags. You can avoid -I flags by structuring your code in the same way 
     you refer to paths in your source code. 
   * Currently only varieties of Linux are actively supported because that's 
     what the compiletools developers have easy access to. That said, it stands 
     a good chance of working on \*BSD and macOS. We are interested in receiving 
     patches for other platforms including Windows.
   
ct-cake works off a "pull" philosophy of building, unlike the "push" model
of most build processes. Often, there is the monolithic build script that
rebuilds everything. Users iterate over changing a file, relinking everything
and then rerunning their binary. A hierarchy of libraries is built up and
then linked in to the final executables. All of this takes a lot of time,
particularly for C++.

With ct-cake, you only pull in what is strictly necessary to what you need to 
run right now. Say, you are testing a particular tool in a large project, with
a large base of 2000 library files for string handling, sockets, etc. There
is simply no Makefile (This is actually a lie, there is a Makefile under the 
hood). You might want to create a build.sh for regression
testing, but it's not essential.

The basic workflow is to simply type:

    ``ct-cake --auto``

If there are multiple executables that --auto finds and you only want to build 
one specific one:

    ``ct-cake path/to/src/app.cpp``

Only the library cpp files that are needed, directly, or indirectly to create
./bin/app are actually compiled. If you don't #include anything that refers
to a library file, you don't pay for it. Also, only the link options that
are strictly needed to generate the app are included. Its possible to do in
make files, but such fine-level granularity is rarely set up in practice,
because its too error-prone to do manually, or with recursive make goodness.


How it Works
============

ct-cake generates the header dependencies for the "main.cpp"
file you specify at the command line by either examining the "#include" lines in 
the source code (or by executing "gcc -MM -MF" if you use the --preprocess flag).  
For each header file found in the source file, it looks for
an underlying implementation (c,cpp,cc,cxx,etc) file with the same name, and 
adds that implementation file to the build.  ct-cake also reads the first 8KB
of each file for special comments
that indicate needed link and compile flags.  Then it recurses through the
dependencies of the cpp file, and uses this spidering to generate complete
dependency information for the application. A Makefile is generated and finally 
it calls make.

Magic Comments / Magic Flags
============================

ct-cake works very differently to other build systems, which specify a hierarchy
of link flags and compile options, because ct-cake ties the compiler flags
directly to the source code. If you have compress.hpp that requires "-lzip"
on the link line, add the following comment in the first 8KB of the header file:

``//#LDFLAGS=-lzip``

Whenever the header is included (either directly or indirectly), the -lzip
will be automatically added to the link step. If you stop using the header,
for a particular executable, cake will figure that out and not link against it.

If you want to compile a cpp file with a particular optimization enabled,
add, say:

``//#CXXFLAGS=-fstrict-aliasing``

Because the code and build flags are defined so close to each other, its
much easier to tweak the compilation locally.

Performance
===========

Because ct-cake internally generates a makefile to build the C++ file, cake is
about as fast as a handrolled Makefile that uses the same lazily generated
dependencies. One particular example project took 0.04 seconds to build if 
nothing is out of date, versus 2 seconds for, say, Boost.Build.

ct-cake also eliminates the redundant generation of static archive files that
a more hierarchical build process would generate as intermediaries, saving
the cost of running 'ar'.

Note that ct-cake doesn't build all cpp files that you have checked out, only 
those
strictly needed to build your particular binary, so you only pay for what
you use. This difference alone should see a large improvement on most
projects, especially for incremental rebuilds.

Selective build and test
========================

You can instruct ct-cake to only build binaries dependant on a list of
source files using the ``--build-only-changed`` flag. This is helpful for
limiting building and testing in a Continuous Integration pipeline to only
source that has changed from master.

``changed_source=git diff --name-only master | sed "s,^,$(git rev-parse --show-toplevel)/,"
ct-cake --auto --build-only-changed \"$changed_source\"``

Configuration
=============

The compiletools programs require *almost* no configuration. However, it is 
still
useful to have some shortcut build templates such as 'release',
'profile' etc.

Config files for the ct-* applications are programmatically located using 
python-appdirs, which on linux is a wrapper around the XDG specification.  Thus 
default locations are /etc/xdb/ct/ and $HOME/.config/ct/.  Configuration parsing 
is done using python-configargparse which automatically handles environment 
variables, command line arguments, system configs
and user configs.  

Specifically, the config files are searched for in the following locations (from 
lowest to highest priority):

    * same path as exe,
    * system config (XDG compliant, so usually /etc/xdg/ct)
    * python virtual environment system configs 
      (${python-site-packages}/etc/xdg/ct)
    * user config   (XDG compliant, so usually ~/.config/ct)

The ct-* applications are aware of two levels of configs.  There is a base level 
ct.conf that contains the basic variables that apply no  matter what variant 
(i.e, debug/release/etc) is being built. 

The second layer of config files are the variant configs that contain the 
details for the debug/release/etc.  The variant names are simply a config file 
name but without the .conf. There are also variant aliases to make for less 
typing. So --variant=debug looks up the variant alias (specified in ct.conf) and 
notices that "debug" really means "gcc.debug".  So the config file that gets 
opened is "gcc.debug.conf".  If any config value is specified in more than one 
way then the following hierarchy is used

* command line > environment variables > config file values > defaults 

The example /etc/xdg/ct/gcc.release.conf file looks as follows: ::

    ID=GNU
    CC=gcc
    CXX=g++
    LD=g++
    CFLAGS=-fPIC -g -Wall -O3 -DNDEBUG -finline-functions -Wno-inline
    CXXFLAGS=-std=c++11 -fPIC -g -Wall -O3 -DNDEBUG -finline-functions -Wno-inline
    LDFLAGS=-fPIC -Wall -Werror -Xlinker --build-id
    TESTPREFIX=timeout 300 valgrind --quiet --error-exitcode=1

CXXFLAGS lists the flags appended to each compilation job. The value in 
/etc/xdg/ct/\*.conf
is overridden by the environment variable, which is in return overridden by
the command-line argument --CXXFLAGS=. Likewise, LDFLAGS sets the default 
options used for linking.

TESTPREFIX specifies a command prefix to place in front of unit test runs. This 
should ideally be a tool like valgrind, gdb or purify that can be configured 
to execute the app and return a non-zero exit code on any failure.


Build variants
==============
A variant is a configuration file that specifies various configurable settings 
like the compiler and compiler flags. Common variants are "debug" and "release".  
Build variants are used by specifying the variant name at the command-line as 
follows: 

    ``$ ct-cake --variant=release a.cpp``

Unit Tests
==========

ct-cake integrates with unit tests in a fairly simple (and perhaps simplistic) 
way.

ct-cake allows you to specify multiple build targets on each line,
so the following is valid and useful:

    ``$ ct-cake utilities/*.cpp    # builds all apps and places them under bin/``

Unit tests are executables that are generated, that create an additional
build step. They must run and return an exit code of 0 as part of the build
process. To specify that executables are unit tests, use the --tests flag.

    ``$ ct-cake utilities/*.cpp --tests tests/*.cpp``

If the *TESTPREFIX* variable is set, you can automatically check
all unit tests with a code purifying tool. For example:

    ``export TESTPREFIX="valgrind --quiet --error-exitcode=1"``

will cause all unit tests to only pass if they run through valgrind with no
memory errors.

Putting it all together - a typical build setup
===============================================

For most simple projects, a build.sh script that looks like the
following is quite useful. You can simply add more cpp to the apps directory to 
generate more tools from the project,
or add test scripts to the regression directory to improve
test coverage.

Code generation steps can be added at the beginning of
the build.sh, before cake runs. ::

    #!/bin/sh
    set -e
    python fancypythoncodegenerator.py
    ct-cake --auto "$@"


The special *"$@"* marker is the recommended way
of forwarding arguments to an application. You can then
run the build script like this:

    ``$ ./build.sh --variant=release``

or:

    ``$ ./build.sh --variant=release --append-CXXFLAGS=-DSPECIALMODE``

SEE ALSO
========
``compiletools`` (1), ``ct-list-variants`` (1), ``ct-config`` (1)
