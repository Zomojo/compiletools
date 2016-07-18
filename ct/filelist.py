from __future__ import print_function
from __future__ import unicode_literals

import sys

import configargparse

import ct.utils
import ct.git_utils
import ct.wrappedos
from ct.hunter import Hunter


class FlatStyle:

    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print(source)


class IndentStyle:

    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print('\t', source)


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

    passfilters = ['header', 'source', 'all']
    cap.add(
        '--filter',
        choices=passfilters,
        default='all',
        help="What type of files are allowed in the output")

    ct.utils.add_boolean_argument(cap, 'merge', default=True, help='Merge all outputs into a single list')
    hunter = Hunter(argv)

    myargs = cap.parse_known_args(args=argv[1:])
    ct.utils.verbose_print_args(myargs[0])

    styleclass = globals()[myargs[0].style + 'Style']
    styleobject = styleclass()

    mergedfiles = set()
    for filename in myargs[0].filename:
        check_filename(filename)
        realpath = ct.wrappedos.realpath(filename)
        files = hunter.required_files(realpath)
        if myargs[0].filter == 'header':
            filteredfiles = {
                filename for filename in files if ct.utils.isheader(filename)}
        elif myargs[0].filter == 'source':
            filteredfiles = {
                filename for filename in files if ct.utils.issource(filename)}
        else:
            filteredfiles = files

        if myargs[0].merge:
            mergedfiles |= filteredfiles
        else:
            try:
                # Remove realpath from the list so that the style object
                # doesn't have to worry about it.
                filteredfiles.remove(realpath)
            except KeyError:
                pass
            outputpath=realpath
            if myargs[0].strip_git_root:
                output=ct.git_utils.strip_git_root(realpath)
            print(outputpath)
            if myargs[0].strip_git_root:
                styleobject({ct.git_utils.strip_git_root(ff) for ff in filteredfiles})
            else:
                styleobject(filteredfiles)

    if myargs[0].merge:
        if myargs[0].strip_git_root:
            styleobject({ct.git_utils.strip_git_root(ff) for ff in mergedfiles})
        else:
            styleobject(sorted(mergedfiles))

    return 0
