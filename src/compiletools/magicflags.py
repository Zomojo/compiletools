import sys
import os
import subprocess
import re
import configargparse
from collections import defaultdict
from io import open
from compiletools.diskcache import diskcache
import compiletools.utils
import compiletools.git_utils
import compiletools.headerdeps
import compiletools.wrappedos
import compiletools.configutils
import compiletools.apptools
from compiletools.file_analyzer import create_file_analyzer


def create(args, headerdeps):
    """MagicFlags Factory"""
    classname = args.magic.title() + "MagicFlags"
    if args.verbose >= 4:
        print("Creating " + classname + " to process magicflags.")
    magicclass = globals()[classname]
    magicobject = magicclass(args, headerdeps)
    return magicobject


def add_arguments(cap, variant=None):
    """Add the command line arguments that the MagicFlags classes require"""
    compiletools.apptools.add_common_arguments(cap, variant=variant)
    compiletools.preprocessor.PreProcessor.add_arguments(cap)
    alldepscls = [
        st[:-10].lower() for st in dict(globals()) if st.endswith("MagicFlags")
    ]
    cap.add(
        "--magic",
        choices=alldepscls,
        default="direct",
        help="Methodology for reading file when processing magic flags",
    )
    cap.add(
        "--max-file-read-size",
        type=int,
        default=0,
        help="Maximum bytes to read from files (0 = entire file)",
    )


class MagicFlagsBase:
    """A magic flag in a file is anything that starts
    with a //# and ends with an =
    E.g., //#key=value1 value2

    Note that a magic flag is a C++ comment.

    This class is a map of filenames
    to the map of all magic flags for that file.
    Each magic flag has a list of values preserving order.
    E.g., { '/somepath/libs/base/somefile.hpp':
               {'CPPFLAGS':['-D', 'MYMACRO', '-D', 'MACRO2'],
                'CXXFLAGS':['-fsomeoption'],
                'LDFLAGS':['-lsomelib']}}
    This function will extract all the magics flags from the given
    source (and all its included headers).
    source_filename must be an absolute path
    """

    def __init__(self, args, headerdeps):
        self._args = args
        self._headerdeps = headerdeps

        # The magic pattern is //#key=value with whitespace ignored
        self.magicpattern = re.compile(
            r"^[\s]*//#([\S]*?)[\s]*=[\s]*(.*)", re.MULTILINE
        )

    def readfile(self, filename):
        """Derived classes implement this method"""
        raise NotImplemented

    def __call__(self, filename):
        return self.parse(filename)

    def _handle_source(self, flag, text):
        # Find the include before the //#SOURCE=
        result = re.search(
            r'# \d.* "(/\S*?)".*?//#SOURCE\s*=\s*' + flag, text, re.DOTALL
        )
        # Now adjust the flag to include the full path
        newflag = compiletools.wrappedos.realpath(
            os.path.join(compiletools.wrappedos.dirname(result.group(1)), flag.strip())
        )
        if self._args.verbose >= 9:
            print(
                " ".join(
                    [
                        "Adjusting source magicflag from flag=",
                        flag,
                        "to",
                        newflag,
                    ]
                )
            )

        if not compiletools.wrappedos.isfile(newflag):
            raise IOError(
                filename
                + " specified "
                + magic
                + "='"
                + newflag
                + "' but it does not exist"
            )

        return newflag

    def _handle_include(self, flag):
        flagsforfilename = {}
        flagsforfilename.setdefault("CPPFLAGS", []).append("-I " + flag)
        flagsforfilename.setdefault("CFLAGS", []).append("-I " + flag)
        flagsforfilename.setdefault("CXXFLAGS", []).append("-I " + flag)
        if self._args.verbose >= 9:
            print(f"Added -I {flag} to CPPFLAGS, CFLAGS, and CXXFLAGS")
        return flagsforfilename

    def _handle_pkg_config(self, flag):
        flagsforfilename = defaultdict(list)
        for pkg in flag.split():
            # TODO: when we move to python 3.7, use text=True rather than universal_newlines=True and capture_output=True,
            cflags = (
                subprocess.run(
                    ["pkg-config", "--cflags", pkg],
                    stdout=subprocess.PIPE,
                    universal_newlines=True,
                )
                .stdout.rstrip()
                .replace("-I", "-isystem ")
            )  # This helps the CppHeaderDeps avoid searching packages
            libs = subprocess.run(
                ["pkg-config", "--libs", pkg],
                stdout=subprocess.PIPE,
                universal_newlines=True,
            ).stdout.rstrip()
            flagsforfilename["CPPFLAGS"].append(cflags)
            flagsforfilename["CFLAGS"].append(cflags)
            flagsforfilename["CXXFLAGS"].append(cflags)
            flagsforfilename["LDFLAGS"].append(libs)
            if self._args.verbose >= 9:
                print(f"Magic PKG-CONFIG = {pkg}:")
                print(f"\tadded {cflags} to CPPFLAGS, CFLAGS, and CXXFLAGS")
                print(f"\tadded {libs} to LDFLAGS")
        return flagsforfilename

    def _parse(self, filename):
        if self._args.verbose >= 4:
            print("Parsing magic flags for " + filename)

        # diskcache assumes that headerdeps _always_ exist
        # before the magic flags are called.
        # When used in the "usual" fashion this is true.
        # However, it is possible to call directly so we must
        # ensure that the headerdeps exist manually.
        self._headerdeps.process(filename)

        text = self.readfile(filename)
        flagsforfilename = defaultdict(list)

        for match in self.magicpattern.finditer(text):
            magic, flag = match.groups()

            # If the magic was SOURCE then fix up the path in the flag
            if magic == "SOURCE":
                flag = self._handle_source(flag, text)

            # If the magic was INCLUDE then modify that into the equivalent CPPFLAGS, CFLAGS, and CXXFLAGS
            if magic == "INCLUDE":
                extrafff = self._handle_include(flag)
                for key, values in extrafff.items():
                    for value in values:
                        flagsforfilename[key].append(value)

            # If the magic was PKG-CONFIG then call pkg-config
            if magic == "PKG-CONFIG":
                extrafff = self._handle_pkg_config(flag)
                for key, values in extrafff.items():
                    for value in values:
                        flagsforfilename[key].append(value)

            flagsforfilename[magic].append(flag)
            if self._args.verbose >= 5:
                print(
                    "Using magic flag {0}={1} extracted from {2}".format(
                        magic, flag, filename
                    )
                )
        
        # Deduplicate all flags while preserving order
        for key in flagsforfilename:
            flagsforfilename[key] = compiletools.utils.ordered_unique(flagsforfilename[key])

        return flagsforfilename

    @staticmethod
    def clear_cache():
        compiletools.utils.clear_cache()
        compiletools.git_utils.clear_cache()
        compiletools.wrappedos.clear_cache()
        DirectMagicFlags.clear_cache()
        CppMagicFlags.clear_cache()


