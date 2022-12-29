================
ct-gitroot
================

------------------------------------------------------------
What directory is the root of the git repository?
------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2017-09-28
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-gitroot

DESCRIPTION
===========
ct-gitroot is a command line tool to inspect what the other ct-* tools will
believe the root of the git repository to be.  The logic is simple:

* Try to execute ``git rev-parse --show-toplevel``
* If that fails traverse up the directory hierarchy looking for a ".git" 
  directory.  This is useful for when you need to fake it up for any reason.
* If that fails then use the current working directory as the "gitroot"

The reason the "gitroot" is important is that it is automatically added
to the include path for the compiler. This behaviour can be turned off by 
using the ``--no-git-root`` option.

EXAMPLES
========

ct-gitroot

SEE ALSO
========
``compiletools`` (1), ``ct-cake`` (1)
