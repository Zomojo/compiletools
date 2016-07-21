from __future__ import print_function
from __future__ import unicode_literals

import sys
import configargparse
import ct.utils
import ct.makefile
import ct.filelist

class Cake:
    def __init__(self, args):
        self.args = args

    @staticmethod
    def add_arguments(cap, variant, argv):
        cap.add(
            "--append-CPPFLAGS",
            dest=appendcppflags,
            help="Appends the given text to the CPPFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--append-CFLAGS",
            dest=appendcflags,
            help="Appends the given text to the CFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--append-CXXFLAGS",
            dest=appendcxxflags,
            help="Appends the given text to the CXXFLAGS already set. Useful for adding search paths etc. ")
        ct.utils.add_boolean_argument(
            parser=cap,
            name="file-list",
            dest="filelist",
                default=False,
                help="Print list of referenced files.")
        ct.makefile.MakefileCreator.add_arguments(cap, variant, argv)
        ct.filelist.Filelist.add_arguments(cap)

    def process(self):
        """ Transform the arguments into suitable versions for ct-* tools 
            and call the appropriate tool.
        """
        if self.args.appendcppflags:
            self.args.CPPFLAGS += self.args.appendcppflags
        if self.args.appendcflags:
            self.args.CFLAGS += self.args.appendcflags
        if self.args.appendcxxflags:
            self.args.CXXFLAGS += self.args.appendcxxflags

        if self.args.filelist:
            filelist = ct.filelist.Filelist(self.args)
            filelist.process()
        else:
            makefile_creator = ct.makefile.MakefileCreator(args)
            makefile_creator.create()

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
