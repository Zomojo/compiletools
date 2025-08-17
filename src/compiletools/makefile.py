# vim: set filetype=python:
import os
import sys
from io import open

import configargparse

import compiletools.utils
import compiletools.wrappedos
import compiletools.apptools
import compiletools.headerdeps
import compiletools.magicflags
import compiletools.hunter
import compiletools.namer
import compiletools.configutils
import compiletools.timing


class Rule:
    """A rule is a target, prerequisites and optionally a recipe
    and optionally any order_only_prerequisites.
    https://www.gnu.org/software/make/manual/html_node/Rule-Introduction.html#Rule-Introduction
    Example: myrule = Rule( target='mytarget'
                          , prerequisites='file1.hpp file2.hpp'
                          , recipe='g++ -c mytarget.cpp -o mytarget.o'
                          )
    Note: it had to be a class rather than a dict so that we could hash it.
    """

    def __init__(
        self,
        target,
        prerequisites,
        order_only_prerequisites=None,
        recipe=None,
        phony=False,
    ):
        self.target = target
        self.prerequisites = prerequisites
        self.order_only_prerequisites = order_only_prerequisites
        self.recipe = recipe
        self.phony = phony

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __str__(self):
        return "%r" % self.__dict__

    def __eq__(self, other):
        return self.target == other.target

    def __hash__(self):
        return hash(self.target)

    def write(self, makefile):
        """Write the given rule into the given Makefile."""
        if self.phony:
            makefile.write(" ".join([".PHONY:", self.target, "\n"]))

        linetowrite = "".join([self.target, ": ", self.prerequisites])
        if self.order_only_prerequisites:
            linetowrite += "".join([" | ", self.order_only_prerequisites])

        makefile.write(linetowrite + "\n")
        try:
            makefile.write("\t" + self.recipe + "\n")
        except TypeError:
            pass
        makefile.write("\n")


class LinkRuleCreator(object):
    """Base class to provide common infrastructure for the creation of
    specific link rules by the derived classes.
    """

    def __init__(self, args, namer, hunter):
        self.args = args
        self.namer = namer
        self.hunter = hunter

    def _create_link_rule(
        self,
        outputname,
        completesources,
        linker,
        linkerflags=None,
        extraprereqs=None,
        suppressmagicldflags=False,
    ):
        """For a given source file (so usually the file with the main) and the
        set of complete sources (i.e., all the other source files + the original)
        return the link rule required for the Makefile
        """
        if extraprereqs is None:
            extraprereqs = []
        if linkerflags is None:
            linkerflags = ""

        allprerequisites = " ".join(extraprereqs)
        object_names = {self.namer.object_pathname(source) for source in completesources}
        allprerequisites += " "
        allprerequisites += " ".join(object_names)

        all_magic_ldflags = []
        if not suppressmagicldflags:
            for source in completesources:
                magic_flags = self.hunter.magicflags(source)
                all_magic_ldflags.extend(magic_flags.get("LDFLAGS", []))
                all_magic_ldflags.extend(magic_flags.get("LINKFLAGS", []))  # For backward compatibility with cake
            all_magic_ldflags = compiletools.utils.ordered_unique(all_magic_ldflags)
        recipe = ""
        
        # Add timing for link operations if enabled
        link_timing_prefix = ""
        link_timing_suffix = ""
        if hasattr(self.args, 'time') and self.args.time and self.args.verbose >= 1:
            link_timing_prefix = "@START=$$(date +%s%N); "
            link_timing_suffix = f"; END=$$(date +%s%N); echo \"... linking {outputname} ($$(( ($$END-$$START)/1000000 ))ms)\""
        
        if self.args.verbose >= 1 and not (hasattr(self.args, 'time') and self.args.time):
            recipe += " ".join(["+@echo ...", outputname, ";"])
        
        link_flags = [linker, "-o", outputname] + list(object_names) + list(all_magic_ldflags) + [linkerflags]
        if hasattr(self.args, 'time') and self.args.time and self.args.verbose >= 3:
            # Add -time flag for detailed linker timing
            link_flags.insert(1, "-time")
        
        link_cmd = " ".join(link_flags)
        recipe += link_timing_prefix + link_cmd + link_timing_suffix
        return Rule(target=outputname, prerequisites=allprerequisites, recipe=recipe)


