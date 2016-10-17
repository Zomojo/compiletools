================
ct-list-variants
================

------------------------------------------------------------
Locates available variants for use by the ct-* applications
------------------------------------------------------------

:Author: geoff@zomojo.com
:Date:   2016-08-16
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.31
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
    ct-list-variants

DESCRIPTION
===========

A variant is a configuration file that specifies various configurable settings
like the compiler and compiler flags. Common variants are "debug" and "release".
Other ct-* applications use a --variant=<debug/release/clang.debug/etc>
option to specify the parameters to be used for the build.  ct-list-variants
is the tool you use to discover what variants are available on your system.

It should be noted that a variant is simply a config file without the .conf.
Config files for the ct-* applications are programmatically located using 
python-appdirs, which on linux is a wrapper around the XDG specification. 
The default locations are /etc/xdb/ct/ and $HOME/.config/ct/.  
Configuration is down done using python-configargparse which automatically 
handles environment variables, command line arguments, system configs, 
and user configs.  Also there are two levels of configs.  There is a ct.conf 
that contains the basic variables that apply no matter what variant 
(i.e, debug/release/etc) is being built.  Then there are variant configs that 
contain the details for the debug/release/etc.

ct.conf can specify a variant aliases map so as to reduce the amount of typing
you need to do for a --variant=some.long.variant.name. As an example,
--variant=debug is actually a variant alias for "gcc.debug".  So the config 
file that gets opened is "gcc.debug.conf".  

If any config value is specified in more than one way then

* command line > environment variables > config file values > defaults



SEE ALSO
========
``compiletools`` (1), ``ct-config`` (1)
