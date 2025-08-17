import signal
import sys
import configargparse
import subprocess
import os
from io import open
import shutil
import compiletools.utils
import compiletools.apptools
import compiletools.headerdeps
import compiletools.magicflags
import compiletools.hunter
import compiletools.makefile
import compiletools.filelist
import compiletools.findtargets
import compiletools.jobs
import compiletools.wrappedos
import compiletools.timing


class Cake(object):
    def __init__(self, args):
        self.args = args
        self.namer = None
        self.headerdeps = None
        self.magicparser = None
        self.hunter = None

    @staticmethod
    def _hide_makefilename(args):
        """ Change the args.makefilename to hide the Makefile in the executable_dir()
            This is a callback function for the compiletools.apptools.substitutions.
        """
        namer = compiletools.namer.Namer(args)
        if namer.executable_dir() not in args.makefilename:
            movedmakefile = os.path.join(namer.executable_dir(), args.makefilename)
            if args.verbose > 4:
                print(
                    "Makefile location is being altered.  New location is {}".format(
                        movedmakefile
                    )
                )
            args.makefilename = movedmakefile

    @staticmethod
    def registercallback():
        """ Must be called before object creation so that the args parse
            correctly
        """
        compiletools.apptools.registercallback(Cake._hide_makefilename)

    def _createctobjs(self):
        """ Has to be separate because --auto fiddles with the args """
        self.namer = compiletools.namer.Namer(self.args)
        self.headerdeps = compiletools.headerdeps.create(self.args)
        self.magicparser = compiletools.magicflags.create(self.args, self.headerdeps)
        self.hunter = compiletools.hunter.Hunter(self.args, self.headerdeps, self.magicparser)

    @staticmethod
    def add_arguments(cap):
        compiletools.makefile.MakefileCreator.add_arguments(cap)
        compiletools.jobs.add_arguments(cap)

        cap.add(
            "--file-list",
            "--filelist",
            dest="filelist",
            action="store_true",
            help="Print list of referenced files.",
        )
        compiletools.filelist.Filelist.add_arguments(cap)  # To get the style arguments

        cap.add(
            "--begintests",
            dest="tests",
            nargs="*",
            help="Starts a test block. The cpp files following this declaration will generate executables which are then run. Synonym for --tests",
        )
        cap.add(
            "--endtests",
            action="store_true",
            help="Ignored. For backwards compatibility only.",
        )

        compiletools.findtargets.add_arguments(cap)

        compiletools.utils.add_boolean_argument(
            parser=cap,
            name="preprocess",
            default=False,
            help="Set both --magic=cpp and --headerdeps=cpp. Defaults to false because it is slower.",
        )

        cap.add(
            "--CAKE_PREPROCESS",
            dest="preprocess",
            default=False,
            help="Deprecated. Synonym for preprocess",
        )

        cap.add("--clean", action="store_true", help="Agressively cleanup.")

        cap.add(
            "-o",
            "--output",
            help="When there is only a single build product, rename it to this name.",
        )

    def _callfilelist(self):
        filelist = compiletools.filelist.Filelist(self.args, self.hunter, style="flat")
        filelist.process()

    def _copyexes(self):
        # Copy the executables into the "bin" dir (as per cake)
        # Unless the user has changed the bindir (or set --output)
        # in which case assume that they know what they are doing
        if self.args.output:
            if self.args.verbose > 0:
                print(self.args.output)
            if self.args.filename:
                compiletools.wrappedos.copy(
                    self.namer.executable_pathname(self.args.filename[0]),
                    self.args.output,
                )
            if self.args.static:
                compiletools.wrappedos.copy(self.namer.staticlibrary_pathname(), self.args.output)
            if self.args.dynamic:
                compiletools.wrappedos.copy(
                    self.namer.dynamiclibrary_pathname(), self.args.output
                )
        else:
            outputdir = self.namer.topbindir()
            filelist = self.namer.all_executable_pathnames()
            for srcexe in filelist:
                base = os.path.basename(srcexe)
                destexe = compiletools.wrappedos.realpath(os.path.join(outputdir, base))
                if compiletools.utils.isexecutable(srcexe) and srcexe != destexe:
                    if self.args.verbose > 0:
                        print("".join([outputdir, base]))
                    compiletools.wrappedos.copy(srcexe, outputdir)

            if self.args.static:
                src = self.namer.staticlibrary_pathname()
                filename = self.namer.staticlibrary_name()
                dest = compiletools.wrappedos.realpath(os.path.join(outputdir, filename))
                if src != dest:
                    if self.args.verbose > 0:
                        print(os.path.join(outputdir, filename))
                    compiletools.wrappedos.copy(src, outputdir)

            if self.args.dynamic:
                src = self.namer.dynamiclibrary_pathname()
                filename = self.namer.dynamiclibrary_name()
                dest = compiletools.wrappedos.realpath(os.path.join(outputdir, filename))
                if src != dest:
                    if self.args.verbose > 0:
                        print(os.path.join(outputdir, filename))
                    compiletools.wrappedos.copy(src, outputdir)

    def _callmakefile(self):
        makefile_creator = compiletools.makefile.MakefileCreator(self.args, self.hunter)
        makefilename = makefile_creator.create()
        os.makedirs(self.namer.executable_dir(), exist_ok=True)
        cmd = ["make"]
        if self.args.verbose <= 1:
            cmd.append("-s")
        if self.args.verbose >= 4:
            # --trace first comes in GNU make 4.0
            make_version = (
                subprocess.check_output(["make", "--version"], universal_newlines=True)
                .splitlines()[0]
                .split(" ")[-1]
                .split(".")[0]
            )
            if int(make_version) >= 4:
                cmd.append("--trace")
        cmd.extend(["-j", str(self.args.parallel), "-f", self.args.makefilename])
        if self.args.clean:
            cmd.append("realclean")
        else:
            cmd.append("build")
        if self.args.verbose >= 1:
            print(" ".join(cmd))
        subprocess.check_call(cmd, universal_newlines=True)

        if self.args.tests and not self.args.clean:
            cmd = ["make"]
            cmd.extend(["-j", str(self.args.parallel)])
            if self.args.verbose < 2:
                cmd.append("-s")
            cmd.extend(["-f", self.args.makefilename, "runtests"])
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
        if self.args.verbose > 4:
            print("Early scanning. Cake determining targets and implied files")

        with compiletools.timing.time_operation("create_ct_objects"):
            self._createctobjs()
        recreateobjs = False
        if self.args.static and len(self.args.static) == 1:
            with compiletools.timing.time_operation("static_source_hunting"):
                self.args.static.extend(
                    self.hunter.required_source_files(self.args.static[0])
                )
            recreateobjs = True

        if self.args.dynamic and len(self.args.dynamic) == 1:
            with compiletools.timing.time_operation("dynamic_source_hunting"):
                self.args.dynamic.extend(
                    self.hunter.required_source_files(self.args.dynamic[0])
                )
            recreateobjs = True

        if self.args.auto:
            with compiletools.timing.time_operation("target_detection"):
                findtargets = compiletools.findtargets.FindTargets(self.args)
                findtargets.process(self.args)
            recreateobjs = True

        if recreateobjs:
            # Since we've fiddled with the args,
            # run the substitutions again
            # Primarily, this fixes the --includes for the git root of the
            # targets. And recreate the ct objects
            if self.args.verbose > 4:
                print("Cake recreating objects and reparsing for second stage processing")
            with compiletools.timing.time_operation("recreate_ct_objects"):
                compiletools.apptools.substitutions(self.args, verbose=0)
                self._createctobjs()

        compiletools.apptools.verboseprintconfig(self.args)

        if self.args.filelist:
            with compiletools.timing.time_operation("filelist_generation"):
                self._callfilelist()
        else:
            with compiletools.timing.time_operation("makefile_creation_and_execution"):
                self._callmakefile()

    def clear_cache(self):
        """ Only useful in test scenarios where you need to reset to a pristine state """
        compiletools.wrappedos.clear_cache()
        compiletools.utils.clear_cache()
        compiletools.git_utils.clear_cache()
        self.namer.clear_cache()
        self.hunter.clear_cache()
        compiletools.magicflags.MagicFlagsBase.clear_cache()


