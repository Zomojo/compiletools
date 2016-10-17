from __future__ import print_function
from __future__ import unicode_literals

import signal
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

    @staticmethod
    def _hide_makefilename(args):
        """ Change the args.makefilename to hide the Makefile in the executable_dir()
            This is a callback function for the ct.apptools.substitutions.
        """
        namer = ct.namer.Namer(args)
        if namer.executable_dir() not in args.makefilename:
            movedmakefile = os.path.join(
                namer.executable_dir(), args.makefilename)
            if args.verbose > 4:
                print(
                    "Makefile location is being altered.  New location is {}".format(movedmakefile))
            args.makefilename = movedmakefile

    @staticmethod
    def registercallback():
        """ Must be called before object creation so that the args parse
            correctly
        """
        ct.apptools.registercallback(Cake._hide_makefilename)

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
                action="append",
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
                action="append",
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

    def _copyexes(self):
        # Copy the executables into the "bin" dir (as per cake)
        # Unless the user has changed the bindir (or set --output)
        # in which case assume that they know what they are doing
        if self.args.output:
            print(self.args.output)
            if self.args.filename:
                ct.wrappedos.copy(
                    self.namer.executable_pathname(
                        self.args.filename[0]),
                    self.args.output)
            if self.args.static:
                ct.wrappedos.copy(
                    self.namer.staticlibrary_pathname(),
                    self.args.output)
            if self.args.dynamic:
                ct.wrappedos.copy(
                    self.namer.dynamiclibrary_pathname(),
                    self.args.output)
        else:
            outputdir = self.namer.topbindir()
            filelist = self.namer.all_executable_pathnames()
            for srcexe in filelist:
                base = os.path.basename(srcexe)
                destexe = ct.wrappedos.realpath(
                    os.path.join(outputdir, base))
                if ct.utils.isexecutable(srcexe) and srcexe != destexe:
                    print("".join([outputdir, base]))
                    ct.wrappedos.copy(srcexe, outputdir)

            if self.args.static:
                src = self.namer.staticlibrary_pathname()
                filename = self.namer.staticlibrary_name()
                dest = ct.wrapped.realpath(os.path.join(outputdir, filename))
                if src != dest:
                    print(os.path.join(outputdir, filename))
                    ct.wrappedos.copy(src, outputdir)

            if self.args.dynamic:
                src = self.namer.dynamiclibrary_pathname()
                filename = self.namer.dynamiclibrary_name()
                dest = ct.wrapped.realpath(os.path.join(outputdir, filename))
                if src != dest:
                    print(os.path.join(outputdir, filename))
                    ct.wrappedos.copy(src, outputdir)

    def _callmakefile(self):
        makefile_creator = ct.makefile.MakefileCreator(self.args, self.hunter)
        makefilename = makefile_creator.create()
        ct.wrappedos.makedirs(self.namer.executable_dir())
        cmd = ['make']
        if self.args.verbose <= 1:
            cmd.append('-s')
        if self.args.verbose >= 4:
            cmd.append('--trace')
        cmd.extend(['-j', str(self.args.parallel),
                    '-f', self.args.makefilename])
        if self.args.clean:
            cmd.append('realclean')
        else:
            cmd.append('build')
        if self.args.verbose >= 1:
            print(" ".join(cmd))
        subprocess.check_call(cmd, universal_newlines=True)

        if self.args.tests and not self.args.clean:
            cmd = ['make']
            if self.args.verbose < 2:
                cmd.append('-s')
            cmd.extend(['-f', self.args.makefilename, 'runtests'])
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
            self._copyexes()

    def process(self):
        """ Transform the arguments into suitable versions for ct-* tools
            and call the appropriate tool.
        """
        # If the user specified only a single file to be turned into a library, guess that
        # they mean for ct-cake to chase down all the implied files.
        self._createctobjs()
        recreateobjs = False
        if self.args.static and len(self.args.static) == 1:
            self.args.static.extend(
                self.hunter.required_source_files(
                    self.args.static[0]))
            recreateobjs = True

        if self.args.dynamic and len(self.args.dynamic) == 1:
            self.args.dynamic.extend(
                self.hunter.required_source_files(
                    self.args.dynamic[0]))
            recreateobjs = True

        if self.args.auto:
            findtargets = ct.findtargets.FindTargets(self.args)
            findtargets.process(self.args)
            recreateobjs = True

        if recreateobjs:
            # Since we've fiddled with the args,
            # run the substitutions again
            # Primarily, this fixes the --includes for the git root of the
            # targets. And recreate the ct objects
            ct.apptools.substitutions(self.args, verbose=0)
            self._createctobjs()

        ct.apptools.verboseprintconfig(self.args)

        if self.args.filelist:
            self._callfilelist()
        else:
            self._callmakefile()


def signal_handler(signal, frame):
    sys.exit(0)


def main(argv=None):
    cap = configargparse.getArgumentParser()
    Cake.add_arguments(cap)
    Cake.registercallback()

    if argv is None:
        # Output of stdout is done via increasing the verbosity
        # Developers seem to be "default happy" when verbosity defaults to 1
        sys.argv.append('-v')
    args = ct.apptools.parseargs(cap, argv, verbose=0)

    if not any([args.filename,
                args.static,
                args.dynamic,
                args.tests,
                args.auto]):
        print(
            'Nothing for cake to do.  Did you mean cake --auto? Use cake --help for help.')
        return 0

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGPIPE, signal_handler)

    try:
        cake = Cake(args)
        cake.process()
    except IOError as ioe:
        if args.verbose < 2:
            print(
                " ".join(["Error processing", ioe.filename, ". Does it exist?"]))
            return 1
        else:
            raise
    except Exception as err:
        if args.verbose < 2:
            print(err.message)
            return 1
        else:
            raise

    return 0
