================
ct-cache-clean
================

------------------------------------------------------------------------
Remove the current dependency cache 
------------------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2018-02-23
:Copyright: Copyright (C) 2011-2018 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-cache-clean [-h] [-v]


DESCRIPTION
===========
In most cases this is just a fancy ``rm -rf <cachedir>``.  It is possible for
different config files to specify different caches (yes this would be
pathological, but it is possible) so be careful to make sure
that you are removing the cache you think you are removing. ``ct-cache``
will answer that question for you.

Mostly you will never need this tool.  It's primarily for people how need to
do internal performance testing of parts of the compiletools infrastructure.

EXAMPLES
========

ct-cache-clean

ct-cache-clean -v

ct-cache-clean -vv

export CTCACHE=/dev/shm/ct; ct-cache-clean

SEE ALSO
========
``compiletools`` (1), ``ct-config`` (1), ``ct-cache`` (1)
