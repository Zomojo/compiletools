================
ct-magicflags
================

------------------------------------------------------------------------
Show the magic flags / magic comments that a file exports
------------------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2018-02-23
:Copyright: Copyright (C) 2011-2018 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-magicflags [-h] [-c CONFIG_FILE] [--headerdeps {direct,cpp}]
                   [--variant VARIANT] [-v] [-q] [--version] [-?]
                   [--CTCACHE CTCACHE] [--ID ID] [--CPP CPP] [--CC CC]
                   [--CXX CXX] [--CPPFLAGS CPPFLAGS] [--CXXFLAGS CXXFLAGS]
                   [--CFLAGS CFLAGS] [--git-root | --no-git-root]
                   [--include [INCLUDE [INCLUDE ...]]]
                   [--shorten | --no-shorten] [--magic {cpp,direct}]
                   [--style {null,pretty}]
                   filename [filename ...]

DESCRIPTION
===========
ct-magicflags extracts the magic flags/magic comments from a given file.
It is mostly used for debugging purposes so that you can see what the 
other compiletools will be using as the magic flags.  A magic flag /
magic comment is simply a C++ style comment that provides information
required to complete the build process.

compiletools works very differently to other build systems, because 
compiletools expects that the compiler/link flags will be directly in the 
source code. For example, if you have written your own "compress.hpp" that 
requires linking against libzip you would normally specify "-lzip" in your 
Makefile (or build system) on the link line.  However, compiletools based 
applications add the following comment 
in the first 8KB of the file the includes: ::

    //#LDFLAGS=-lzip

For easy maintainence, it is convenient to put the magic flag directly after 
the include: ::

    #include <zip.h>
    //#LDFLAGS=-lzip

Whenever "compress.hpp" is included (either directly or indirectly), the 
"-lzip" will be automatically added to the link step. If you stop using the 
header, for a particular executable, compiletools will figure that out and 
stop linking against libzip.

If you want to compile a cpp file with a particular optimization enabled you
would add something like: ::

    //#CXXFLAGS=-fstrict-aliasing 

Because the code and build flags are defined so close to each other, it is
much easier to tweak the compilation locally and allow for easier maintainence.

VALID MAGIC FLAGS
=================
A magic flag follows the pattern ``//#key=value``. Whitespace around the 
equal sign is acceptable.

The known magic flags are::

    =========   ==============================================================
    Key         Description
    =========   ==============================================================
    CPPFLAGS    C Pre Processor flags
    CFLAGS      C compiler flags
    CXXFLAGS    C++ flags (do not confuse these with the C PreProcessor flags)
    INCLUDE     Specify include paths without "-I". 
                Adds the path to CPPFLAGS, CFLAGS and CXXFLAGS.
    LDFLAGS     Linker flags
    LINKFLAGS   Linker flags (deprecated)
    SOURCE      Inject an extra souce file into the list of files to be built. 
                This is most commonly used in cross platform work.
    PKG-CONFIG  Extract the cflags and libs using pkg-config
    ==========  ==============================================================

EXAMPLES
========

* ct-magicflags main.cpp 
* ct-magicflags --variant=release main.cpp 

SEE ALSO
========
``compiletools`` (1), ``ct-cake`` (1)
