================
ct-cppdeps
================

------------------------------------------------------------
What 
------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2022-06-05
:Copyright: Copyright (C) Geoffery Ericksson
:Version: 4.1.85
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-cppdeps [-h] [-c CONFIG_FILE] [--variant VARIANT] [-v] [-q] 
[--version] [-?] [--man] 
[--CTCACHE CTCACHE] [--ID ID] 
[--CPP CPP] [--CC CC] [--CXX CXX] 
[--CPPFLAGS CPPFLAGS] [--CXXFLAGS CXXFLAGS] 
[--CFLAGS CFLAGS] 
[--git-root | --no-git-root] 
[--include INCLUDE] [--pkg-config PKG_CONFIG] 
[--shorten | --no-shorten] 
[--headerdeps {direct,cpp}]
filename [filename ...]

DESCRIPTION
===========
ct-cppdeps generates the header dependencies for the file you specify at the 
command line.  There are two possible methodologys:  

* "--headerdeps=direct" uses a regex to find the "#include" lines in the source
  code. This methodology is fast. However, while the regex correctly ignores 
  commented out includes, it incorrectly identifies files that are surrounded 
  by #ifdef 0 guards.

* "--headerdeps=cpp" executes "$CPP -MM -MF" which is slower but guarantees correctness.  


For each header file found in the source file, it looks for
an underlying implementation (c,cpp,cc,cxx,etc) file with the same name, and 
adds that implementation file to the build.  
ct-cppdeps also reads the first 8KB of each file for special comments
that indicate needed link and compile flags.  Then it recurses through the
dependencies of the cpp file, and uses this spidering to generate complete
dependency information for the application. 

EXAMPLES
========

ct-cppdeps somefile1.cpp somefile2.cpp

ct-cppdeps --variant=release somefile.cpp


SEE ALSO
========
``compiletools`` (1), ``ct-findtargets`` (1), ``ct-headertree`` (1), ``ct-config`` (1), ``ct-cake`` (1)


