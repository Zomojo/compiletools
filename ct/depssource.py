from __future__ import unicode_literals
from __future__ import print_function
import sys
import configargparse
import ct.wrappedos
import ct.utils
from ct.hunter import Hunter

class FlatStyle:
    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print(source)


class IndentStyle:
    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print('\t',source)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    cap = configargparse.getArgumentParser()
    cap.add(
        "filename",
        help='File to find source dependencies for."',
        nargs='+')

    # Figure out what output style classes are available and add them to the
    # command line options
    styles = [st[:-5] for st in dict(globals()) if st.endswith('Style')]
    cap.add(
        '--style',
        choices=styles,
        default='Indent',
        help="Output formatting style")

    hunter = Hunter(argv)

    myargs = cap.parse_known_args(args=argv[1:])
    ct.utils.verbose_print_args(myargs[0])

    styleclass = globals()[myargs[0].style + 'Style']
    styleobject = styleclass()

    for filename in myargs[0].filename:
        realpath = ct.wrappedos.realpath(filename)        
        sourcefiles = hunter.required_source_files(realpath)
        try:
            # Remove realpath from the list so that we can 
            # have it left justified and tab in the deps
            sourcefiles.remove(realpath)
        except KeyError:
            pass
        print(realpath)
        styleobject(sourcefiles)

    return 0
