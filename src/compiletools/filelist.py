import sys
import os
import configargparse

import compiletools.utils
import compiletools.git_utils
import compiletools.wrappedos
import compiletools.apptools
from compiletools.hunter import Hunter


class FlatStyle(compiletools.git_utils.NameAdjuster):
    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print(self.adjust(source))


class IndentStyle(compiletools.git_utils.NameAdjuster):
    def __call__(self, sourcefiles):
        for source in sourcefiles:
            print("\t", self.adjust(source))


class HeaderPassFilter(object):
    def __call__(self, files):
        return {fn for fn in files if compiletools.utils.isheader(fn)}


class SourcePassFilter(object):
    def __call__(self, files):
        return {fn for fn in files if compiletools.utils.issource(fn)}


class AllPassFilter(object):
    def __call__(self, files):
        return files


def check_filename(filename):
    if not compiletools.wrappedos.isfile(filename):
        sys.stderr.write(
            "The supplied filename ({0}) isn't a file. "
            "Did you spell it correctly?"
            "Another possible reason is that you didn't supply a filename"
            " and that configargparse has picked an unused positional argument"
            " from the config file.\n".format(filename)
        )
        exit(1)


class Filelist(object):
    def __init__(self, args, hunter, style=None):
        self.args = args
        self._hunter = hunter

        if style is None:
            style = self.args.style
        styleclass = globals()[style.title() + "Style"]
        self.styleobject = styleclass(args)

    @staticmethod
    def add_arguments(cap):
        compiletools.apptools.add_target_arguments(cap)
        cap.add(
            "--extrafile", help="Extra files to directly add to the filelist", nargs="*"
        )
        cap.add(
            "--extradir",
            help="Extra directories to add all files from to the filelist",
            nargs="*",
        )
        cap.add(
            "--extrafilelist",
            help="Read the given files to find a list of extra files to add to the filelist",
            nargs="*",
        )

        # Figure out what output style classes are available and add them to the
        # command line options
        styles = [st[:-5].lower() for st in dict(globals()) if st.endswith("Style")]
        cap.add(
            "--style", choices=styles, default="flat", help="Output formatting style"
        )

        passfilters = [
            st[:-10].lower() for st in dict(globals()) if st.endswith("PassFilter")
        ]
        cap.add(
            "--filter",
            choices=passfilters,
            default="all",
            help="What type of files are allowed in the output",
        )

        compiletools.utils.add_flag_argument(
            cap, "merge", default=True, help="Merge all outputs into a single list"
        )
        compiletools.hunter.add_arguments(cap)

    def process(self):
        filterclass = globals()[self.args.filter.title() + "PassFilter"]
        filterobject = filterclass()
        extras = set()

        # Add all the command line specified extras
        if self.args.extrafile:
            extras.update(self.args.extrafile)
        if self.args.extradir:
            for ed in self.args.extradir:
                extras.update([
                    os.path.join(ed, ff)
                    for ff in os.listdir(ed)
                    if compiletools.wrappedos.isfile(os.path.join(ed, ff))
                ])
        if self.args.extrafilelist:
            for fname in self.args.extrafilelist:
                with open(fname) as ff:
                    extras.update([line.strip() for line in ff.readlines()])

        # Add all the files in the same directory as test files
        if self.args.tests:
            for testfile in self.args.tests:
                testdir = compiletools.wrappedos.dirname(compiletools.wrappedos.realpath(testfile))
                extras |= {
                    os.path.join(testdir, fileintestdir)
                    for fileintestdir in os.listdir(testdir)
                    if compiletools.wrappedos.isfile(os.path.join(testdir, fileintestdir))
                }

        mergedfiles = []
        if self.args.merge:
            filteredfiles = filterobject(
                {compiletools.wrappedos.realpath(fname) for fname in extras}
            )
            mergedfiles.extend(filteredfiles)
        else:
            for fname in extras:
                realpath = compiletools.wrappedos.realpath(fname)
                print(self.styleobject.adjust(realpath))

        followable = []
        lists = [
            self.args.filename,
            self.args.static,
            self.args.dynamic,
            self.args.tests,
        ]
        for ll in lists:
            if ll:
                followable.extend(ll)
        followable = compiletools.utils.ordered_unique(followable)
        for filename in followable:
            check_filename(filename)
            realpath = compiletools.wrappedos.realpath(filename)
            files = self._hunter.required_files(realpath)
            filteredfiles = filterobject(files)

            if self.args.merge:
                mergedfiles.extend(filteredfiles)
            else:
                try:
                    # Remove realpath from the list so that the style object
                    # doesn't have to worry about it.
                    filteredfiles = [f for f in filteredfiles if f != realpath]
                except KeyError:
                    pass
                print(self.styleobject.adjust(realpath))
                self.styleobject(sorted(filteredfiles))

        if self.args.merge:
            mergedfiles = compiletools.utils.ordered_unique(mergedfiles)
            self.styleobject(sorted(mergedfiles))


def main(argv=None):
    cap = compiletools.apptools.create_parser("Generate file lists for packaging", argv=argv, include_config=False)
    Filelist.add_arguments(cap)
    args = compiletools.apptools.parseargs(cap, argv)
    headerdeps = compiletools.headerdeps.create(args)
    magicparser = compiletools.magicflags.create(args, headerdeps)
    hunter = compiletools.hunter.Hunter(args, headerdeps, magicparser)
    filelist = Filelist(args, hunter)
    filelist.process()

    # For testing purposes, clear out the memcaches for the times when main is called more than once.
    compiletools.wrappedos.clear_cache()
    compiletools.utils.clear_cache()
    compiletools.git_utils.clear_cache()
    headerdeps.clear_cache()
    magicparser.clear_cache()
    hunter.clear_cache()

    return 0
