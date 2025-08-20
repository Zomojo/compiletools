import os
import re
from io import open
import functools

# At deep verbose levels pprint is used
from pprint import pprint

import compiletools.wrappedos
import compiletools.apptools
import compiletools.tree as tree
import compiletools.preprocessor
import compiletools.compiler_macros
from compiletools.simple_preprocessor import SimplePreprocessor
from compiletools.file_analyzer import create_file_analyzer
import compiletools.timing



def create(args):
    """HeaderDeps Factory"""
    classname = args.headerdeps.title() + "HeaderDeps"
    if args.verbose >= 4:
        print("Creating " + classname + " to process header dependencies.")
    depsclass = globals()[classname]
    depsobject = depsclass(args)
    return depsobject


def add_arguments(cap):
    """Add the command line arguments that the HeaderDeps classes require"""
    compiletools.apptools.add_common_arguments(cap)
    alldepscls = [st[:-10].lower() for st in dict(globals()) if st.endswith("HeaderDeps")]
    cap.add(
        "--headerdeps",
        choices=alldepscls,
        default="direct",
        help="Methodology for determining header dependencies",
    )
    cap.add(
        "--max-file-read-size",
        type=int,
        default=0,
        help="Maximum bytes to read from files (0 = entire file)",
    )


class HeaderDepsBase(object):
    """Implement the common functionality of the different header
    searching classes.  This really should be an abstract base class.
    """

    def __init__(self, args):
        self.args = args

    def _process_impl(self, realpath):
        """Derived classes implement this function"""
        raise NotImplemented

    def process(self, filename):
        """Return the set of dependencies for a given filename"""
        realpath = compiletools.wrappedos.realpath(filename)
        with compiletools.timing.time_operation(f"header_dependency_analysis_{os.path.basename(filename)}"):
            try:
                result = self._process_impl(realpath)
            except IOError:
                # If there was any error the first time around, an error correcting removal would have occured
                # So strangely, the best thing to do is simply try again
                result = None

            if not result:
                result = self._process_impl(realpath)

        return result

    @staticmethod
    def clear_cache():
        # print("HeaderDepsBase::clear_cache")
        DirectHeaderDeps.clear_cache()
        CppHeaderDeps.clear_cache()


