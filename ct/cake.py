from __future__ import print_function
from __future__ import unicode_literals

import sys
import configargparse
import subprocess
import os
import shutil
import ct.utils
import ct.makefile
import ct.filelist

class Cake:
    def __init__(self, args):
        self.args = args

    @staticmethod
    def _add_prepend_append_argument(cap, name, destname=None, extrahelp=None):
        """ Add a prepend flags argument and an append flags argument to the config arg parser """
        if destname is None:
            destname = name

        if extrahelp is None:
            extrahelp = ""

        cap.add(
            "".join(["--","prepend","-", name.upper()]),
            dest="".join(["prepend", destname.lower()]),
            help=" ".join(["prepend".title(), "the given text to the", name.upper(), "already set. Useful for adding search paths etc.", extrahelp]))
        cap.add(
            "".join(["--","append","-", name.upper()]),
            dest="".join(["append", destname.lower()]),
            help=" ".join(["append".title(), "the given text to the", name.upper(), "already set. Useful for adding search paths etc.", extrahelp]))

    @staticmethod
    def add_arguments(cap, variant, argv):
        ct.makefile.MakefileCreator.add_arguments(cap)

        Cake._add_prepend_append_argument(cap, 'cppflags')
        Cake._add_prepend_append_argument(cap, 'cflags')
        Cake._add_prepend_append_argument(cap, 'cxxflags')
        Cake._add_prepend_append_argument(cap, 'ldflags')
        Cake._add_prepend_append_argument(cap, 'linkflags', destname='ldflags', extrahelp='Synonym for setting LDFLAGS.')

        ct.utils.add_boolean_argument(
            parser=cap,
            name="file-list",
            dest='filelist',
                default=False,
                help="Print list of referenced files.")        
        cap.add(
            "--begintests",
            dest='tests',
            nargs='*',
            help="Starts a test block. The cpp files following this declaration will generate executables which are then run. Synonym for --tests")

    def _callfilelist(self):
        # The extra arguments were deliberately left off before due to conflicts.  
        # Add them on now.
        cap = configargparse.getArgumentParser()
        ct.filelist.Filelist.add_arguments(cap)
        args = ct.utils.parseargs(cap)
        filelist = ct.filelist.Filelist(args)
        filelist.process()

    def _callmakefile(self):
        makefile_creator = ct.makefile.MakefileCreator(self.args)
        makefilename = makefile_creator.create()
        cmd = ['make', '-f', makefilename]
        subprocess.check_call(cmd, universal_newlines=True)
        
        # Copy the executables into the bindir (as per cake)
        namer = ct.utils.Namer(self.args)
        filelist = os.listdir(namer.executable_dir())
        for ff in filelist:
            filename = os.path.join(namer.executable_dir(),ff)
            if ct.utils.isexecutable(filename):
                shutil.copy2(filename, 'bin/')

    def process(self):
        """ Transform the arguments into suitable versions for ct-* tools 
            and call the appropriate tool.
        """
        if self.args.prependcppflags:
            self.args.CPPFLAGS = " ".join([self.args.prependcppflags, self.args.CPPFLAGS])
        if self.args.prependcflags:
            self.args.CFLAGS = " ".join([self.args.prependcflags, self.args.CFLAGS])
        if self.args.prependcxxflags:
            self.args.CXXFLAGS = " ".join([self.args.prependcxxflags, self.args.CXXFLAGS])
        if self.args.prependldflags:
            self.args.LDFLAGS = " ".join([self.args.prependldflags, self.args.LDFLAGS])
        if self.args.appendcppflags:
            self.args.CPPFLAGS += " " + self.args.appendcppflags
        if self.args.appendcflags:
            self.args.CFLAGS += " " + self.args.appendcflags
        if self.args.appendcxxflags:
            self.args.CXXFLAGS += " " + self.args.appendcxxflags
        if self.args.appendldflags:
            self.args.LDFLAGS += " " + self.args.appendldflags

        if self.args.filelist:
            self._callfilelist()
        else:
            self._callmakefile()

def main(argv=None):
    if argv is None:
        argv = sys.argv

    variant = ct.utils.extract_variant_from_argv(argv)
    cap = configargparse.getArgumentParser()
    Cake.add_arguments(cap, variant, argv)
    args = ct.utils.parseargs(cap, argv)
    cake = Cake(args)
    cake.process()

    return 0