def signal_handler(signal, frame):
    sys.exit(0)


def main(argv=None):
    cap = compiletools.apptools.create_parser(
        "A convenience tool to aid migration from cake to the ct-* tools", argv=argv
    )
    Cake.add_arguments(cap)
    Cake.registercallback()

    args = compiletools.apptools.parseargs(cap, argv)

    # Initialize timing if enabled
    timing_enabled = hasattr(args, 'time') and args.time
    compiletools.timing.initialize_timer(timing_enabled)

    if not any([args.filename, args.static, args.dynamic, args.tests, args.auto]):
        print(
            "Nothing for cake to do.  Did you mean cake --auto? Use cake --help for help."
        )
        return 0

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGPIPE, signal_handler)

    try:
        cake = Cake(args)
        with compiletools.timing.time_operation("total_build_time"):
            cake.process()
        # For testing purposes, clear out the memcaches for the times when main is called more than once.
        cake.clear_cache()
    except IOError as ioe:
        if args.verbose < 2:
            print(" ".join(["Error processing", ioe.filename, ". Does it exist?"]))
            return 1
        else:
            raise
    except Exception as err:
        if args.verbose < 2:
            print(err)
            return 1
        else:
            raise
    
    # Report timing information if enabled
    if timing_enabled:
        compiletools.timing.report_timing(args.verbose)

    return 0
