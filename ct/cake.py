from __future__ import print_function
from __future__ import unicode_literals

import sys
import configargparse
import ct.utils
import ct.makefile
import ct.filelist

class Cake:
    def __init__(self, argv=None):
        self.args = None
        # self.args will exist after this call
        ct.utils.setattr_args(self, argv)

    @staticmethod
    def add_arguments(cap, variant, argv):
        cap.add(
            "--append-CPPFLAGS",
            help="Appends the given text to the CPPFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--append-CFLAGS",
            help="Appends the given text to the CFLAGS already set. Useful for adding search paths etc. ")
        cap.add(
            "--append-CXXFLAGS",
            help="Appends the given text to the CXXFLAGS already set. Useful for adding search paths etc. ")
        ct.utils.add_boolean_argument(
            parser=cap,
            name="file-list",
            dest="filelist",
                default=False,
                help="Print list of referenced files.")
        ct.makefile.MakefileCreator.add_arguments(cap, variant, argv)
        ct.filelist.Filelist.add_arguments(cap)

    def process(self,argv):
        """ Transform the arguments into suitable versions for ct-* tools """
        #makefile_creator = ct.makefile.MakefileCreator(parser=cap, variant=variant, argv=argv)
        if self.args.filelist:
            filelist = ct.filelist.Filelist()
            filelist.process(argv)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    variant = ct.utils.extract_variant_from_argv(argv)
    cap = configargparse.getArgumentParser()
    Cake.add_arguments(cap, variant, argv)
    myargs = cap.parse_known_args(args=argv[1:])
    ct.utils.verbose_print_args(myargs[0])

    cake = Cake()
    cake.process(argv)

    return 0
