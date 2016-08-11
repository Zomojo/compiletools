from __future__ import print_function
from __future__ import unicode_literals

import sys
import configargparse

import ct.utils
import ct.git_utils
import ct.wrappedos
from ct.hunter import Hunter


class FlatStyle(ct.git_utils.NameAdjuster):

    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print(self.adjust(source))


class IndentStyle(ct.git_utils.NameAdjuster):

    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print('\t', self.adjust(source))


class HeaderPassFilter(object):

    def __call__(self, files):
        return {fn for fn in files if ct.utils.isheader(fn)}


class SourcePassFilter(object):

    def __call__(self, files):
        return {fn for fn in files if ct.utils.issource(fn)}


class AllPassFilter(object):

    def __call__(self, files):
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


class Filelist(object):

    def __init__(self, args, hunter, style=None):
        self.args = args
        self._hunter = hunter

        if style is None:
            style = self.args.style
        styleclass = globals()[style.title() + 'Style']
        self.styleobject = styleclass(args)

    @staticmethod
    def add_arguments(cap):
        # Don't re-add filename if it is already in the configargparse
        if not any('filename' in action.dest for action in cap._actions):
            cap.add(
                "filename",
                help='File(s) to follow dependencies from.',
                nargs='+')

        # Figure out what output style classes are available and add them to the
        # command line options
        styles = [st[:-5].lower()
                  for st in dict(globals()) if st.endswith('Style')]
        cap.add(
            '--style',
            choices=styles,
            default='flat',
            help="Output formatting style")

        passfilters = [st[:-10].lower()
                       for st in dict(globals()) if st.endswith('PassFilter')]
        cap.add(
            '--filter',
            choices=passfilters,
            default='all',
            help="What type of files are allowed in the output")

        ct.utils.add_boolean_argument(
            cap,
            'merge',
            default=True,
            help='Merge all outputs into a single list')
        ct.hunter.add_arguments(cap)

    def process(self):
        filterclass = globals()[self.args.filter.title() + 'PassFilter']
        filterobject = filterclass()

        mergedfiles = set()
        for filename in self.args.filename:
            check_filename(filename)
            realpath = ct.wrappedos.realpath(filename)
            files = self._hunter.required_files(realpath)
            filteredfiles = filterobject(files)

            if self.args.merge:
                mergedfiles |= filteredfiles
            else:
                try:
                    # Remove realpath from the list so that the style object
                    # doesn't have to worry about it.
                    filteredfiles.remove(realpath)
                except KeyError:
                    pass
                print(self.styleobject.adjust(realpath))
                self.styleobject(sorted(filteredfiles))

        if self.args.merge:
            self.styleobject(sorted(mergedfiles))


def main(argv=None):
    cap = configargparse.getArgumentParser()
    Filelist.add_arguments(cap)
    args = ct.apptools.parseargs(cap, argv)
    headerdeps = ct.headerdeps.create(args)
    magicparser = ct.magicflags.create(args, headerdeps)
    hunter = ct.hunter.Hunter(args, headerdeps, magicparser)
    filelist = Filelist(args, hunter)
    filelist.process()

    return 0
