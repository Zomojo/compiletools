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
    def add_arguments(cap, variant, argv):
        cap.add(
            "--prepend-CPPFLAGS",
            dest='prependcppflags',
            help="Prepends the given text to the CPPFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--prepend-CFLAGS",
            dest='prependcflags',
            help="Prepends the given text to the CFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--prepend-CXXFLAGS",
            dest='prependcxxflags',
            help="Prepends the given text to the CXXFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--prepend-LDFLAGS",
            dest='prependldflags',
            help="Prepends the given text to the LDFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--prepend-LINKFLAGS",
            dest='prependldflags',
            help="Prepends the given text to the LDFLAGS already set. Synonym for prepend-LDFLAGS. Useful for adding search paths etc. ")
        cap.add(
            "--append-CPPFLAGS",
            dest='appendcppflags',
            help="Appends the given text to the CPPFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--append-CFLAGS",
            dest='appendcflags',
            help="Appends the given text to the CFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--append-CXXFLAGS",
            dest='appendcxxflags',
            help="Appends the given text to the CXXFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--append-LDFLAGS",
            dest='appendldflags',
            help="Prepends the given text to the LDFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--append-LINKFLAGS",
            dest='appendldflags',
            help="Prepends the given text to the LDFLAGS already set. Synonym for append-LDFLAGS. Useful for adding search paths etc. ")
        ct.utils.add_boolean_argument(
            parser=cap,
            name="file-list",
            dest='filelist',
                default=False,
                help="Print list of referenced files.")        
        ct.makefile.MakefileCreator.add_arguments(cap)
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
