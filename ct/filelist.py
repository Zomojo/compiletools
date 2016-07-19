from __future__ import print_function
from __future__ import unicode_literals

import sys
import configargparse

import ct.utils
import ct.git_utils
import ct.wrappedos
from ct.hunter import Hunter

class NameAdjuster(object):
    def __init__(self, strip_git_root):
        self.strip_git_root = strip_git_root

    def adjust(self,name):
        if self.strip_git_root:
            return ct.git_utils.strip_git_root(ff) 
        else:
            return name

class FlatStyle(NameAdjuster):

    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print(self.adjust(source))

class IndentStyle(NameAdjuster):

    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print('\t', self.adjust(source))


class HeaderFilter(object):
    def process(self,files):
        return {fn for fn in files if ct.utils.isheader(fn)}

class SourceFilter(object):
    def process(self,files):
        return {fn for fn in files if ct.utils.issource(fn)}

class AllFilter(object):
    def process(self,files):
        return files


def check_filename(filename):
    if not ct.wrappedos.isfile(filename):
        sys.stderr.write(
            "The supplied filename ({0}) isn't a file. "
            "Did you spell it correctly?"
            "Another possible reason is that you didn't supply a filename"
            " and that configargparse has picked an unused positional argument"
            " from the config file.\n".format(filename))
        exit(1)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    cap = configargparse.getArgumentParser()
    cap.add(
        "filename",
        help='File(s) to follow dependencies from.',
        nargs='+')

    # Figure out what output style classes are available and add them to the
    # command line options
    styles = [st[:-5] for st in dict(globals()) if st.endswith('Style')]
    cap.add(
        '--style',
        choices=styles,
        default='Flat',
        help="Output formatting style")

    passfilters = [st[:-6] for st in dict(globals()) if st.endswith('Filter')]
    cap.add(
        '--filter',
        choices=passfilters,
        default='All',
        help="What type of files are allowed in the output")

    ct.utils.add_boolean_argument(cap, 'merge', default=True, help='Merge all outputs into a single list')
    hunter = Hunter(argv)

    myargs = cap.parse_known_args(args=argv[1:])
    ct.utils.verbose_print_args(myargs[0])

    styleclass = globals()[myargs[0].style + 'Style']
    kwargs = ct.utils.extractinitargs(myargs[0],styleclass)
    styleobject = styleclass(**kwargs)

    filterclass = globals()[myargs[0].filter + 'Filter']
    filterobject = filterclass()

    mergedfiles = set()
    for filename in myargs[0].filename:
        check_filename(filename)
        realpath = ct.wrappedos.realpath(filename)
        files = hunter.required_files(realpath)
        filteredfiles = filterobject.process(files)

        if myargs[0].merge:
            mergedfiles |= filteredfiles
        else:
            try:
                # Remove realpath from the list so that the style object
                # doesn't have to worry about it.
                filteredfiles.remove(realpath)
            except KeyError:
                pass
            print(styleobject.adjust(realpath))
            styleobject(filteredfiles)

    if myargs[0].merge:
        styleobject(sorted(mergedfiles))

    return 0
