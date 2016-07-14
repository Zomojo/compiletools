# vim: set filetype=python:
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
from io import open

import configargparse

import ct.utils
import ct.wrappedos
from ct.hunter import Hunter


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


class MakefileCreator:

    """ Create a Makefile based on the filename, --static and --dynamic command line options """

    def __init__(self, parser, variant, argv=None):
        ct.utils.add_target_arguments(parser)
        ct.utils.add_link_arguments(parser)
        ct.utils.add_output_directory_arguments(parser, variant)

        # Keep track of what build artifacts are created for easier cleanup
        self.objects = set()
        self.object_directories = set()

        # By using a set, duplicate rules will be eliminated.
        # However, rules need to be written to disk in a specific order
        # so we use an OrderedSet
        self.rules = ct.utils.OrderedSet()

        self.args = None
        # self.args will exist after this call
        ct.utils.setattr_args(self, argv)

        self.namer = ct.utils.Namer(parser, variant, argv)
        self.hunter = Hunter(argv)

    @staticmethod
    def _create_all_rule(prerequisites):
        """ Create the rule that in depends on all build products """
        return Rule(
            target="all",
            prerequisites=" ".join(prerequisites),
            phony=True)

    def _create_mkdir_rule(self, alloutputs):
        outputdirs = [ct.wrappedos.dirname(output) for output in alloutputs]
        recipe = " ".join(
            ["mkdir -p"] +
            outputdirs +
            list(
                self.object_directories))
        return Rule(
            target="mkdir_output",
            prerequisites="",
            recipe=recipe,
            phony=True)

    def _create_clean_rules(self, alloutputs):
        rules = set()
        rmcopiedexes = " ".join(
            ["rm -f", os.path.join(self.namer.executable_dir(), '*'), " 2>/dev/null"])
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

        recipe = " ".join(["rm -rf", self.namer.executable_dir()])
        if self.namer.executable_dir() != self.namer.object_dir():
            recipe += "; rm -rf " + self.namer.object_dir()
        rule_realclean = Rule(target="realclean",
                              prerequisites="",
                              recipe=recipe,
                              phony=True)
        rules.add(rule_realclean)

        return rules

    def _create_cp_rule(self, static_dynamic_executables, prerequisites):
        return Rule(
            target="_".join(["cp", static_dynamic_executables]),
            prerequisites=prerequisites,
            recipe=" ".join(["cp", prerequisites, self.namer.executable_dir()]),
            phony=True)

    def create(self):
        # Find the realpaths of the given filenames (to avoid this being
        # duplicated many times)
        realpaths = list()
        all_outputs = set()
        all_prerequisites = ["mkdir_output"]

        if self.args.static:
            realpath_static = [ct.wrappedos.realpath(filename)
                               for filename in self.args.static]
            realpaths.extend(realpath_static)
            staticlibrarypathname = self.namer.staticlibrary_pathname(
                realpath_static[0])
            all_outputs.add(staticlibrarypathname)
            all_prerequisites.append("cp_static_library")

        if self.args.dynamic:
            realpath_dynamic = [ct.wrappedos.realpath(filename)
                                for filename in self.args.dynamic]
            realpaths.extend(realpath_dynamic)
            dynamiclibrarypathname = self.namer.dynamiclibrary_pathname(
                realpath_dynamic[0])
            all_outputs.add(dynamiclibrarypathname)
            all_prerequisites.append("cp_dynamic_library")

        if self.args.filename:
            realpath_sources = sorted([ct.wrappedos.realpath(filename)
                                       for filename in self.args.filename])
            realpaths.extend(realpath_sources)
            all_exes = {
                self.namer.executable_pathname(source) for source in realpath_sources}
            all_outputs |= all_exes
            all_prerequisites.append("cp_executables")

        all_prerequisites.extend(all_outputs)
        self.rules.add(self._create_all_rule(all_prerequisites))

        if self.args.filename:
            self.rules.add(
                self._create_cp_rule(
                    'executables',
                    " ".join(all_exes)))
            self.rules |= self._create_makefile_rules_for_sources(
                realpath_sources,
                exe_static_dynamic='exe')

        if self.args.static:
            self.rules.add(
                self._create_cp_rule(
                    'static_library',
                    staticlibrarypathname))
            self.rules |= self._create_makefile_rules_for_sources(
                realpath_static,
                exe_static_dynamic='static')

        if self.args.dynamic:
            self.rules.add(
                self._create_cp_rule(
                    'dynamic_library',
                    dynamiclibrarypathname))
            self.rules |= self._create_makefile_rules_for_sources(
                realpath_dynamic,
                exe_static_dynamic='dynamic')

        self.rules.add(self._create_mkdir_rule(all_outputs))
        self.rules |= self._create_clean_rules(all_outputs)

        self.write()

    def _create_compile_rule_for_source(self, filename):
        """ For a given source file return the compile rule required for the Makefile """
        deplist = self.hunter.header_dependencies(filename)
        prerequisites = [filename] + sorted([str(dep) for dep in deplist])

        self.object_directories.add(self.namer.object_dir(filename))
        obj_name = self.namer.object_pathname(filename)
        self.objects.add(obj_name)

        source = filename
        # If filename is actually a header then change source
        if ct.utils.isheader(source):
            source = ct.utils.implied_source(filename)
            # If the implied source doesn't exist then
            # use /dev/null as the dummy source file.
            if not source:
                source = " ".join(
                    ["-include", filename, "-x", "c++", "/dev/null"])

        magicflags = self.hunter.parse_magic_flags(filename)
        if ct.wrappedos.isc(filename):
            magic_c_flags = magicflags.get('CFLAGS', [])
            recipe = " ".join([self.args.CC, self.args.CFLAGS]
                              + list(magic_c_flags)
                              + ["-c", "-o", obj_name, source])
        else:
            magic_cxx_flags = magicflags.get('CXXFLAGS', [])
            recipe = " ".join([self.args.CXX, self.args.CXXFLAGS]
                              + list(magic_cxx_flags)
                              + ["-c", "-o", obj_name, source])
        if self.args.verbose >= 3:
            print("Creating rule for ", obj_name)

        return Rule(target=obj_name,
                    prerequisites=" ".join(prerequisites),
                    recipe=recipe)

    def _create_link_rule(
            self,
            outputname,
            completesources,
            linker,
            linkerflags,
            extraprereqs=None):
        """ For a given source file (so usually the file with the main) and the
            set of complete sources (i.e., all the other source files + the original)
            return the link rule required for the Makefile
        """
        if extraprereqs is None:
            extraprereqs = []

        allprerequisites = " ".join(extraprereqs)
        object_names = " ".join(
            self.namer.object_pathname(source) for source in completesources)
        allprerequisites += " "
        allprerequisites += object_names

        all_magic_ldflags = set()
        for source in completesources:
            magic_flags = self.hunter.parse_magic_flags(source)
            all_magic_ldflags |= magic_flags.get('LDFLAGS', set())
            all_magic_ldflags |= magic_flags.get(
                'LINKFLAGS',
                set())  # For backward compatibility with cake

        return Rule(target=outputname,
                    prerequisites=allprerequisites,
                    recipe=" ".join([linker,
                                     linkerflags] + ["-o",
                                                     outputname,
                                                     object_names] + list(all_magic_ldflags)))

    def _create_link_rule_exe(self, sourcefilename, completesources):
        exename = self.namer.executable_pathname(
            ct.wrappedos.realpath(sourcefilename))
        extraprereqs = []
        linkerflags = self.args.LDFLAGS

        # If there is also a library being built then automatically
        # include the path to that library to allow easy linking
        if self.args.static:
            extraprereqs.append("cp_static_library")
            linkerflags += " -L"
            linkerflags += self.namer.executable_dir()

        if self.args.dynamic:
            extraprereqs.append("cp_dynamic_library")
            linkerflags += " -L"
            linkerflags += self.namer.executable_dir()

        return self._create_link_rule(
            outputname=exename,
            completesources=completesources,
            linker=self.args.LD,
            linkerflags=linkerflags,
            extraprereqs=extraprereqs)

    def _create_link_rule_static_library(
            self,
            sourcefilename,
            completesources):
        outputname = self.namer.staticlibrary_pathname(
            ct.wrappedos.realpath(sourcefilename))
        return self._create_link_rule(
            outputname,
            completesources,
            "ar -src",
            "")

    def _create_link_rule_dynamic_library(
            self,
            sourcefilename,
            completesources):
        magicflags = self.hunter.parse_magic_flags(sourcefilename)
        magicflags.setdefault('LDFLAGS', set()).add('-shared')
        outputname = self.namer.dynamiclibrary_pathname(
            ct.wrappedos.realpath(sourcefilename))
        rule = self._create_link_rule(
            outputname,
            completesources,
            self.args.LD,
            self.args.LDFLAGS)
        magicflags.get('LDFLAGS').remove('-shared')
        return rule

    def _create_makefile_rules_for_sources(self, sources, exe_static_dynamic):
        """ For all the given source files return the set of rules required
            for the Makefile that will turn the source files into executables.
        """

        # The set of rules needed to turn the source file into an executable
        # (or library as appropriate)
        rules_for_source = ct.utils.OrderedSet()

        # Output all the link rules
        if self.args.verbose >= 3:
            print("Creating link rule for ", sources)
        if 'exe' in exe_static_dynamic:
            for source in sources:
                if self.args.verbose >= 4:
                    print(
                        "Asking hunter for required_source_files for source=",
                        source)
                completesources = self.hunter.required_source_files(source)
                if self.args.verbose >= 6:
                    print(
                        "Complete list of implied source files for " +
                        source +
                        ": " +
                        " ".join(
                            cs for cs in completesources))
                linkrules = self._create_link_rule_exe(source, completesources)
                rules_for_source.add(linkrules)
        elif 'static' in exe_static_dynamic:
            linkrules = self._create_link_rule_static_library(
                sources[0],
                sources)
            rules_for_source.add(linkrules)
        elif 'dynamic' in exe_static_dynamic:
            linkrules = self._create_link_rule_dynamic_library(
                sources[0],
                sources)
            rules_for_source.add(linkrules)
        else:
            raise Exception('Unknown exe_static_dynamic')

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
            mfile.write("# Makefile generated by ct-create-makefile\n")
            for rule in self.rules:
                rule.write(mfile)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    variant = ct.utils.extract_variant_from_argv(argv)
    cap = configargparse.getArgumentParser()
    makefile_creator = MakefileCreator(parser=cap, variant=variant, argv=argv)
    myargs = cap.parse_known_args(args=argv[1:])
    ct.utils.verbose_print_args(myargs[0])

    makefile_creator.create()
    return 0