class DirectHeaderDeps(HeaderDepsBase):
    """Create a tree structure that shows the header include tree"""

    def __init__(self, args):
        HeaderDepsBase.__init__(self, args)

        # Keep track of ancestor paths so that we can do header cycle detection
        self.ancestor_paths = []

        # Grab the include paths from the CPPFLAGS
        # By default, exclude system paths
        # TODO: include system paths if the user sets (the currently nonexistent) "use-system" flag
        #pat = re.compile(r"-(?:I|isystem)\s+([\S]+)")
        pat = re.compile(r"-(?:I)\s+([\S]+)")
        self.includes = pat.findall(self.args.CPPFLAGS)

        if self.args.verbose >= 3:
            print("Includes=" + str(self.includes))
            
        # Track defined macros during processing - use dict to store name-value pairs
        self.defined_macros = {}
        
        # Extract -D macro definitions from CPPFLAGS, CFLAGS, and CXXFLAGS
        define_pat = re.compile(r"-D([\S]+)")
        flag_sources = [
            ('CPPFLAGS', getattr(self.args, 'CPPFLAGS', '')),
            ('CFLAGS', getattr(self.args, 'CFLAGS', '')), 
            ('CXXFLAGS', getattr(self.args, 'CXXFLAGS', ''))
        ]
        
        for flag_name, flag_value in flag_sources:
            if flag_value:  # Only process if flag_value is not empty
                # Handle both string and list types for flag_value
                if isinstance(flag_value, list):
                    flag_string = ' '.join(flag_value)
                else:
                    flag_string = flag_value
                    
                flag_macros = define_pat.findall(flag_string)
                for macro in flag_macros:
                    # Handle -DMACRO=value by splitting on first = to get name and value
                    if '=' in macro:
                        macro_name, macro_value = macro.split('=', 1)
                    else:
                        macro_name = macro
                        macro_value = "1"  # Default value for macros without explicit values
                    self.defined_macros[macro_name] = macro_value
                    if self.args.verbose >= 3:
                        print(f"Added macro from {flag_name}: {macro_name} = {macro_value}")
        
        # Get compiler, platform, and architecture macros dynamically
        compiler = getattr(self.args, 'CXX', 'g++')
        macros = compiletools.compiler_macros.get_compiler_macros(compiler, self.args.verbose)
        self.defined_macros.update(macros)

    @functools.lru_cache(maxsize=None)
    def _search_project_includes(self, include):
        """Internal use.  Find the given include file in the project include paths"""
        for inc_dir in self.includes:
            trialpath = os.path.join(inc_dir, include)
            if compiletools.wrappedos.isfile(trialpath):
                return compiletools.wrappedos.realpath(trialpath)

        # else:
        #    TODO: Try system include paths if the user sets (the currently nonexistent) "use-system" flag
        #    Only get here if the include file cannot be found anywhere
        #    raise FileNotFoundError("DirectHeaderDeps could not determine the location of ",include)
        return None

    @functools.lru_cache(maxsize=None)
    def _find_include(self, include, cwd):
        """Internal use.  Find the given include file.
        Start at the current working directory then try the project includes
        """
        # Check if the file is referable from the current working directory
        # if that guess doesn't exist then try all the include paths
        trialpath = os.path.join(cwd, include)
        if compiletools.wrappedos.isfile(trialpath):
            return compiletools.wrappedos.realpath(trialpath)
        else:
            return self._search_project_includes(include)

    def _process_conditional_compilation(self, text):
        """Process conditional compilation directives and return only active sections"""
        preprocessor = SimplePreprocessor(self.defined_macros, self.args.verbose)
        processed_text = preprocessor.process(text)
        
        # Update our defined_macros dict with any changes from the preprocessor
        self.defined_macros.clear()
        self.defined_macros.update(preprocessor.macros)
        
        return processed_text

    def _create_include_list(self, realpath):
        """Internal use. Create the list of includes for the given file"""
        with compiletools.timing.time_operation(f"include_analysis_{os.path.basename(realpath)}"):
            max_read_size = getattr(self.args, 'max_file_read_size', 0)
            
            # Use FileAnalyzer for efficient file reading and pattern detection  
            # Note: create_file_analyzer() handles StringZilla/Legacy fallback internally
            from compiletools.file_analyzer import create_file_analyzer
            with compiletools.timing.time_operation(f"file_read_{os.path.basename(realpath)}"):
                analyzer = create_file_analyzer(realpath, max_read_size, self.args.verbose)
                analysis_result = analyzer.analyze()
                text = analysis_result.text

            # Process conditional compilation - this updates self.defined_macros as it encounters #define
            with compiletools.timing.time_operation(f"conditional_compilation_{os.path.basename(realpath)}"):
                processed_text = self._process_conditional_compilation(text)

            # The pattern is intended to match all include statements but
            # not the ones with either C or C++ commented out.
            with compiletools.timing.time_operation(f"pattern_matching_{os.path.basename(realpath)}"):
                pat = re.compile(
                    r'/\*.*?\*/|//.*?$|^[\s]*#include[\s]*["<][\s]*([\S]*)[\s]*[">]',
                    re.MULTILINE | re.DOTALL,
                )
                return [group for group in pat.findall(processed_text) if group]

    def _generate_tree_impl(self, realpath, node=None):
        """Return a tree that describes the header includes
        The node is passed recursively, however the original caller
        does not need to pass it in.
        """

        if self.args.verbose >= 4:
            print("DirectHeaderDeps::_generate_tree_impl: ", realpath)

        if node is None:
            node = tree.tree()

        # Stop cycles
        if realpath in self.ancestor_paths:
            if self.args.verbose >= 7:
                print(
                    "DirectHeaderDeps::_generate_tree_impl is breaking the cycle on ",
                    realpath,
                )
            return node
        self.ancestor_paths.append(realpath)

        # This next line is how you create the node in the tree
        node[realpath]

        if self.args.verbose >= 6:
            print("DirectHeaderDeps inserted: " + realpath)
            pprint(tree.dicts(node))

        cwd = os.path.dirname(realpath)
        for include in self._create_include_list(realpath):
            trialpath = self._find_include(include, cwd)
            if trialpath:
                self._generate_tree_impl(trialpath, node[realpath])
                if self.args.verbose >= 5:
                    print("DirectHeaderDeps building tree: ")
                    pprint(tree.dicts(node))

        self.ancestor_paths.pop()
        return node

    def generatetree(self, filename):
        """Returns the tree of include files"""
        self.ancestor_paths = []
        realpath = compiletools.wrappedos.realpath(filename)
        return self._generate_tree_impl(realpath)

    def _process_impl_recursive(self, realpath, results):
        results.add(realpath)
        cwd = compiletools.wrappedos.dirname(realpath)
        for include in self._create_include_list(realpath):
            trialpath = self._find_include(include, cwd)
            if trialpath and trialpath not in results:
                if self.args.verbose >= 9:
                    print(
                        "DirectHeaderDeps::_process_impl_recursive about to follow ",
                        trialpath,
                    )
                self._process_impl_recursive(trialpath, results)

    # TODO: Stop writing to the same cache as CPPHeaderDeps.
    # Because the magic flags rely on the .deps cache, this hack was put in
    # place.
    # NOTE: Cache removed due to macro state dependency - cache was keyed only on file path
    # but results depend on self.defined_macros which can change between calls
    def _process_impl(self, realpath):
        if self.args.verbose >= 9:
            print("DirectHeaderDeps::_process_impl: " + realpath)

        results = set()
        self._process_impl_recursive(realpath, results)
        results.discard(realpath)
        return results


    @staticmethod
    def clear_cache():
        # print("DirectHeaderDeps::clear_cache")
        DirectHeaderDeps._search_project_includes.cache_clear()
        DirectHeaderDeps._find_include.cache_clear()


