from __future__ import print_function
from __future__ import unicode_literals

import sys
import configargparse
import subprocess
import os
from io import open
import shutil
import ct.utils
import ct.apptools
import ct.headerdeps
import ct.magicflags
import ct.hunter
import ct.makefile
import ct.filelist
import ct.findtargets
import ct.jobs

class Cake:

    def __init__(self, args):
        self.args = args
        self.namer = None
        self.headerdeps = None
        self.magicparser = None
        self.hunter = None

    def _createctobjs(self):
        """ Has to be separate because --auto fiddles with the args """
        self.namer = ct.namer.Namer(self.args)
        self.headerdeps = ct.headerdeps.create(self.args)
        self.magicparser = ct.magicflags.create(self.args, self.headerdeps)
        self.hunter = ct.hunter.Hunter(
            self.args,
            self.headerdeps,
            self.magicparser)


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
        ct.jobs.add_arguments(cap)

        Cake._add_prepend_append_argument(cap, 'cppflags')
        Cake._add_prepend_append_argument(cap, 'cflags')
        Cake._add_prepend_append_argument(cap, 'cxxflags')
        Cake._add_prepend_append_argument(cap, 'ldflags')
        Cake._add_prepend_append_argument(
            cap,
            'linkflags',
            destname='ldflags',
            extrahelp='Synonym for setting LDFLAGS.')

        cap.add(
            "--file-list",
            "--filelist",
            dest='filelist',
            action='store_true',
            help="Print list of referenced files.")
        ct.filelist.Filelist.add_arguments(cap)  # To get the style arguments

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

        ct.utils.add_boolean_argument(
            parser=cap,
            name="preprocess",
            default=False,
            help="Set both --magic=cpp and --headerdeps=cpp. Defaults to false because it is slower.")

        cap.add(
            "--CAKE_PREPROCESS",
            dest="preprocess",
            default=False,
            help="Deprecated. Synonym for preprocess")
        
        cap.add(
            "--clean",
            action='store_true',
            help="Agressively cleanup.")

        cap.add(
            "-o",
            "--output",
            help="When there is only a single build product, rename it to this name.")

    def _callfilelist(self):
        filelist = ct.filelist.Filelist(self.args, self.hunter, style='flat')
        filelist.process()

    def _callmakefile(self):
        makefile_creator = ct.makefile.MakefileCreator(self.args, self.hunter)
        makefilename = makefile_creator.create()
        movedmakefile = os.path.join(self.namer.executable_dir(), makefilename)
        ct.wrappedos.makedirs(self.namer.executable_dir())
        shutil.move(makefilename, movedmakefile)        
        cmd = ['make', '-j', str(self.args.parallel), '-f', movedmakefile]
        if self.args.clean:
            cmd.append('realclean')
        else:
            cmd.append('build')
        if self.args.verbose >= 2:
            print(" ".join(cmd))
        subprocess.check_call(cmd, universal_newlines=True)

        if self.args.tests and not self.args.clean:
            cmd = ['make', '-f', movedmakefile, 'runtests']
            if self.args.verbose >= 2:
                print(" ".join(cmd))
            subprocess.check_call(cmd, universal_newlines=True)

        if self.args.clean:
            # Remove the extra executables we copied
            if self.args.output:
                try:
                    os.remove(self.args.output)
                except OSError:
                    pass
            else:
                outputdir = self.namer.topbindir()
                filelist = os.listdir(outputdir)
                for ff in filelist:
                    filename = os.path.join(outputdir, ff)
                    try:
                        os.remove(filename)
                    except OSError:
                        pass
        else:
            # Copy the executables into the "bin" dir (as per cake)
            # Unless the user has changed the bindir (or set --output)
            # in which case assume that they know what they are doing
            if self.args.output:
                if self.args.filename:
                    shutil.copy2(self.namer.executable_pathname(self.args.filename[0]), self.args.output)
                if self.args.static:
                    shutil.copy2(self.namer.staticlibrary_pathname(self.args.static[0]), self.args.output)
                if self.args.dynamic:
                    shutil.copy2(self.namer.dynamiclibrary_pathname(self.args.dynamic[0]), self.args.output)
            else:
                outputdir = self.namer.topbindir()
                filelist = os.listdir(self.namer.executable_dir())
                for ff in filelist:
                    filename = os.path.join(self.namer.executable_dir(), ff)
                    if ct.utils.isexecutable(filename):
                            shutil.copy2(filename, outputdir)
                if self.args.static:
                    filename = self.namer.staticlibrary_pathname(self.args.static[0])
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

        # Cake used preprocess to mean both magic flag preprocess and headerdeps preprocess
        if self.args.preprocess:
            self.args.magic = 'cpp'
            self.args.headerdeps = 'cpp'
        
        # If the user specified only a single file to be turned into a library, guess that
        # they mean for ct-cake to chase down all the implied files.
        self._createctobjs()
        if self.args.static and len(self.args.static) == 1:
            self.args.static.extend(self.hunter.required_source_files(self.args.static[0]))
        if self.args.dynamic and len(self.args.dynamic) == 1:
            self.args.dynamic.extend(self.hunter.required_source_files(self.args.dynamic[0]))

        if self.args.auto:
            findtargets = ct.findtargets.FindTargets(self.args)
            executabletargets, testtargets = findtargets()
            self.args.filename += executabletargets
            if testtargets:
                if not self.args.tests:
                    self.args.tests = []
                self.args.tests += testtargets

            if self.args.verbose >= 2:
                #styleclass = globals()['ct.findtargets.'+ self.args.style.title() + 'Style']
                #styleobj = styleclass()
                styleobj = ct.findtargets.IndentStyle()
                styleobj(executabletargets, testtargets)

        # Since we've fiddled with the args,
        # run the common substitutions again
        # Primarily, this fixes the --includes for the git root of the
        # targets. And recreate the ct objects
        ct.apptools.commonsubstitutions(self.args)
        self._createctobjs()

        if self.args.filelist:
            self._callfilelist()
        else:
            self._callmakefile()


def main(argv=None):
    cap = configargparse.getArgumentParser()
    Cake.add_arguments(cap)
    args = ct.apptools.parseargs(cap, argv)
    cake = Cake(args)
    cake.process()

    return 0
