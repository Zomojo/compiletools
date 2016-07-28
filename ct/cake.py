from __future__ import print_function
from __future__ import unicode_literals

import sys
import configargparse
import subprocess
import os
from io import open
import shutil
import ct.utils
import ct.headerdeps
import ct.magicflags
import ct.hunter
import ct.makefile
import ct.filelist
import ct.findtargets

class Cake:

    def __init__(self, args):
        self.args = args

    @staticmethod
    def _cpus():
        with open("/proc/cpuinfo") as ff:
            proclines = [
                line for line in ff.readlines() if line.startswith("processor")]
        if 0 == len(proclines):
            return 1
        else:
            return len(proclines)

    @staticmethod
    def _add_prepend_append_argument(cap, name, destname=None, extrahelp=None):
        """ Add a prepend flags argument and an append flags argument to the config arg parser """
        if destname is None:
            destname = name

        if extrahelp is None:
            extrahelp = ""

        cap.add("".join(["--",
                         "prepend",
                         "-",
                         name.upper()]),
                dest="".join(["prepend",
                              destname.lower()]),
                help=" ".join(["prepend".title(),
                               "the given text to the",
                               name.upper(),
                               "already set. Useful for adding search paths etc.",
                               extrahelp]))
        cap.add("".join(["--",
                         "append",
                         "-",
                         name.upper()]),
                dest="".join(["append",
                              destname.lower()]),
                help=" ".join(["append".title(),
                               "the given text to the",
                               name.upper(),
                               "already set. Useful for adding search paths etc.",
                               extrahelp]))

    @staticmethod
    def add_arguments(cap):
        ct.makefile.MakefileCreator.add_arguments(cap)

        Cake._add_prepend_append_argument(cap, 'cppflags')
        Cake._add_prepend_append_argument(cap, 'cflags')
        Cake._add_prepend_append_argument(cap, 'cxxflags')
        Cake._add_prepend_append_argument(cap, 'ldflags')
        Cake._add_prepend_append_argument(
            cap,
            'linkflags',
            destname='ldflags',
            extrahelp='Synonym for setting LDFLAGS.')

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
        cap.add(
            "--endtests",
            action='store_true',
            help="Ignored. For backwards compatibility only.")

        ct.utils.add_boolean_argument(
            parser=cap,
            name="auto",
            default=False,
            help="Search the filesystem from the current working directory to find all the C/C++ files with main functions and unit tests")
        ct.findtargets.add_arguments(cap)

        cap.add(
            "-j",
            "--parallel",
            dest='parallel',
            type=int,
            default=2 *
            Cake._cpus(),
            help="Sets the number of CPUs to use in parallel for a build.  Defaults to 2 * all cpus.")

    def _callfilelist(self):
        # The extra arguments were deliberately left off before due to conflicts.
        # Add them on now.
        cap = configargparse.getArgumentParser()
        ct.filelist.Filelist.add_arguments(cap)
        args = ct.utils.parseargs(cap)
        filelist = ct.filelist.Filelist(args)
        filelist.process()

    def _callmakefile(self):
        if self.args.auto:
            findtargets = ct.findtargets.FindTargets(self.args)
            executabletargets, testtargets = findtargets()
            self.args.filename += executabletargets
            if testtargets:
                if not self.args.tests:
                    self.args.tests = []
                self.args.tests += testtargets

            # Since we've fiddled with the args, 
            # run the common substitutions again
            # Primarily, this fixes the --includes for the git root of the targets
            ct.utils.commonsubstitutions(self.args)

        namer = ct.utils.Namer(self.args)
        headerdeps = ct.headerdeps.create(self.args)
        magicflags = ct.magicflags.create(self.args, headerdeps)
        hunter = ct.hunter.Hunter(self.args, headerdeps, magicflags)
        makefile_creator = ct.makefile.MakefileCreator(self.args, hunter)
        makefilename = makefile_creator.create()
        movedmakefile = os.path.join(namer.executable_dir(), makefilename)
        ct.wrappedos.makedirs(namer.executable_dir())
        shutil.move(makefilename, movedmakefile)
        cmd = ['make', '-j', str(self.args.parallel), '-f', movedmakefile]
        subprocess.check_call(cmd, universal_newlines=True)

        # Copy the executables into the "bin" dir (as per cake)
        # Unless the user has changed the bindir in which case assume
        # that they know what they are doing
        outputdir = namer.topbindir()

        filelist = os.listdir(namer.executable_dir())
        for ff in filelist:
            filename = os.path.join(namer.executable_dir(), ff)
            if ct.utils.isexecutable(filename):
                shutil.copy2(filename, outputdir)

    def process(self):
        """ Transform the arguments into suitable versions for ct-* tools
            and call the appropriate tool.
        """
        if self.args.prependcppflags:
            self.args.CPPFLAGS = " ".join(
                [self.args.prependcppflags, self.args.CPPFLAGS])
        if self.args.prependcflags:
            self.args.CFLAGS = " ".join(
                [self.args.prependcflags, self.args.CFLAGS])
        if self.args.prependcxxflags:
            self.args.CXXFLAGS = " ".join(
                [self.args.prependcxxflags, self.args.CXXFLAGS])
        if self.args.prependldflags:
            self.args.LDFLAGS = " ".join(
                [self.args.prependldflags, self.args.LDFLAGS])
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
    cap = configargparse.getArgumentParser()
    Cake.add_arguments(cap)
    args = ct.utils.parseargs(cap, argv)
    cake = Cake(args)
    cake.process()

    return 0