class CppHeaderDeps(HeaderDepsBase):
    """Using the C Pre Processor, create the list of headers that the given file depends upon."""

    def __init__(self, args):
        HeaderDepsBase.__init__(self, args)
        self.preprocessor = compiletools.preprocessor.PreProcessor(args)

    def _process_impl(self, realpath):
        """Use the -MM option to the compiler to generate the list of dependencies
        If you supply a header file rather than a source file then
        a dummy, blank, source file will be transparently provided
        and the supplied header file will be included into the dummy source file.
        """
        # By default, exclude system paths
        # TODO: include system paths if the user sets (the currently nonexistent) "use-system" flag
        regex = r"-isystem ([^\s]+)"  # Regex to find paths following -isystem
        system_paths = re.findall(regex, self.args.CPPFLAGS)
        system_paths = tuple(item for pth in system_paths for item in (pth, compiletools.wrappedos.realpath(pth)))
        if realpath.startswith(system_paths):
            return []

        output = self.preprocessor.process(realpath, extraargs="-MM")

        # output will be something like
        # test_direct_include.o: tests/test_direct_include.cpp
        # tests/get_numbers.hpp tests/get_double.hpp tests/get_int.hpp
        # We need to throw away the object file and only keep the dependency
        # list
        deplist = output.split(":")[1]

        # Strip non-space whitespace, remove any backslashes, and remove any empty strings
        # Also remove the initially given realpath and /dev/null from the list
        # Use a set to inherently remove any redundancies
        # Use realpath to get rid of  // and ../../ etc in paths (similar to normpath) and
        # to get the full path even to files in the current working directory
        return compiletools.utils.ordered_unique(
            [
                compiletools.wrappedos.realpath(x)
                for x in deplist.split()
                if x.strip("\\\t\n\r") and x not in [realpath, "/dev/null"] and not x.startswith(system_paths)
            ]
        )

    @staticmethod
    def clear_cache():
        # print("CppHeaderDeps::clear_cache")
        pass
