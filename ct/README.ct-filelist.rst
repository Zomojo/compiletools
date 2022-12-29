================
ct-filelist
================

-------------------------------------------------------------------------------------------------------
Determine header and source dependencies of a C/C++ file by following headers and implied source files.
-------------------------------------------------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2017-07-06
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-filelist [OPTION] filename [filename ...]

DESCRIPTION
===========
ct-filelist uses the given variants/configs, command line arguments, 
environment variables, and most importantly one or more filenames to determine 
the list of files that are required to build the given filename(s). For example, 
if myfile.cpp includes myfile.hpp and myfile.hpp in turn includes awesome.h

::

  myfile.cpp
  |_ myfile.hpp
     |_ awesome.h

then "ct-filelist myfile.cpp" will return

::

  awesome.h
  myfile.cpp
  myfile.hpp

The command line arguments --extrafile, --extradir, --extrafilelist are used
to add extra files to the output.  This can be useful when you are using the
output to build up a set of files to include in a tarball.

OPTIONS
=======

--extrafile [EXTRAFILE [EXTRAFILE ...]]
                    Extra files to directly add to the filelist 
                    [env var: EXTRAFILE] (default: None)
--extradir [EXTRADIR [EXTRADIR ...]]
                    Extra directories to add all files from to the filelist 
                    [env var: EXTRADIR] (default: None)
--extrafilelist [EXTRAFILELIST [EXTRAFILELIST ...]]
                    Read the given files to find a list of extra files to add to the filelist 
                    [env var: EXTRAFILELIST] (default: None)
--shorten []      
                    Strip the git root from the filenames.
                    Use "--no-shorten" to turn the feature off. 
                    [env var: SHORTEN] (default: False)
--no-shorten []          
                    [env var: NO_SHORTEN] (default: True)
--merge []
                    Merge all outputs into a single list Use "--no-merge" to 
                    turn the feature off. 
                    [env var: MERGE] (default: True)
--no-merge []
                    [env var: NO_MERGE] (default: False)


EXAMPLES
========

ct-filelist myfile.cpp

ct-filelist --extradir ../icons myfile.cpp


SEE ALSO
========
``compiletools`` (1), ``ct-commandline`` (1), ``ct-config`` (1)
