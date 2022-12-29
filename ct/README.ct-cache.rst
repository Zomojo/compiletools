================
ct-cache
================

------------------------------------------------------------------------
Where is the dependency information used by the ct-* applications stored 
------------------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2018-02-21
:Copyright: Copyright (C) 2011-2018 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-cache [-h] [--CTCACHE CTCACHE] [-v]


DESCRIPTION
===========
The various ct-* applications need to determine the dependency graph of each 
source file. It is possible to get a minor speed improvement by caching this
dependency tree. By default caching of dependencies is turned off and 
ct-cache will return "None".

ct-cache uses the command line arguments and environment variables to 
determine which dependency cache will be used to store the dependency graph 
of a given file.

If you need to set the location of the cache, set the variable ``CTCACHE``
in one of the config files. For example, the default /etc/xdg/ct/ct.conf uses
``CTCACHE=None``.
Another common usecase is
``CTCACHE=/dev/shm/ct``.

Increasing the verbosity levels gives more information about how the ct-*
applications do their search to determine what the cache location should be.
See the ``ct-config`` manpage for more information about configuration file
locations.

The default cache is set to None due to python recursion limits that will cause 
failure on large projects.  Having said that, the author uses 
``CTCACHE=/dev/shm/ct`` on all their projects.  Naturally the cache can be 
specified to be on disk too. The cache can be cleared using ``ct-cache-clean``.

EXAMPLES
========

ct-cache

ct-cache -v

ct-cache -vv

export CTCACHE=/dev/shm/ct; ct-cache

SEE ALSO
========
``compiletools`` (1), ``ct-config`` (1), ``ct-cache-clean`` (1)
