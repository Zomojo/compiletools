============
ct-config
============

--------------------------------------------
Helper tool for examining ct-* configuration
--------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2016-08-16
:Copyright: Copyright (C) 2011-2016 Zomojo Pty Ltd
:Version: 4.1.92
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
Thus default locations are /etc/xdg/ct/ and $HOME/.config/ct/.  
Configuration parsing is done using python-configargparse which automatically 
handles environment variables, command line arguments, system configs
and user configs.  

Specifically, the config files are searched for in the following 
locations (from lowest to highest priority):
* same path as exe,
* system config (XDG compliant, so usually /etc/xdg/ct)
* python virtual environment system configs (${python-site-packages}/etc/xdg/ct)
* user config   (XDG compliant, so usually ~/.config/ct)
* gitroot
* current working directory

The ct-* applications are aware of two levels of configs.  
There is a base level ct.conf that contains the basic variables that apply no 
matter what variant (i.e, debug/release/etc) is being built. The default 
ct.conf defines the following variables: ::

    CTCACHE = None
    variant = debug
    variantaliases = {'debug':'gcc.debug', 'release':'gcc.release'}
    exemarkers = [main(,main (,wxIMPLEMENT_APP,g_main_loop_new]
    testmarkers = unit_test.hpp

The second layer of config files are the variant configs that contain the 
details for the debug/release/etc.  The variant names are simply a config file 
name but without the .conf. There are also variant aliases to make for less 
typing. So --variant=debug looks up the variant alias (specified in ct.conf) 
and notices that "debug" really means "gcc.debug".  So the config file that 
gets opened is "gcc.debug.conf".  The default gcc.debug.conf defines the 
following variables: ::

    ID=GNU
    CC=gcc
    CXX=g++
    LD=g++
    CFLAGS=-fPIC -g -Wall
    CXXFLAGS=-std=c++11 -fPIC -g -Wall
    LDFLAGS=-fPIC -Wall -Werror -Xlinker --build-id

If any config value is specified in more than one way then the following 
hierarchy is used

* command line > environment variables > config file values > defaults

ct-config can be used to create a new config and write the config to file 
simply by using the ``-w`` flag.

OPTIONS
=======

--verbose, -v  Output verbosity. Add more v's to make it more verbose (default: 0)
--version      Show program's version number and exit
--help, -h     Show help and exit
--variant VARIANT  Specifies which variant of the config should be used. Use the config name without the .conf (default: gcc.debug)
--write-out-config-file OUTPUT_PATH, -w OUTPUT_PATH  takes the current command line args and writes them out to a config file at the given path, then exits (default: None)

``compilation args``
    Any of the standard compilation arguments you want to go into the config.

EXAMPLE
=======

Say that you are cross compiling to a beaglebone. First off you might discover that the following line worked but was rather tedious to type

* ct-cake main.cpp --CXX=arm-linux-gnueabihf-g++ --CPP=arm-linux-gnueabihf-g++  --CC=arm-linux-gnueabihf-g++ --LD=arm-linux-gnueabihf-g++

What you would really prefer to type is 

* ct-cake main.cpp --variant=bb.debug
* ct-cake main.cpp --variant=bb.release

Which leads you to the question, how do you write the new variant? A variant is just a config file (with extension .conf) so you could simply copy an existing variant config and edit with a text editor. Alternatively, there is an app for that.  The -w option on the ct-config command will write a new config file.

* ct-config --CXX=arm-linux-gnueabihf-g++ --CPP=arm-linux-gnueabihf-g++  --CC=arm-linux-gnueabihf-g++ --LD=arm-linux-gnueabihf-g++ -w ~/.config/ct/bb.debug.conf

Once that has written you should now use your favourite editor to edit ~/.config/ct/bb.debug.conf.  You will probably need to edit the various FLAGS variables.  Most of the other variables can be removed as they will default to the values shown in the file anyway.

Now if almost all you ever do is cross compile to the beaglebone then you might prefer that the "debug" meant "bb.debug" and similarly for release. That is, you really might prefer to type

* ct-cake main.cpp --variant=release   # meaning bb.release
* ct-cake main.cpp                     # meaning bb.debug

To achieve that you have to edit the ct.conf file in ~/.config/ct/ct.conf (or /etc/xdg/ct/ct.conf if you are doing a systemwide setup) to include the following lines

variant = debug
variantaliases = {'debug':'bb.debug', 'release':'bb.release'}

SEE ALSO
========
``compiletools`` (1), ``ct-list-variants`` (1)
