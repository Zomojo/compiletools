================
ct-findtargets
================

------------------------------------------------------------
What 
------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2018-04-17
:Copyright: Copyright (C) 2011-2018 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-findtargets [-h] [-c CONFIG_FILE] [--variant VARIANT] [-v] [-q]
                    [--version] [-?] [--CTCACHE CTCACHE] [--ID ID]
                    [--CPP CPP] [--CC CC] [--CXX CXX] [--CPPFLAGS CPPFLAGS]
                    [--CXXFLAGS CXXFLAGS] [--CFLAGS CFLAGS]
                    [--git-root | --no-git-root]
                    [--include [INCLUDE [INCLUDE ...]]]
                    [--shorten | --no-shorten] [--bindir BINDIR]
                    [--objdir OBJDIR] [--exemarkers EXEMARKERS]
                    [--testmarkers TESTMARKERS] [--auto | --no-auto]
                    [--style {indent,null,args,flat}]
                    [--filenametestmatch | --no-filenametestmatch]


DESCRIPTION
===========
ct-findtargets uses the variables exemarkers and testmarkers (usually 
defined in ct.conf) to find the source files that will 
compile to either an executable or a unit test.  The default settings are

* exemarkers = [main(,main (,wxIMPLEMENT_APP,g_main_loop_new]
* testmarkers = unit_test.hpp

A filename that starts with "test" and also satisfies the exemarkers will 
be reported as a test, unless --no-filenametestmatch is set.

EXAMPLES
========

ct-findtargets

ct-findtargets --variant=release


SEE ALSO
========
``compiletools`` (1), ``ct-config`` (1)