class DirectMagicFlags(MagicFlagsBase):
    def __init__(self, args, headerdeps):
        MagicFlagsBase.__init__(self, args, headerdeps)
        # Track defined macros during processing
        self.defined_macros = set()
        # Track macro values for expression evaluation
        self.macro_values = {}

    def _add_macros_from_command_line_flags(self):
        """Extract -D macros from command-line CPPFLAGS and CXXFLAGS and add them to defined_macros"""
        import shlex
        
        # Check both CPPFLAGS and CXXFLAGS for macro definitions
        flag_sources = []
        if hasattr(self._args, 'CPPFLAGS') and self._args.CPPFLAGS:
            flag_sources.append(('CPPFLAGS', self._args.CPPFLAGS))
        if hasattr(self._args, 'CXXFLAGS') and self._args.CXXFLAGS:
            flag_sources.append(('CXXFLAGS', self._args.CXXFLAGS))
            
        for source_name, flag_value in flag_sources:
            # Handle both string and list types for flag_value
            if isinstance(flag_value, list):
                flag_string = ' '.join(flag_value)
            else:
                flag_string = flag_value
                
            flags = shlex.split(flag_string)
            for flag in flags:
                if flag.startswith('-D'):
                    # Extract macro name and value (handle both -DMACRO and -DMACRO=value)
                    macro_def = flag[2:]  # Remove the -D
                    if '=' in macro_def:
                        macro_name, macro_value = macro_def.split('=', 1)
                    else:
                        macro_name = macro_def
                        macro_value = "1"
                    
                    if macro_name:
                        self.defined_macros.add(macro_name)
                        self.macro_values[macro_name] = macro_value
                        if self._args.verbose >= 9:
                            print(f"DirectMagicFlags: added command-line macro {macro_name} = {macro_value} from {source_name}")

    def _create_macro_dict(self):
        """Convert defined_macros and macro_values to a dict for SimplePreprocessor"""
        # Return a copy of our macro_values dict
        return self.macro_values.copy()

    def _recursive_expand_macros(self, expr, macros, max_iterations=10):
        """Recursively expand macros until no more changes occur"""
        import re
        
        def replace_macro(match):
            macro_name = match.group(0)
            if macro_name in macros:
                value = macros[macro_name]
                # Try to convert to int if possible
                try:
                    return str(int(value))
                except ValueError:
                    return value
            else:
                # Undefined macro defaults to 0
                return "0"
        
        previous_expr = None
        iteration = 0
        
        while expr != previous_expr and iteration < max_iterations:
            previous_expr = expr
            # Replace macro names (identifiers) with their values
            expr = re.sub(r'(?<![0-9])\b[A-Za-z_][A-Za-z0-9_]*\b(?![0-9])', replace_macro, expr)
            iteration += 1
            
        return expr

    def _process_conditional_compilation(self, text):
        """Process conditional compilation directives and return only active sections"""
        lines = text.split('\n')
        result_lines = []
        
        # Stack to track conditional compilation state
        # Each entry is (is_active, seen_else)
        condition_stack = [(True, False)]  # Start with active context
        
        # Create SimplePreprocessor for expression evaluation
        from compiletools.simple_preprocessor import SimplePreprocessor
        macro_dict = self._create_macro_dict()
        preprocessor = SimplePreprocessor(macro_dict, verbose=self._args.verbose)
        
        for line in lines:
            stripped = line.strip()
            
            # Track #define statements
            if stripped.startswith('#define ') and condition_stack[-1][0]:
                parts = stripped.split(' ', 2)
                if len(parts) >= 2:
                    macro_name = parts[1]
                    macro_value = parts[2] if len(parts) > 2 else "1"
                    self.defined_macros.add(macro_name)
                    self.macro_values[macro_name] = macro_value
                    # Also update the preprocessor's macro dict
                    preprocessor.macros[macro_name] = macro_value
                    if self._args.verbose >= 9:
                        print(f"DirectMagicFlags: defined macro {macro_name} = {macro_value}")
            
            # Handle conditional compilation directives
            elif stripped.startswith('#ifdef '):
                macro = stripped[7:].strip()
                is_defined = macro in self.defined_macros
                condition_stack.append((is_defined and condition_stack[-1][0], False))
                if self._args.verbose >= 9:
                    print(f"DirectMagicFlags: #ifdef {macro} -> {is_defined}")
                    
            elif stripped.startswith('#ifndef '):
                macro = stripped[8:].strip()
                is_defined = macro in self.defined_macros
                condition_stack.append((not is_defined and condition_stack[-1][0], False))
                if self._args.verbose >= 9:
                    print(f"DirectMagicFlags: #ifndef {macro} -> {not is_defined}")
            
            elif stripped.startswith('#if '):
                expr = stripped[4:].strip()
                # Strip C++ style comments from the expression
                if '//' in expr:
                    expr = expr[:expr.find('//')].strip()
                    
                try:
                    # Use our recursive macro expansion
                    expanded_expr = self._recursive_expand_macros(expr, self.macro_values)
                    if self._args.verbose >= 9:
                        print(f"DirectMagicFlags: expanding #if '{expr}' -> '{expanded_expr}'")
                    
                    # Now evaluate with SimplePreprocessor's safe evaluator
                    result = preprocessor._safe_eval(expanded_expr)
                    is_true = bool(result)
                    is_active = is_true and condition_stack[-1][0]
                    condition_stack.append((is_active, False))
                    if self._args.verbose >= 9:
                        print(f"DirectMagicFlags: #if {expr} -> {result} ({is_active})")
                except Exception as e:
                    # If evaluation fails, assume false
                    if self._args.verbose >= 8:
                        print(f"DirectMagicFlags: #if evaluation failed for '{expr}': {e}")
                    condition_stack.append((False, False))
                    
            elif stripped.startswith('#else'):
                if len(condition_stack) > 1:
                    current_active, seen_else = condition_stack.pop()
                    if not seen_else:
                        parent_active = condition_stack[-1][0] if condition_stack else True
                        new_active = not current_active and parent_active
                        condition_stack.append((new_active, True))
                        if self._args.verbose >= 9:
                            print(f"DirectMagicFlags: #else -> {new_active}")
                    else:
                        condition_stack.append((False, True))
                        
            elif stripped.startswith('#endif'):
                if len(condition_stack) > 1:
                    condition_stack.pop()
                    if self._args.verbose >= 9:
                        print("DirectMagicFlags: #endif")
            else:
                # Only include this line if we're in an active context
                if condition_stack[-1][0]:
                    result_lines.append(line)
        
        return '\n'.join(result_lines)

    def readfile(self, filename):
        """Read the first chunk of the file and all the headers it includes"""
        # Reset defined macros for each new parse
        self.defined_macros = set()
        self.macro_values = {}
        
        # Add macros from command-line CPPFLAGS and CXXFLAGS (e.g., from --append-CPPFLAGS/--append-CXXFLAGS)
        self._add_macros_from_command_line_flags()
        
        # Add some common predefined macros that are typically available
        # These are basic ones that don't require a compiler invocation
        if sys.platform.startswith('linux'):
            self.defined_macros.add('__linux__')
            self.macro_values['__linux__'] = "1"
        elif sys.platform.startswith('win'):
            self.defined_macros.add('_WIN32')
            self.macro_values['_WIN32'] = "1"
        elif sys.platform.startswith('darwin'):
            self.defined_macros.add('__APPLE__')
            self.macro_values['__APPLE__'] = "1"
        
        headers = self._headerdeps.process(filename)
        
        # Process files iteratively until no new macros are discovered
        # This handles cases where macros defined in one file affect conditional
        # compilation in other files
        previous_macros = set()
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while previous_macros != self.defined_macros and iteration < max_iterations:
            previous_macros = self.defined_macros.copy()
            iteration += 1
            
            if self._args.verbose >= 9:
                print(f"DirectMagicFlags::readfile iteration {iteration}, known macros: {self.defined_macros}")
            
            text = ""
            # Process files in dependency order
            # Combine headers with filename, handling both list and set types
            all_files = list(headers) + [filename] if filename not in headers else list(headers)
            for fname in all_files:
                if self._args.verbose >= 9:
                    print("DirectMagicFlags::readfile is processing " + fname)
                
                # To match the output of the C Pre Processor we insert
                # the filename before the text
                file_header = '# 1 "' + compiletools.wrappedos.realpath(fname) + '"\n'
                
                # Read file content using FileAnalyzer respecting max_file_read_size configuration
                max_read_size = getattr(self._args, 'max_file_read_size', 0)
                
                # Use FileAnalyzer for efficient file reading
                # Note: create_file_analyzer() handles StringZilla/Legacy fallback internally
                analyzer = create_file_analyzer(fname, max_read_size, self._args.verbose)
                analysis_result = analyzer.analyze()
                file_content = analysis_result.text
                
                # Process conditional compilation for this file
                processed_content = self._process_conditional_compilation(file_content)
                
                text += file_header + processed_content

        return text

    @diskcache("directmagic", magic_mode=True)
    def parse(self, filename):
        return self._parse(filename)

    @staticmethod
    def clear_cache():
        compiletools.diskcache.diskcache.clear_cache()


