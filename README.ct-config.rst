============
ct-config
============

--------------------------------------------
Helper tool for examining ct-* configuration
--------------------------------------------

:Author: geoff@zomojo.com
:Date:   2016-08-16
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.31
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-config [compilation args] [--variant=<VARIANT>] [-w output.conf]

DESCRIPTION
===========
ct-config is a helper tool for examining how config files, command line 
arguments and environment variables are combined to make the internal 
variables that the ct-* applications use to do their job.

Config files for the ct-* applications are programmatically located using 
python-appdirs, which on linux is a wrapper around the XDG specification. 
Thus default locations are /etc/xdb/ct/ and $HOME/.config/ct/.  
Configuration parsing is done using python-configargparse which automatically 
handles environment variables, command line arguments, system configs
and user configs.  The ct-* applications are aware of two levels of configs.  
There is a base level ct.conf that contains the basic variables that apply no 
matter what variant (i.e, debug/release/etc) is being built. 

The second layer of config files are the variant configs that contain the 
details for the debug/release/etc.  The variant names are simply a config file 
name but without the .conf. There are also variant aliases to make for less 
typing. So --variant=debug looks up the variant alias (specified in ct.conf) 
and notices that "debug" really means "gcc.debug".  So the config file that 
gets opened is "gcc.debug.conf".  If any config value is specified in more 
than one way then the following hierarchy is used

* command line > environment variables > config file values > defaults

Write the config to file with -w.

OPTIONS
=======

--verbose, -v  Output verbosity. Add more v's to make it more verbose (default: 0)
--version      Show program's version number and exit
--help, -h     Show help and exit
--variant VARIANT  Specifies which variant of the config should be used. Use the config name without the .conf (default: gcc.debug)
--write-out-config-file CONFIG_OUTPUT_PATH, -w CONFIG_OUTPUT_PATH    takes the current command line args and writes them out to a config file at the given path, then exits (default: None)

``compilation args``
    Any of the standard compilation arguments you want to go into the config.


SEE ALSO
========
``compiletools`` (1), ``ct-list-variants`` (1)
