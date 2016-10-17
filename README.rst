============
compiletools
============

--------------------------------------------------------
C/C++ build tools that requires almost no configuration.
--------------------------------------------------------

:Author: geoff@zomojo.com
:Date:   2016-08-09
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.31
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
    ct-* [compilation args] [filename.cpp] [--variant=<VARIANT>]

DESCRIPTION
===========
The various ct-* tools exist to build C/C++ executables with almost no 
configuration. For example, to build a C or C++ program, type

    ct-cake --auto

which will try to determine the correct source files to generate executables
from and also determine the tests to build and run.

A variant is a configuration file that specifies various configurable settings
like the compiler and compiler flags. Common variants are "debug" and "release".

Options are parsed using python-configargparse.  This means they can be passed
in on the command line, as environment variables or in config files.
Command-line values override environment variables which override config file 
values which override defaults. Note that the environment variables are 
captilized. That is, a command line option of --magic=cpp is the equivalent of 
an environment variable MAGIC=cpp.

Other notable tools are 

* ct-headertree: provides information about structure of the include files
* ct-filelist:   provides the list of files needed to be included in a tarball (e.g. for packaging)

SEE ALSO
========
* ct-build
* ct-build-dynamic-library
* ct-build-static-library
* ct-cache
* ct-cache-clean
* ct-cake
* ct-cmakelists
* ct-config
* ct-cppdeps
* ct-create-cmakelists
* ct-create-makefile
* ct-filelist
* ct-findtargets
* ct-gitroot
* ct-headertree
* ct-jobs
* ct-list-variants
* ct-magicflags