class CppMagicFlags(MagicFlagsBase):
    def __init__(self, args, headerdeps):
        MagicFlagsBase.__init__(self, args, headerdeps)
        self.preprocessor = compiletools.preprocessor.PreProcessor(args)

    def readfile(self, filename):
        """Preprocess the given filename but leave comments"""
        extraargs = "-C -E"
        return self.preprocessor.process(
            realpath=filename, extraargs="-C -E", redirect_stderr_to_stdout=True
        )

    @diskcache("cppmagic", magic_mode=True)
    def parse(self, filename):
        return self._parse(filename)

    @staticmethod
    def clear_cache():
        compiletools.diskcache.diskcache.clear_cache()


class NullStyle(compiletools.git_utils.NameAdjuster):
    def __init__(self, args):
        compiletools.git_utils.NameAdjuster.__init__(self, args)

    def __call__(self, realpath, magicflags):
        print("{}: {}".format(self.adjust(realpath), str(magicflags)))


class PrettyStyle(compiletools.git_utils.NameAdjuster):
    def __init__(self, args):
        compiletools.git_utils.NameAdjuster.__init__(self, args)

    def __call__(self, realpath, magicflags):
        sys.stdout.write("\n{}".format(self.adjust(realpath)))
        try:
            for key in magicflags:
                sys.stdout.write("\n\t{}:".format(key))
                for flag in magicflags[key]:
                    sys.stdout.write(" {}".format(flag))
        except TypeError:
            sys.stdout.write("\n\tNone")


def main(argv=None):
    cap = compiletools.apptools.create_parser(
        "Parse a file and show the magicflags it exports", argv=argv
    )
    compiletools.headerdeps.add_arguments(cap)
    add_arguments(cap)
    cap.add("filename", help='File/s to extract magicflags from"', nargs="+")

    # Figure out what style classes are available and add them to the command
    # line options
    styles = [st[:-5].lower() for st in dict(globals()) if st.endswith("Style")]
    cap.add("--style", choices=styles, default="pretty", help="Output formatting style")

    args = compiletools.apptools.parseargs(cap, argv)
    headerdeps = compiletools.headerdeps.create(args)
    magicparser = create(args, headerdeps)

    styleclass = globals()[args.style.title() + "Style"]
    styleobject = styleclass(args)

    for fname in args.filename:
        realpath = compiletools.wrappedos.realpath(fname)
        styleobject(realpath, magicparser.parse(realpath))

    print()
    return 0