class StaticLibraryLinkRuleCreator(LinkRuleCreator):
    def __call__(self, sources, libraryname):
        rule = self._create_link_rule(
            outputname=libraryname,
            completesources=sources,
            linker="ar -src",
            suppressmagicldflags=True,
        )
        return [rule]


class DynamicLibraryLinkRuleCreator(LinkRuleCreator):
    def __call__(self, sources, libraryname):
        rule = self._create_link_rule(
            outputname=libraryname,
            completesources=sources,
            linker=self.args.LD,
            linkerflags=self.args.LDFLAGS + " -shared",
        )
        return [rule]


class ExeLinkRuleCreator(LinkRuleCreator):
    def __call__(self, sources, libraryname):
        extraprereqs = []
        linkerflags = self.args.LDFLAGS

        # If there is also a library being built then automatically
        # include the path to that library to allow easy linking
        if self.args.static or self.args.dynamic:
            linkerflags += " -L"
            linkerflags += self.namer.executable_dir()
        if self.args.static:
            staticlibrarypathname = self.namer.staticlibrary_pathname(compiletools.wrappedos.realpath(self.args.static[0]))
            libname = os.path.join(self.namer.executable_dir(), os.path.basename(staticlibrarypathname))
            extraprereqs.append(libname)
        if self.args.dynamic:
            dynamiclibrarypathname = self.namer.dynamiclibrary_pathname(compiletools.wrappedos.realpath(self.args.dynamic[0]))
            libname = os.path.join(self.namer.executable_dir(), os.path.basename(dynamiclibrarypathname))
            extraprereqs.append(libname)

        linkrules = {}
        for source in sources:
            if self.args.verbose >= 4:
                print(
                    "ExeLinkRuleCreator. Asking hunter for required_source_files for source=",
                    source,
                )
            completesources = self.hunter.required_source_files(source)
            if self.args.verbose >= 6:
                print(
                    "ExeLinkRuleCreator. Complete list of implied source files for "
                    + source
                    + ": "
                    + " ".join(cs for cs in completesources)
                )
            exename = self.namer.executable_pathname(compiletools.wrappedos.realpath(source))
            rule = self._create_link_rule(
                outputname=exename,
                completesources=completesources,
                linker=self.args.LD,
                linkerflags=linkerflags,
                extraprereqs=extraprereqs,
            )
            linkrules[rule.target] = rule

        return list(linkrules.values())


