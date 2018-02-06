============
ct-cake
============

---------------------------------------------
Swiss army knife for building a C/C++ project
---------------------------------------------

:Author: geoff@zomojo.com
:Date:   2018-02-06
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.49
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
the source code to determine what implementation files to build, what 
libraries to link against and what compiler flags to set. Only build what you
need, and throw out your Makefiles.

SEE ALSO
========
``compiletools`` (1), ``ct-list-variants`` (1), ``ct-config`` (1)
