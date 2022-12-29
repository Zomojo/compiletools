================
ct-jobs
================

------------------------------------------------------------
How many jobs to run concurrently by the ct-* applications.  
------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2017-04-28
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-jobs [--variant=<VARIANT>] [--config=<CONFIG>] [--jobs=<num>]

DESCRIPTION
===========
ct-jobs uses the given variants/configs, command line arguments
and environment variables to determine how many jobs the user 
wants to run concurrently. The default is to use the number
of cores available (which can be restricted using taskset on linux).

EXAMPLES
========

ct-jobs

ct-jobs --variant=release

taskset -c 1-3 ct-jobs

SEE ALSO
========
``compiletools`` (1), ``ct-config`` (1)