class MakefileCreator:
    """Create a Makefile based on the filename, --static and --dynamic
    command line options.
    """

    def __init__(self, args, hunter):
        self.args = args

        # Keep track of what build artifacts are created for easier cleanup
        self.objects = set()
        self.object_directories = set()

        # By using a set, duplicate rules will be eliminated.
        # However, rules need to be written to disk in a specific order
        # so we use a dict to maintain order and uniqueness
        self.rules = {}

        self.namer = compiletools.namer.Namer(args)
        self.hunter = hunter

    @staticmethod
    def add_arguments(cap):
        compiletools.apptools.add_target_arguments_ex(cap)
        compiletools.apptools.add_link_arguments(cap)
        # Don't add the output directory arguments. Namer will do it.
        # compiletools.utils.add_output_directory_arguments(parser, variant)
        compiletools.namer.Namer.add_arguments(cap)
        compiletools.hunter.add_arguments(cap)
        cap.add(
            "--makefilename",
            default="Makefile",
            help="Output filename for the Makefile",
        )
        cap.add(
            "--build-only-changed",
            help="Only build the binaries depending on the source or header absolute filenames in this space-delimited list.",
        )
        compiletools.utils.add_flag_argument(
            parser=cap,
            name="serialise-tests",
            dest="serialisetests",
            default=False,
            help="Force the unit tests to run serially rather than in parallel. Defaults to false because it is slower.",
        )

    def _uptodate(self):
        """Is the Makefile up to date?
        If the argv has changed
        then regenerate on the assumption that the filelist or flags have changed
        else check if the modification time of the Makefile is greater than
             the modification times of all the source and header files.
        """
        # Check if the Makefile exists and grab its modification time if it does exist.
        try:
            makefilemtime = compiletools.wrappedos.getmtime(self.args.makefilename)
        except OSError:
            # If the Makefile doesn't exist then we aren't up to date
            if self.args.verbose > 7:
                print("Regenerating Makefile.")
                print(
                    "Could not determine mtime for {}. Assuming that it doesn't exist.".format(self.args.makefilename)
                )
            return False

        # See how the Makefile was previously generated
        expected = "".join(["# Makefile generated by ", str(self.args)])

        with open(self.args.makefilename, mode="r", encoding="utf-8") as mfile:
            previous = mfile.readline().strip()
            if previous != expected:
                if self.args.verbose > 7:
                    print("Regenerating Makefile.")
                    print('Previous generation line was "{}".'.format(previous))
                    print('Current  generation line  is "{}".'.format(expected))
                return False
            elif self.args.verbose > 9:
                print("Makefile header line is identical.  Testing mod time of all the files now.")

        # Check the mod times of all the implied files against the mod time of the Makefile
        for sf in self._gather_root_sources():
            filelist = self.hunter.required_files(sf)
            for ff in filelist:
                if compiletools.wrappedos.getmtime(ff) > makefilemtime:
                    if self.args.verbose > 7:
                        print("Regenerating Makefile.")
                        print(
                            "mtime {} for {} is newer than mtime for the Makefile".format(compiletools.wrappedos.getmtime(ff), ff)
                        )
                    return False
                elif self.args.verbose > 9:
                    print(
                        "mtime {} for {} is older than mtime for the Makefile. This wont trigger regeneration of the Makefile.".format(
                            compiletools.wrappedos.getmtime(ff), ff
                        )
                    )

        if self.args.verbose > 9:
            print("Makefile is up to date.  Not recreating.")

        return True

    def _create_all_rule(self):
        """Create the rule that in depends on all build products"""
        prerequisites = ["build"]
        if self.args.tests:
            prerequisites.append("runtests")

        return Rule(target="all", prerequisites=" ".join(prerequisites), phony=True)

    @staticmethod
    def _create_build_rule(prerequisites):
        """Create the rule that in depends on all build products"""
        return Rule(target="build", prerequisites=" ".join(prerequisites), phony=True)

    def _create_clean_rules(self, alloutputs):
        rules = {}

        # Clean will only remove empty directories
        # Use realclean if you want force directories to be removed.
        rmcopiedexes = " ".join(
            [
                "find",
                self.namer.executable_dir(),
                "-type f -executable -delete 2>/dev/null",
            ]
        )
        rmtargetsandobjects = " ".join(["rm -f"] + list(alloutputs) + list(self.objects))
        rmemptydirs = " ".join(["find", self.namer.object_dir(), "-type d -empty -delete"])
        recipe = ";".join([rmcopiedexes, rmtargetsandobjects, rmemptydirs])

        if self.namer.executable_dir() != self.namer.object_dir():
            recipe += " ".join([";find", self.namer.executable_dir(), "-type d -empty -delete"])

        rule_clean = Rule(target="clean", prerequisites="", recipe=recipe, phony=True)
        rules[rule_clean.target] = rule_clean

        # Now for realclean.  Just take a heavy handed rm -rf approach.
        # Note this will even remove the Makefile generated by ct-cake
        recipe = " ".join(["rm -rf", self.namer.executable_dir()])
        if self.namer.executable_dir() != self.namer.object_dir():
            recipe += "; rm -rf " + self.namer.object_dir()
        rule_realclean = Rule(target="realclean", prerequisites="", recipe=recipe, phony=True)
        rules[rule_realclean.target] = rule_realclean

        return list(rules.values())

    def _create_cp_rule(self, output):
        """Given the original output, copy it to the executable_dir()"""
        if self.namer.executable_dir() == compiletools.wrappedos.dirname(output):
            return None

        return Rule(
            target=os.path.join(self.namer.executable_dir(), os.path.basename(output)),
            prerequisites=output,
            recipe=" ".join(["cp", output, self.namer.executable_dir(), "2>/dev/null ||true"]),
        )

    def _create_test_rules(self, alltestsources):
        testprefix = ""
        if self.args.TESTPREFIX:
            testprefix = self.args.TESTPREFIX

        rules = {}

        # Create the PHONY that will run all the tests
        prerequisites = " ".join([".".join([self.namer.executable_pathname(tt), "result"]) for tt in alltestsources])
        runtestsrule = Rule(target="runtests", prerequisites=prerequisites, phony=True)
        rules[runtestsrule.target] = runtestsrule

        # Create a rule for each individual test
        for tt in alltestsources:
            exename = self.namer.executable_pathname(tt)
            testresult = ".".join([exename, "result"])

            recipe = ""
            if self.args.verbose >= 1:
                recipe += " ".join(["@echo ...", exename, ";"])
            recipe += " ".join(["rm -f", testresult, "&&", testprefix, exename, "&& touch", testresult])
            rule = Rule(target=testresult, prerequisites=exename, recipe=recipe)
            rules[rule.target] = rule
        return list(rules.values())

    @staticmethod
    def _create_tests_not_parallel_rule():
        return Rule(target=".NOTPARALLEL", prerequisites="runtests", phony=True)

    def _gather_root_sources(self):
        """Gather all the source files listed on the command line
        into one uber set
        """
        sources = []
        if self.args.static:
            sources.extend(self.args.static)
        if self.args.dynamic:
            sources.extend(self.args.dynamic)
        if self.args.filename:
            sources.extend(self.args.filename)
        if self.args.tests:
            sources.extend(self.args.tests)
        sources = compiletools.utils.ordered_unique(sources)

        return sources

    def _gather_build_outputs(self):
        """Gathers together object files and other outputs"""
        buildoutputs = []

        if self.args.static:
            staticlibrarypathname = self.namer.staticlibrary_pathname()
            buildoutputs.append(staticlibrarypathname)
            buildoutputs.append(os.path.join(self.namer.executable_dir(), os.path.basename(staticlibrarypathname)))

        if self.args.dynamic:
            dynamiclibrarypathname = self.namer.dynamiclibrary_pathname()
            buildoutputs.append(dynamiclibrarypathname)
            buildoutputs.append(
                os.path.join(
                    self.namer.executable_dir(),
                    os.path.basename(dynamiclibrarypathname),
                )
            )

        buildoutputs.extend(self.namer.all_executable_pathnames())
        if self.args.filename:
            allcopiedexes = {
                os.path.join(self.namer.executable_dir(), self.namer.executable_name(source))
                for source in self.args.filename
            }
            buildoutputs.extend(allcopiedexes)

        buildoutputs.extend(self.namer.all_test_pathnames())
        buildoutputs = compiletools.utils.ordered_unique(buildoutputs)

        return buildoutputs

    def create(self):
        if self._uptodate():
            return

        # Find the realpaths of the given filenames (to avoid this being
        # duplicated many times)
        os.makedirs(self.namer.executable_dir(), exist_ok=True)
        rule = self._create_all_rule()
        self.rules[rule.target] = rule
        buildoutputs = self._gather_build_outputs()
        rule = self._create_build_rule(buildoutputs)
        self.rules[rule.target] = rule

        realpath_sources = []
        if self.args.filename:
            realpath_sources += sorted(compiletools.wrappedos.realpath(source) for source in self.args.filename)
        if self.args.tests:
            realpath_tests = sorted(compiletools.wrappedos.realpath(source) for source in self.args.tests)
            realpath_sources += realpath_tests

        if self.args.filename or self.args.tests:
            allexes = {self.namer.executable_pathname(source) for source in realpath_sources}
            for exe in allexes:
                cprule = self._create_cp_rule(exe)
                if cprule:
                    self.rules[cprule.target] = cprule

            link_rules = self._create_link_rules_for_sources(realpath_sources, exe_static_dynamic="Exe")
            for rule in link_rules:
                self.rules[rule.target] = rule

        if self.args.tests:
            test_rules = self._create_test_rules(realpath_tests)
            for rule in test_rules:
                self.rules[rule.target] = rule
            if self.args.serialisetests:
                rule = self._create_tests_not_parallel_rule()
                self.rules[rule.target] = rule

        if self.args.static:
            libraryname = self.namer.staticlibrary_pathname(compiletools.wrappedos.realpath(self.args.static[0]))
            cprule = self._create_cp_rule(libraryname)
            if cprule:
                self.rules[cprule.target] = cprule
            realpath_static = {compiletools.wrappedos.realpath(filename) for filename in self.args.static}
            static_rules = self._create_link_rules_for_sources(
                realpath_static,
                exe_static_dynamic="StaticLibrary",
                libraryname=libraryname,
            )
            for rule in static_rules:
                self.rules[rule.target] = rule

        if self.args.dynamic:
            libraryname = self.namer.dynamiclibrary_pathname(compiletools.wrappedos.realpath(self.args.dynamic[0]))
            cprule = self._create_cp_rule(libraryname)
            if cprule:
                self.rules[cprule.target] = cprule
            realpath_dynamic = {compiletools.wrappedos.realpath(filename) for filename in self.args.dynamic}
            dynamic_rules = self._create_link_rules_for_sources(
                realpath_dynamic,
                exe_static_dynamic="DynamicLibrary",
                libraryname=libraryname,
            )
            for rule in dynamic_rules:
                self.rules[rule.target] = rule

        if self.args.filename or self.args.tests:
            compile_rules = self._create_compile_rules_for_sources(realpath_sources)
            for rule in compile_rules:
                self.rules[rule.target] = rule
        if self.args.static and realpath_static:
            static_compile_rules = self._create_compile_rules_for_sources(realpath_static)
            for rule in static_compile_rules:
                self.rules[rule.target] = rule
        if self.args.dynamic and realpath_dynamic:
            dynamic_compile_rules = self._create_compile_rules_for_sources(realpath_dynamic)
            for rule in dynamic_compile_rules:
                self.rules[rule.target] = rule

        clean_rules = self._create_clean_rules(buildoutputs)
        for rule in clean_rules:
            self.rules[rule.target] = rule

        if self.args.build_only_changed:
            changed_files = set(self.args.build_only_changed.split(" "))
            targets = set()
            done = False
            while not done:
                done = True
                for rule in self.rules.values():
                    if rule.target in targets:
                        continue
                    relevant_changed_files = set(rule.prerequisites.split(" ")).intersection(changed_files)
                    if not relevant_changed_files:
                        continue
                    changed_files.add(rule.target)
                    targets.add(rule.target)
                    done = False
                    if self.args.verbose >= 3:
                        print(
                            "Building {} because it depends on changed: {}".format(
                                rule.target, list(relevant_changed_files)
                            )
                        )
            new_rules = {}
            for rule in self.rules.values():
                if not rule.phony:
                    new_rules[rule.target] = rule
                else:
                    rule.prerequisites = " ".join(set(rule.prerequisites.split()).intersection(targets))
                    new_rules[rule.target] = rule
            self.rules = new_rules

        self.write(self.args.makefilename)
        return self.args.makefilename

    def _create_object_directory(self):
        return Rule(
            target=self.args.objdir,
            prerequisites="",
            recipe=" ".join(["mkdir -p", self.args.objdir]),
        )

    def _create_compile_rule_for_source(self, filename):
        """For a given source file return the compile rule required for the Makefile"""
        if self.args.verbose >= 9:
            print("MakefileCreator::_create_compile_rule_for_source" + filename)

        if compiletools.utils.isheader(filename):
            sys.stderr.write("Error.  Trying to create a compile rule for a header file: ", filename)

        deplist = self.hunter.header_dependencies(filename)
        prerequisites = [filename] + sorted([str(dep) for dep in deplist])

        self.object_directories.add(self.namer.object_dir(filename))
        obj_name = self.namer.object_pathname(filename)
        self.objects.add(obj_name)

        magicflags = self.hunter.magicflags(filename)
        recipe = ""
        
        # Add timing wrapper if enabled
        timing_prefix = ""
        timing_suffix = ""
        if hasattr(self.args, 'time') and self.args.time and self.args.verbose >= 1:
            # Simple timing with elapsed time display
            timing_prefix = "@START=$$(date +%s%N); "
            timing_suffix = f"; END=$$(date +%s%N); echo \"... {filename} ($$(( ($$END-$$START)/1000000 ))ms)\""
        
        if self.args.verbose >= 1 and not (hasattr(self.args, 'time') and self.args.time):
            recipe = " ".join(["@echo ...", filename, ";"])
        
        magic_cpp_flags = magicflags.get("CPPFLAGS", [])
        compile_cmd = ""
        if compiletools.wrappedos.isc(filename):
            magic_c_flags = magicflags.get("CFLAGS", [])
            compile_flags = [self.args.CC, self.args.CFLAGS] + list(magic_cpp_flags) + list(magic_c_flags)
            if hasattr(self.args, 'time') and self.args.time and self.args.verbose >= 3:
                compile_flags.append("-time")
            compile_cmd = " ".join(compile_flags + ["-c", "-o", obj_name, filename])
        else:
            magic_cxx_flags = magicflags.get("CXXFLAGS", [])
            compile_flags = [self.args.CXX, self.args.CXXFLAGS] + list(magic_cpp_flags) + list(magic_cxx_flags)
            if hasattr(self.args, 'time') and self.args.time and self.args.verbose >= 3:
                compile_flags.append("-time")
            compile_cmd = " ".join(compile_flags + ["-c", "-o", obj_name, filename])
        
        recipe += timing_prefix + compile_cmd + timing_suffix

        if self.args.verbose >= 3:
            print("Creating rule for ", obj_name)

        # The order_only_prerequisite is to create the object directory
        return Rule(
            target=obj_name,
            prerequisites=" ".join(prerequisites),
            order_only_prerequisites=self.args.objdir,
            recipe=recipe,
        )

    def _create_link_rules_for_sources(self, sources, exe_static_dynamic, libraryname=None):
        """For all the given source files return the set of rules required
        for the Makefile that will _link_ the source files into executables.
        """

        # The set of rules needed to turn the source file into an executable
        # (or library as appropriate)
        rules_for_source = {}

        # Output all the link rules
        if self.args.verbose >= 3:
            print("Creating link rule for ", sources)
        linkrulecreatorclass = globals()[exe_static_dynamic + "LinkRuleCreator"]
        linkrulecreatorobject = linkrulecreatorclass(args=self.args, namer=self.namer, hunter=self.hunter)
        link_rules = linkrulecreatorobject(libraryname=libraryname, sources=sources)
        for rule in link_rules:
            rules_for_source[rule.target] = rule

        return list(rules_for_source.values())

    def _create_compile_rules_for_sources(self, sources):
        """For all the given source files return the set of rules required
        for the Makefile that will compile the source files into object files.
        """

        # The set of rules needed to turn the source file into an executable
        # (or library as appropriate)
        rules_for_source = {}
        rule = self._create_object_directory()
        rules_for_source[rule.target] = rule

        # Output all the compile rules
        for source in sources:
            # Reset the cycle detection because we are starting a new source
            # file
            cycle_detection = set()
            completesources = self.hunter.required_source_files(source)
            for item in completesources:
                if item not in cycle_detection:
                    cycle_detection.add(item)
                    rule = self._create_compile_rule_for_source(item)
                    rules_for_source[rule.target] = rule
                else:
                    print("ct-create-makefile detected cycle on source " + item)

        return list(rules_for_source.values())

    def write(self, makefile_name="Makefile"):
        """Take a list of rules and write the rules to a Makefile"""
        with open(makefile_name, mode="w", encoding="utf-8") as mfile:
            mfile.write("# Makefile generated by ")
            mfile.write(str(self.args))
            mfile.write("\n")
            for rule in self.rules.values():
                rule.write(mfile)

    def clear_cache(self):
        """Only useful in test scenarios where you need to reset to a pristine state"""
        compiletools.wrappedos.clear_cache()
        compiletools.utils.clear_cache()
        compiletools.git_utils.clear_cache()
        self.namer.clear_cache()
        self.hunter.clear_cache()
        compiletools.magicflags.MagicFlagsBase.clear_cache()


def main(argv=None):
    cap = compiletools.apptools.create_parser(
        "Create a Makefile that will compile the given source file into an executable (or library)", argv=argv
    )
    MakefileCreator.add_arguments(cap)
    compiletools.hunter.add_arguments(cap)
    args = compiletools.apptools.parseargs(cap, argv)
    headerdeps = compiletools.headerdeps.create(args)
    magicparser = compiletools.magicflags.create(args, headerdeps)
    hunter = compiletools.hunter.Hunter(args, headerdeps, magicparser)
    makefile_creator = MakefileCreator(args, hunter)
    makefile_creator.create()

    # And clean up for the test cases where main is called more than once
    makefile_creator.clear_cache()
    return 0
