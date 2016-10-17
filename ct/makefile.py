# vim: set filetype=python:
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
from io import open

import configargparse

import ct.utils
import ct.wrappedos
import ct.apptools
import ct.headerdeps
import ct.magicflags
import ct.hunter
import ct.namer

class Rule:

    """ A rule is a target, prerequisites and optionally a recipe
        https://www.gnu.org/software/make/manual/html_node/Rule-Introduction.html#Rule-Introduction
        Example: myrule = Rule( target='mytarget'
                              , prerequisites='file1.hpp file2.hpp'
                              , recipe='g++ -c mytarget.cpp -o mytarget.o'
                              )
        Note: it had to be a class rather than a dict so that we could hash it.
    """

    def __init__(self, target, prerequisites, recipe=None, phony=False):
        self.target = target
        self.prerequisites = prerequisites
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
        """ Write the given rule into the given Makefile."""
        if self.phony:
            makefile.write(" ".join([".PHONY:", self.target, "\n"]))

        makefile.write(self.target + ": " + self.prerequisites + "\n")
        try:
            makefile.write("\t" + self.recipe + "\n")
        except TypeError:
            pass
        makefile.write("\n")


class LinkRuleCreator(object):

    """ Base class to provide common infrastructure for the creation of
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
            suppressmagicldflags=False):
        """ For a given source file (so usually the file with the main) and the
            set of complete sources (i.e., all the other source files + the original)
            return the link rule required for the Makefile
        """
        if extraprereqs is None:
            extraprereqs = []
        if linkerflags is None:
            linkerflags = ""

        allprerequisites = " ".join(extraprereqs)
        object_names = {
            self.namer.object_pathname(source) for source in completesources}
        allprerequisites += " "
        allprerequisites += " ".join(object_names)

        all_magic_ldflags = set()
        if not suppressmagicldflags:
            for source in completesources:
                magic_flags = self.hunter.magicflags(source)
                all_magic_ldflags |= magic_flags.get('LDFLAGS', set())
                all_magic_ldflags |= magic_flags.get(
                    'LINKFLAGS',
                    set())  # For backward compatibility with cake
        recipe = ""
        if self.args.verbose >= 1:
            recipe += " ".join(["@echo ...", outputname, ";"])
        recipe += " ".join(["mkdir -p", ct.wrappedos.dirname(outputname), ";", linker, linkerflags] +
                           ["-o", outputname] +
                           list(object_names) +
                           list(all_magic_ldflags))
        return Rule(target=outputname,
                    prerequisites=allprerequisites,
                    recipe=recipe)


class StaticLibraryLinkRuleCreator(LinkRuleCreator):

    def __call__(self, sources, libraryname):
        return {self._create_link_rule(
            outputname=libraryname,
            completesources=sources,
            linker="ar -src",
            suppressmagicldflags=True)}


class DynamicLibraryLinkRuleCreator(LinkRuleCreator):

    def __call__(self, sources, libraryname):
        return {self._create_link_rule(
            outputname=libraryname,
            completesources=sources,
            linker=self.args.LD,
            linkerflags=self.args.LDFLAGS + " -shared")}


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
            staticlibrarypathname = self.namer.staticlibrary_pathname(
                ct.wrappedos.realpath(self.args.static[0]))
            libname = os.path.join(self.namer.executable_dir(), os.path.basename(staticlibrarypathname))
            extraprereqs.append(libname)
        if self.args.dynamic:
            dynamiclibrarypathname = self.namer.dynamiclibrary_pathname(
                ct.wrappedos.realpath(self.args.dynamic[0]))
            libname = os.path.join(self.namer.executable_dir(), os.path.basename(dynamiclibrarypathname))
            extraprereqs.append(libname)

        linkrules = set()
        for source in sources:
            if self.args.verbose >= 4:
                print(
                    "ExeLinkRuleCreator. Asking hunter for required_source_files for source=",
                    source)
            completesources = self.hunter.required_source_files(source)
            if self.args.verbose >= 6:
                print(
                    "ExeLinkRuleCreator. Complete list of implied source files for " +
                    source +
                    ": " +
                    " ".join(
                        cs for cs in completesources))
            exename = self.namer.executable_pathname(
                ct.wrappedos.realpath(source))
            linkrules.add(self._create_link_rule(
                outputname=exename,
                completesources=completesources,
                linker=self.args.LD,
                linkerflags=linkerflags,
                extraprereqs=extraprereqs))

        return linkrules


class MakefileCreator:

    """ Create a Makefile based on the filename, --static and --dynamic
        command line options.
    """

    def __init__(self, args, hunter):
        self.args = args

        # Keep track of what build artifacts are created for easier cleanup
        self.objects = set()
        self.object_directories = set()

        # By using a set, duplicate rules will be eliminated.
        # However, rules need to be written to disk in a specific order
        # so we use an OrderedSet
        self.rules = ct.utils.OrderedSet()

        self.namer = ct.namer.Namer(args)
        self.hunter = hunter

    @staticmethod
    def add_arguments(cap):
        ct.apptools.add_target_arguments_ex(cap)
        ct.apptools.add_link_arguments(cap)
        # Don't add the output directory arguments. Namer will do it.
        #ct.utils.add_output_directory_arguments(parser, variant)
        ct.namer.Namer.add_arguments(cap)
        ct.hunter.add_arguments(cap)
        cap.add(
            "--makefilename",
            default="Makefile",
            help="Output filename for the Makefile")

    def _uptodate(self):
        """ Is the Makefile up to date?
            If the argv has changed
            then regenerate on the assumption that the filelist or flags have changed
            else check if the modification time of the Makefile is greater than 
                 the modification times of all the source and header files.  
        """
        # Check if the Makefile exists and grab its modification time if it does exist.
        try:
            makefilemtime = ct.wrappedos.getmtime(self.args.makefilename)
        except OSError:
            # If the Makefile doesn't exist then we aren't up to date
            if self.args.verbose > 7:
                print("Could not determine mtime for {}. Assuming that it doesn't exist.".format(self.args.makefilename))
            return False

        # See how the Makefile was previously generated
        expected = ' '.join(["# Makefile generated by"]+sys.argv)
        with open(self.args.makefilename, mode='r', encoding='utf-8') as mfile:
            previous = mfile.readline().strip()
            if previous != expected:
                if self.args.verbose > 7:
                    print('Regenerating Makefile.')
                    print('Previous generation line was "{}".'.format(previous))
                    print('Current  generation line  is "{}".'.format(expected))
                return False

        # Check the mod times of all the implied files against the mod time of the Makefile
        for sf in self._gather_root_sources():
            filelist = self.hunter.required_files(sf)
            for ff in filelist:
                if ct.wrappedos.getmtime(ff) > makefilemtime:
                    if self.args.verbose > 7:
                        print("mtime for {} is newer than mtime for the Makefile".format(ct.wrappedos.getmtime(ff))) 
                    return False
        
        if self.args.verbose > 9:
            print("Makefile is up to date.  Not recreating.")

        return True

    def _create_all_rule(self):
        """ Create the rule that in depends on all build products """
        prerequisites = ['build']
        if self.args.tests:
            prerequisites.append('runtests')

        return Rule(
            target="all",
            prerequisites=" ".join(prerequisites),
            phony=True)

    @staticmethod
    def _create_build_rule(prerequisites):
        """ Create the rule that in depends on all build products """
        return Rule(
            target="build",
            prerequisites=" ".join(prerequisites),
            phony=True)

    def _create_clean_rules(self, alloutputs):
        rules = set()

        # Clean will only remove empty directories
        # Use realclean if you want force directories to be removed.
        rmcopiedexes = " ".join(["find",
                                 self.namer.executable_dir(),
                                 '-type f -executable -delete 2>/dev/null'])
        rmtargetsandobjects = " ".join(
            ["rm -f"] +
            list(alloutputs) +
            list(
                self.objects))
        rmemptydirs = " ".join(
            ["find", self.namer.object_dir(), "-type d -empty -delete"])
        recipe = ";".join([rmcopiedexes, rmtargetsandobjects, rmemptydirs])

        if self.namer.executable_dir() != self.namer.object_dir():
            recipe += " ".join([";find",
                                self.namer.executable_dir(),
                                "-type d -empty -delete"])

        rule_clean = Rule(
            target="clean",
            prerequisites="",
            recipe=recipe,
            phony=True)
        rules.add(rule_clean)

        # Now for realclean.  Just take a heavy handed rm -rf approach.
        # Note this will even remove the Makefile generated by ct-cake
        recipe = " ".join(["rm -rf", self.namer.executable_dir()])
        if self.namer.executable_dir() != self.namer.object_dir():
            recipe += "; rm -rf " + self.namer.object_dir()
        rule_realclean = Rule(target="realclean",
                              prerequisites="",
                              recipe=recipe,
                              phony=True)
        rules.add(rule_realclean)

        return rules

    def _create_cp_rule(self, output):
        """ Given the original output, copy it to the executable_dir() """
        if self.namer.executable_dir() == ct.wrappedos.dirname(output):
            return None

        return Rule(
            target=os.path.join(self.namer.executable_dir(), os.path.basename(output)),
            prerequisites=output,
            recipe=" ".join(["cp", 
                             output, 
                             self.namer.executable_dir(), 
                             "2>/dev/null ||true"]))

    def _create_test_rules(self, alltestsources):
        testprefix = ""
        if self.args.TESTPREFIX:
            testprefix = self.args.TESTPREFIX

        rules = set()

        # Create the PHONY that will run all the tests
        prerequisites = " ".join(
            [".".join([self.namer.executable_pathname(tt), "result"]) for tt in alltestsources])
        runtestsrule = Rule(
            target="runtests",
            prerequisites=prerequisites,
            phony=True)
        rules.add(runtestsrule)

        # Create a rule for each individual test
        for tt in alltestsources:
            exename = self.namer.executable_pathname(tt)
            testresult = ".".join([exename, "result"])

            recipe = ""
            if self.args.verbose >= 1:
                recipe += " ".join(["@echo ...", exename, ";"])
            recipe += " ".join(["rm -f",
                               testresult,
                               "&&",
                               testprefix,
                               exename,
                               "&& touch",
                               testresult])
            rules.add(Rule(
                target=testresult,
                prerequisites=exename,
                recipe=recipe))
        return rules

    def _gather_root_sources(self):
        """ Gather all the source files listed on the command line 
            into one uber set 
        """
        sources = set()
        if self.args.static:
            sources.update(self.args.static)
        if self.args.dynamic:
            sources.update(self.args.dynamic)
        if self.args.filename:
            sources.update(self.args.filename)
        if self.args.tests:
            sources.update(self.args.tests)

        return sources

    def _gather_build_outputs(self):
        """ Gathers together object files and other outputs """
        buildoutputs = set()

        if self.args.static:
            staticlibrarypathname = self.namer.staticlibrary_pathname()
            buildoutputs.add(staticlibrarypathname)
            buildoutputs.add(os.path.join(self.namer.executable_dir(), os.path.basename(staticlibrarypathname))) 

        if self.args.dynamic:
            dynamiclibrarypathname = self.namer.dynamiclibrary_pathname()
            buildoutputs.add(dynamiclibrarypathname)
            buildoutputs.add(os.path.join(self.namer.executable_dir(), os.path.basename(dynamiclibrarypathname))) 

        buildoutputs |= self.namer.all_executable_pathnames()
        if self.args.filename:
            allcopiedexes = { os.path.join(self.namer.executable_dir(), 
                                           self.namer.executable_name(source)) 
                              for source in self.args.filename}
            buildoutputs |= allcopiedexes

        buildoutputs |= self.namer.all_test_pathnames()

        return buildoutputs


    def create(self):
        if self._uptodate():
            return

        # Find the realpaths of the given filenames (to avoid this being
        # duplicated many times)
        ct.wrappedos.makedirs(self.namer.executable_dir())        
        self.rules.add(self._create_all_rule())
        buildoutputs = self._gather_build_outputs()
        self.rules.add(self._create_build_rule(buildoutputs))

        realpath_sources = []
        if self.args.filename:
            realpath_sources += sorted(
                ct.wrappedos.realpath(source) for source in self.args.filename)
        if self.args.tests:
            realpath_tests = sorted(
                ct.wrappedos.realpath(source) for source in self.args.tests)
            realpath_sources += realpath_tests

        if self.args.filename or self.args.tests:
            allexes = {
                self.namer.executable_pathname(source) for source in realpath_sources}
            for exe in allexes:
                cprule = self._create_cp_rule(exe) 
                if cprule:
                    self.rules.add(cprule)

            self.rules |= self._create_link_rules_for_sources(
                realpath_sources,
                exe_static_dynamic='Exe')

        if self.args.tests:
            self.rules |= self._create_test_rules(realpath_tests)

        if self.args.static:
            libraryname = self.namer.staticlibrary_pathname(
                ct.wrappedos.realpath(self.args.static[0]))
            cprule = self._create_cp_rule(libraryname)
            if cprule:
                self.rules.add(self._create_cp_rule(libraryname))
            realpath_static = {
                ct.wrappedos.realpath(filename) for filename in self.args.static}
            self.rules |= self._create_link_rules_for_sources(
                realpath_static,
                exe_static_dynamic='StaticLibrary',
                libraryname=libraryname)

        if self.args.dynamic:
            libraryname = self.namer.dynamiclibrary_pathname(
                ct.wrappedos.realpath(self.args.dynamic[0]))
            cprule = self._create_cp_rule(libraryname)
            if cprule:
                self.rules.add(cprule)
            realpath_dynamic = {
                ct.wrappedos.realpath(filename) for filename in self.args.dynamic}
            self.rules |= self._create_link_rules_for_sources(
                realpath_dynamic,
                exe_static_dynamic='DynamicLibrary',
                libraryname=libraryname)

        if self.args.filename or self.args.tests:
            self.rules |= self._create_compile_rules_for_sources(realpath_sources)
        if self.args.static and realpath_static:
            self.rules |= self._create_compile_rules_for_sources(realpath_static)
        if self.args.dynamic and realpath_dynamic:
            self.rules |= self._create_compile_rules_for_sources(realpath_dynamic)

        self.rules |= self._create_clean_rules(buildoutputs)

        self.write(self.args.makefilename)
        return self.args.makefilename

    def _create_compile_rule_for_source(self, filename):
        """ For a given source file return the compile rule required for the Makefile """
        if self.args.verbose >=9:
            print("MakefileCreator::_create_compile_rule_for_source" + filename)

        if ct.utils.isheader(filename):
            sys.stderr.write(
                "Error.  Trying to create a compile rule for a header file: ",
                filename)

        deplist = self.hunter.header_dependencies(filename)
        prerequisites = [filename] + sorted([str(dep) for dep in deplist])

        self.object_directories.add(self.namer.object_dir(filename))
        obj_name = self.namer.object_pathname(filename)
        self.objects.add(obj_name)

        magicflags = self.hunter.magicflags(filename)
        recipe = ""
        if self.args.verbose >= 1:
            recipe = " ".join(["@echo ...", filename, ";"])
        if ct.wrappedos.isc(filename):
            magic_c_flags = magicflags.get('CFLAGS', [])
            recipe += " ".join(["mkdir -p", ct.wrappedos.dirname(obj_name),";", self.args.CC, self.args.CFLAGS]
                              + list(magic_c_flags)
                              + ["-c", "-o", obj_name, filename])
        else:
            magic_cxx_flags = magicflags.get('CXXFLAGS', [])
            recipe += " ".join(["mkdir -p", ct.wrappedos.dirname(obj_name),";", self.args.CXX, self.args.CXXFLAGS]
                              + list(magic_cxx_flags)
                              + ["-c", "-o", obj_name, filename])

        if self.args.verbose >= 3:
            print("Creating rule for ", obj_name)

        return Rule(target=obj_name,
                    prerequisites=" ".join(prerequisites),
                    recipe=recipe)

    def _create_link_rules_for_sources(
            self,
            sources,
            exe_static_dynamic,
            libraryname=None):
        """ For all the given source files return the set of rules required
            for the Makefile that will _link_ the source files into executables.
        """

        # The set of rules needed to turn the source file into an executable
        # (or library as appropriate)
        rules_for_source = ct.utils.OrderedSet()

        # Output all the link rules
        if self.args.verbose >= 3:
            print("Creating link rule for ", sources)
        linkrulecreatorclass = globals()[
            exe_static_dynamic +
            'LinkRuleCreator']
        linkrulecreatorobject = linkrulecreatorclass(
            args=self.args,
            namer=self.namer,
            hunter=self.hunter)
        rules_for_source |= linkrulecreatorobject(
            libraryname=libraryname,
            sources=sources)

        return rules_for_source

    def _create_compile_rules_for_sources(self, sources):
        """ For all the given source files return the set of rules required
            for the Makefile that will compil the source files into object files.
        """

        # The set of rules needed to turn the source file into an executable
        # (or library as appropriate)
        rules_for_source = ct.utils.OrderedSet()

        # Output all the compile rules
        for source in sources:
            # Reset the cycle detection because we are starting a new source
            # file
            cycle_detection = set()
            completesources = self.hunter.required_source_files(source)
            for item in completesources:
                if item not in cycle_detection:
                    cycle_detection.add(item)
                    rules_for_source.add(
                        self._create_compile_rule_for_source(item))
                else:
                    print(
                        "ct-create-makefile detected cycle on source " +
                        item)

        return rules_for_source

    def write(self, makefile_name='Makefile'):
        """ Take a list of rules and write the rules to a Makefile """
        with open(makefile_name, mode='w', encoding='utf-8') as mfile:
            mfile.write("# Makefile generated by ")
            mfile.write(' '.join(sys.argv))
            mfile.write("\n")
            for rule in self.rules:
                rule.write(mfile)


def main(argv=None):
    cap = configargparse.getArgumentParser()
    MakefileCreator.add_arguments(cap)
    ct.hunter.add_arguments(cap)
    args = ct.apptools.parseargs(cap, argv)
    headerdeps = ct.headerdeps.create(args)
    magicparser = ct.magicflags.create(args, headerdeps)
    hunter = ct.hunter.Hunter(args, headerdeps, magicparser)
    makefile_creator = MakefileCreator(args, hunter)
    makefile_creator.create()
    return 0
