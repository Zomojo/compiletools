import os
import re
from io import open
import functools

# At deep verbose levels pprint is used
from pprint import pprint

import ct.wrappedos
import ct.apptools
import ct.tree as tree
import ct.preprocessor
from ct.diskcache import diskcache


class SimplePreprocessor:
    """A simple C preprocessor for handling conditional compilation directives"""
    
    def __init__(self, defined_macros, verbose=0):
        # Use a dict to store macro values, not just existence
        self.macros = {}
        # Initialize with existing defined macros
        if isinstance(defined_macros, dict):
            # defined_macros is already a dict of name->value
            self.macros.update(defined_macros)
        else:
            # Legacy compatibility: defined_macros is a set of names
            for macro in defined_macros:
                self.macros[macro] = "1"  # Default value for macros without explicit values
        self.verbose = verbose
        
    def process(self, text):
        """Process text and return only active sections"""
        lines = text.split('\n')
        result_lines = []
        
        # Stack to track conditional compilation state
        # Each entry: (is_active, seen_else, any_condition_met)
        condition_stack = [(True, False, False)]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Handle preprocessor directives
            if stripped.startswith('#'):
                # Handle multiline preprocessor directives
                full_directive = stripped
                line_continuation_count = 0
                while full_directive.rstrip().endswith('\\') and i + line_continuation_count + 1 < len(lines):
                    line_continuation_count += 1
                    next_line = lines[i + line_continuation_count].strip()
                    # Remove the trailing backslash and any trailing whitespace, then add the next line
                    full_directive = full_directive.rstrip().rstrip('\\').rstrip() + ' ' + next_line
                
                directive = self._parse_directive(full_directive)
                if directive:
                    handled = self._handle_directive(directive, condition_stack, i + 1)
                    # If directive wasn't handled (like #include), treat it as a regular line
                    if handled is False and condition_stack[-1][0]:
                        result_lines.append(line)
                        # Add continuation lines too if not handled
                        for j in range(line_continuation_count):
                            result_lines.append(lines[i + j + 1])
                # If no directive was parsed, treat as regular line
                elif condition_stack[-1][0]:
                    result_lines.append(line)
                    # Add continuation lines too
                    for j in range(line_continuation_count):
                        result_lines.append(lines[i + j + 1])
                
                # Skip the continuation lines we've already processed
                i += line_continuation_count + 1
            else:
                # Only include non-directive lines if we're in an active context
                if condition_stack[-1][0]:
                    result_lines.append(line)
                i += 1
        
        return '\n'.join(result_lines)
    
    def _parse_directive(self, line):
        """Parse a preprocessor directive line"""
        # Remove leading # and split into parts
        content = line[1:].strip()
        parts = content.split(None, 1)
        if not parts:
            return None
            
        directive_name = parts[0]
        directive_args = parts[1] if len(parts) > 1 else ""
        
        return {
            'name': directive_name,
            'args': directive_args,
            'raw': line
        }
    
    def _handle_directive(self, directive, condition_stack, line_num):
        """Handle a specific preprocessor directive"""
        name = directive['name']
        args = directive['args']
        
        if name == 'define':
            self._handle_define(args, condition_stack)
            return True
        elif name == 'undef':
            self._handle_undef(args, condition_stack)
            return True
        elif name == 'ifdef':
            self._handle_ifdef(args, condition_stack)
            return True
        elif name == 'ifndef':
            self._handle_ifndef(args, condition_stack)
            return True
        elif name == 'if':
            self._handle_if(args, condition_stack)
            return True
        elif name == 'elif':
            self._handle_elif(args, condition_stack)
            return True
        elif name == 'else':
            self._handle_else(condition_stack)
            return True
        elif name == 'endif':
            self._handle_endif(condition_stack)
            return True
        else:
            # Unknown directive - ignore but don't consume the line
            # This allows #include and other directives to be processed normally
            if self.verbose >= 8:
                print(f"SimplePreprocessor: Ignoring unknown directive #{name}")
            return False  # Indicate that this directive wasn't handled
    
    def _handle_define(self, args, condition_stack):
        """Handle #define directive"""
        if not condition_stack[-1][0]:
            return  # Not in active context
            
        parts = args.split(None, 1)
        if not parts:
            return
            
        macro_name = parts[0]
        macro_value = parts[1] if len(parts) > 1 else "1"
        
        # Handle function-like macros by extracting just the name part
        if '(' in macro_name:
            macro_name = macro_name.split('(')[0]
            
        self.macros[macro_name] = macro_value
        if self.verbose >= 9:
            print(f"SimplePreprocessor: defined macro {macro_name} = {macro_value}")
    
    def _handle_undef(self, args, condition_stack):
        """Handle #undef directive"""
        if not condition_stack[-1][0]:
            return  # Not in active context
            
        macro_name = args.strip()
        if macro_name in self.macros:
            del self.macros[macro_name]
            if self.verbose >= 9:
                print(f"SimplePreprocessor: undefined macro {macro_name}")
    
    def _handle_ifdef(self, args, condition_stack):
        """Handle #ifdef directive"""
        macro_name = args.strip()
        is_defined = macro_name in self.macros
        is_active = is_defined and condition_stack[-1][0]
        condition_stack.append((is_active, False, is_active))
        if self.verbose >= 9:
            print(f"SimplePreprocessor: #ifdef {macro_name} -> {is_defined}")
    
    def _handle_ifndef(self, args, condition_stack):
        """Handle #ifndef directive"""
        macro_name = args.strip()
        is_defined = macro_name in self.macros
        is_active = (not is_defined) and condition_stack[-1][0]
        condition_stack.append((is_active, False, is_active))
        if self.verbose >= 9:
            print(f"SimplePreprocessor: #ifndef {macro_name} -> {not is_defined}")
    
    def _handle_if(self, args, condition_stack):
        """Handle #if directive"""
        try:
            result = self._evaluate_expression(args.strip())
            is_active = bool(result) and condition_stack[-1][0]
            condition_stack.append((is_active, False, is_active))
            if self.verbose >= 9:
                print(f"SimplePreprocessor: #if {args} -> {result} ({is_active})")
        except Exception as e:
            # If evaluation fails, assume false
            if self.verbose >= 8:
                print(f"SimplePreprocessor: #if evaluation failed for '{args}': {e}")
            condition_stack.append((False, False, False))
    
    def _handle_elif(self, args, condition_stack):
        """Handle #elif directive"""
        if len(condition_stack) <= 1:
            return
            
        current_active, seen_else, any_condition_met = condition_stack.pop()
        if not seen_else and not any_condition_met:
            parent_active = condition_stack[-1][0] if condition_stack else True
            try:
                result = self._evaluate_expression(args.strip())
                new_active = bool(result) and parent_active
                new_any_condition_met = any_condition_met or new_active
                condition_stack.append((new_active, False, new_any_condition_met))
                if self.verbose >= 9:
                    print(f"SimplePreprocessor: #elif {args} -> {result} ({new_active})")
            except Exception as e:
                if self.verbose >= 8:
                    print(f"SimplePreprocessor: #elif evaluation failed for '{args}': {e}")
                condition_stack.append((False, False, any_condition_met))
        else:
            # Either we already found a true condition or seen_else is True
            condition_stack.append((False, seen_else, any_condition_met))
    
    def _handle_else(self, condition_stack):
        """Handle #else directive"""
        if len(condition_stack) <= 1:
            return
            
        current_active, seen_else, any_condition_met = condition_stack.pop()
        if not seen_else:
            parent_active = condition_stack[-1][0] if condition_stack else True
            new_active = not any_condition_met and parent_active
            condition_stack.append((new_active, True, any_condition_met or new_active))
            if self.verbose >= 9:
                print(f"SimplePreprocessor: #else -> {new_active}")
        else:
            condition_stack.append((False, True, any_condition_met))
    
    def _handle_endif(self, condition_stack):
        """Handle #endif directive"""
        if len(condition_stack) > 1:
            condition_stack.pop()
            if self.verbose >= 9:
                print("SimplePreprocessor: #endif")
    
    def _evaluate_expression(self, expr):
        """Evaluate a C preprocessor expression"""
        # This is a simplified expression evaluator
        # Handle common cases: defined(MACRO), numeric comparisons, logical operations
        
        expr = expr.strip()
        
        # Handle defined(MACRO) and defined MACRO
        expr = self._expand_defined(expr)
        
        # Replace macro names with their values
        expr = self._expand_macros(expr)
        
        # Evaluate the expression safely
        return self._safe_eval(expr)
    
    def _expand_defined(self, expr):
        """Expand defined(MACRO) expressions"""
        import re
        
        # Handle defined(MACRO)
        def replace_defined_paren(match):
            macro_name = match.group(1)
            return "1" if macro_name in self.macros else "0"
        
        expr = re.sub(r'defined\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)', replace_defined_paren, expr)
        
        # Handle defined MACRO (without parentheses)
        def replace_defined_space(match):
            macro_name = match.group(1)
            return "1" if macro_name in self.macros else "0"
        
        expr = re.sub(r'defined\s+([A-Za-z_][A-Za-z0-9_]*)', replace_defined_space, expr)
        
        return expr
    
    def _expand_macros(self, expr):
        """Replace macro names with their values"""
        import re
        
        def replace_macro(match):
            macro_name = match.group(0)
            if macro_name in self.macros:
                value = self.macros[macro_name]
                # Try to convert to int if possible
                try:
                    return str(int(value))
                except ValueError:
                    return value
            else:
                # Undefined macro defaults to 0
                return "0"
        
        # Replace macro names (identifiers) with their values
        # Use word boundaries to avoid replacing parts of numbers or other tokens
        expr = re.sub(r'(?<![0-9])\b[A-Za-z_][A-Za-z0-9_]*\b(?![0-9])', replace_macro, expr)
        
        return expr
    
    def _safe_eval(self, expr):
        """Safely evaluate a numeric expression"""
        # Clean up the expression
        expr = expr.strip()
        
        # Remove trailing backslashes from multiline directives and normalize whitespace
        import re
        # Remove backslashes followed by whitespace (multiline continuations)
        expr = re.sub(r'\\\s*', ' ', expr)
        # Remove any remaining trailing backslashes
        expr = expr.rstrip('\\').strip()
        
        # First clean up any malformed expressions from macro replacement
        # Fix cases like "0(0)" which occur when macros expand to adjacent numbers
        import re
        expr = re.sub(r'(\d+)\s*\(\s*(\d+)\s*\)', r'\1 * \2', expr)
        
        # Remove C-style integer suffixes (L, UL, LL, ULL, etc.)
        expr = re.sub(r'(\d+)[LlUu]+\b', r'\1', expr)
        
        # Convert C operators to Python equivalents
        # Handle comparison operators first (before replacing ! with not)
        # Use temporary placeholders to protect != from being affected by ! replacement
        expr = expr.replace('!=', '__NE__')  # Temporarily replace != with placeholder
        expr = expr.replace('>=', '__GE__')  # Also protect >= from > replacement
        expr = expr.replace('<=', '__LE__')  # Also protect <= from < replacement
        
        # Now handle logical operators (! is safe to replace now)
        expr = expr.replace('&&', ' and ')
        expr = expr.replace('||', ' or ')
        expr = expr.replace('!', ' not ')
        
        # Now restore comparison operators as Python equivalents
        expr = expr.replace('__NE__', '!=')
        expr = expr.replace('__GE__', '>=')
        expr = expr.replace('__LE__', '<=')
        # Note: ==, >, < are already correct for Python and need no conversion
        
        # Clean up any remaining whitespace issues
        expr = expr.strip()
        
        # Only allow safe characters and words
        if not re.match(r'^[0-9\s\+\-\*\/\%\(\)\<\>\=\!andortnot ]+$', expr):
            raise ValueError(f"Unsafe expression: {expr}")
        
        try:
            # Use eval with a restricted environment
            allowed_names = {"__builtins__": {}}
            result = eval(expr, allowed_names, {})
            return int(result) if isinstance(result, (int, bool)) else 0
        except Exception as e:
            # If evaluation fails, return 0
            if self.verbose >= 8:
                print(f"SimplePreprocessor: Expression evaluation failed for '{expr}': {e}")
            return 0


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
    ct.apptools.add_common_arguments(cap)
    alldepscls = [st[:-10].lower() for st in dict(globals()) if st.endswith("HeaderDeps")]
    cap.add(
        "--headerdeps",
        choices=alldepscls,
        default="direct",
        help="Methodology for determining header dependencies",
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
        realpath = ct.wrappedos.realpath(filename)
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
        diskcache.clear_cache()
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
                flag_macros = define_pat.findall(flag_value)
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
        
        # Add platform, compiler, and architecture built-in macros
        self._add_platform_macros()
        self._add_compiler_macros()
        self._add_architecture_macros()

    @functools.lru_cache(maxsize=None)
    def _search_project_includes(self, include):
        """Internal use.  Find the given include file in the project include paths"""
        for inc_dir in self.includes:
            trialpath = os.path.join(inc_dir, include)
            if ct.wrappedos.isfile(trialpath):
                return ct.wrappedos.realpath(trialpath)

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
        if ct.wrappedos.isfile(trialpath):
            return ct.wrappedos.realpath(trialpath)
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

    @functools.lru_cache(maxsize=None)
    def _create_include_list(self, realpath):
        """Internal use. Create the list of includes for the given file"""
        with open(realpath, encoding="utf-8", errors="ignore") as ff:
            # Assume that all includes occur at the top of the file
            text = ff.read(8192)

        # Process conditional compilation first
        processed_text = self._process_conditional_compilation(text)

        # The pattern is intended to match all include statements but
        # not the ones with either C or C++ commented out.
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
        realpath = ct.wrappedos.realpath(filename)
        return self._generate_tree_impl(realpath)

    def _process_impl_recursive(self, realpath, results):
        results.add(realpath)
        cwd = ct.wrappedos.dirname(realpath)
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
    @diskcache("deps", deps_mode=True)
    def _process_impl(self, realpath):
        if self.args.verbose >= 9:
            print("DirectHeaderDeps::_process_impl: " + realpath)

        results = set()
        self._process_impl_recursive(realpath, results)
        results.discard(realpath)
        return results

    def _add_platform_macros(self):
        """Add platform-specific built-in macros"""
        import sys
        if sys.platform.startswith('linux'):
            for macro in ['__linux__', '__unix__', 'unix']:
                self.defined_macros[macro] = "1"
        elif sys.platform.startswith('win'):
            for macro in ['_WIN32', 'WIN32']:
                self.defined_macros[macro] = "1"
        elif sys.platform.startswith('darwin'):
            for macro in ['__APPLE__', '__MACH__', '__unix__', 'unix']:
                self.defined_macros[macro] = "1"
            
        if self.args.verbose >= 3:
            print(f"Added platform macros for {sys.platform}")

    def _add_compiler_macros(self):
        """Add compiler-specific built-in macros"""
        compiler = getattr(self.args, 'CXX', 'g++').lower()
        
        if 'armcc' in compiler or 'armclang' in compiler:
            for macro in ['__ARMCC_VERSION', '__arm__']:
                self.defined_macros[macro] = "1"
            # ARM Compiler 6+ is based on clang
            if 'armclang' in compiler:
                for macro in ['__clang__', '__GNUC__']:
                    self.defined_macros[macro] = "1"
            if self.args.verbose >= 3:
                print("Added ARM compiler built-in macros")
                
        elif 'clang' in compiler:
            for macro in ['__clang__', '__clang_major__', '__clang_minor__', '__clang_patchlevel__',
                         '__GNUC__', '__GNUC_MINOR__']:  # Clang compatibility macros
                self.defined_macros[macro] = "1"
            if self.args.verbose >= 3:
                print("Added Clang compiler built-in macros")
                
        elif 'gcc' in compiler or 'g++' in compiler:
            for macro in ['__GNUC__', '__GNUG__', '__GNUC_MINOR__', '__GNUC_PATCHLEVEL__']:
                self.defined_macros[macro] = "1"
            if self.args.verbose >= 3:
                print("Added GCC compiler built-in macros")
                
        elif 'tcc' in compiler:
            for macro in ['__TINYC__', '__GNUC__']:  # TCC compatibility macros
                self.defined_macros[macro] = "1"
            if self.args.verbose >= 3:
                print("Added TCC compiler built-in macros")
                
        elif 'cl' in compiler or 'msvc' in compiler:
            for macro in ['_MSC_VER', '_MSC_FULL_VER', '_WIN32']:
                self.defined_macros[macro] = "1"
            if self.args.verbose >= 3:
                print("Added MSVC compiler built-in macros")
                
        elif 'icc' in compiler or 'icx' in compiler or 'intel' in compiler:
            for macro in ['__INTEL_COMPILER', '__ICC', '__GNUC__']:  # Intel + GCC compatibility
                self.defined_macros[macro] = "1"
            if self.args.verbose >= 3:
                print("Added Intel compiler built-in macros")
                
        elif 'emcc' in compiler or 'emscripten' in compiler:
            for macro in ['__EMSCRIPTEN__', '__clang__', '__GNUC__']:  # Emscripten is based on clang
                self.defined_macros[macro] = "1"
            if self.args.verbose >= 3:
                print("Added Emscripten compiler built-in macros")

    def _add_architecture_macros(self):
        """Add architecture-specific built-in macros"""
        import platform
        arch = platform.machine().lower()
        
        if arch in ['x86_64', 'amd64']:
            for macro in ['__x86_64__', '__amd64__', '__LP64__']:
                self.defined_macros[macro] = "1"
        elif arch in ['i386', 'i686', 'x86']:
            for macro in ['__i386__', '__i386']:
                self.defined_macros[macro] = "1"
        elif arch.startswith('arm'):
            self.defined_macros['__arm__'] = "1"
            if '64' in arch:
                for macro in ['__aarch64__', '__LP64__']:
                    self.defined_macros[macro] = "1"
        elif arch.startswith('riscv') or 'riscv' in arch:
            self.defined_macros['__riscv'] = "1"
            if '64' in arch:
                for macro in ['__riscv64__', '__LP64__']:
                    self.defined_macros[macro] = "1"
            elif '32' in arch:
                self.defined_macros['__riscv32__'] = "1"
                
        if self.args.verbose >= 3:
            print(f"Added architecture macros for {arch}")

    @staticmethod
    def clear_cache():
        # print("DirectHeaderDeps::clear_cache")
        diskcache.clear_cache()
        DirectHeaderDeps._search_project_includes.cache_clear()
        DirectHeaderDeps._find_include.cache_clear()
        DirectHeaderDeps._create_include_list.cache_clear()


class CppHeaderDeps(HeaderDepsBase):
    """Using the C Pre Processor, create the list of headers that the given file depends upon."""

    def __init__(self, args):
        HeaderDepsBase.__init__(self, args)
        self.preprocessor = ct.preprocessor.PreProcessor(args)

    @diskcache("deps", deps_mode=True)
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
        system_paths = tuple(item for pth in system_paths for item in (pth, ct.wrappedos.realpath(pth)))
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
        return ct.utils.ordered_unique(
            [
                ct.wrappedos.realpath(x)
                for x in deplist.split()
                if x.strip("\\\t\n\r") and x not in [realpath, "/dev/null"] and not x.startswith(system_paths)
            ]
        )

    @staticmethod
    def clear_cache():
        # print("CppHeaderDeps::clear_cache")
        diskcache.clear_cache()
