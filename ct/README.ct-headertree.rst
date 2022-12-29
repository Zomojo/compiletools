=============
ct-headertree
=============

---------------------------------------------------------------------
Create a tree of header dependencies starting at the given C/C++ file
---------------------------------------------------------------------

:Author: drgeoffathome@gmail.com
:Date:   2018-07-26
:Copyright: Copyright (C) 2011-2018 Zomojo Pty Ltd
:Version: 4.1.92
:Manual section: 1
:Manual group: developers

SYNOPSIS
========
ct-headertree [OPTION] filename [filename ...]

DESCRIPTION
===========
Create a tree of header dependencies starting at a given C/C++ file.

OPTIONS
=======
  --style {tree,depth,dot,flat}
                        Output formatting style [env var: STYLE] (default:
                        tree)

  --variant VARIANT     Specifies which variant of the config should be used.
                        Use the config name without the .conf [env var:
                        VARIANT] (default: ml.debug)

  --git-root            Determine the git root then add it to the include
                        paths. Use --no-git-root to turn the feature off. [env
                        var: GIT_ROOT] (default: True)

  --no-git-root         [env var: NO_GIT_ROOT] (default: False)

  --include [INCLUDE [INCLUDE ...]]
                        Extra path(s) to add to the list of include paths [env
                        var: INCLUDE] (default: [])

  --shorten             Strip the git root from the filenames Use --no-shorten
                        to turn the feature off. [env var: SHORTEN] (default:
                        False)

  --no-shorten          [env var: NO_SHORTEN] (default: True)

  --headerdeps {direct,cpp}
                        Methodology for determining header dependencies [env
                        var: HEADERDEPS] (default: direct)

EXAMPLES
========

ct-headertree myfile.cpp

ct-headertree --style=dot myheader.hpp


SEE ALSO
========
``compiletools`` (1), ``ct-commandline`` (1), ``ct-config`` (1)
