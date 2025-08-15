"""Simple C preprocessor for handling conditional compilation directives."""

import sys


class SimplePreprocessor:
    """A simple C preprocessor for handling conditional compilation directives.

    Capabilities:
    - Handles #if/#elif/#else/#endif, #ifdef/#ifndef, #define/#undef
    - Understands defined(MACRO) and defined MACRO forms
    - Supports C-style numeric literals: hex (0x), binary (0b), octal (0...)
    - Evaluates logical (&&, ||, ! and and/or/not), comparison, bitwise (&, |, ^, ~) and shift (<<, >>) operators
    - Strips // and /* ... */ comments from expressions in directives
    - Respects inactive branches (directives only alter state when active)
    - Provides recursive macro expansion helper for advanced use
    """
    
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
        
    def add_platform_macros(self):
        """Add common platform-specific macros"""
        if sys.platform.startswith('linux'):
            self.macros['__linux__'] = "1"
        elif sys.platform.startswith('win'):
            self.macros['_WIN32'] = "1"
        elif sys.platform.startswith('darwin'):
            self.macros['__APPLE__'] = "1"
    
    def _strip_comments(self, expr):
        """Strip C/C++ style comments from expressions.

        - Removes // line comments
        - Removes /* block comments */ (non-nested)
        """
        # Strip C++ style line comments
        if '//' in expr:
            expr = expr[:expr.find('//')].strip()

        # Strip C-style block comments
        import re
        if '/*' in expr:
            expr = re.sub(r"/\*.*?\*/", " ", expr)
            expr = " ".join(expr.split())  # normalize whitespace
        return expr
        
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
            # Strip comments before processing
            expr = self._strip_comments(args.strip())
            result = self._evaluate_expression(expr)
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
                # Strip comments before processing
                expr = self._strip_comments(args.strip())
                result = self._evaluate_expression(expr)
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
        """Replace macro names with their values.

        Avoid replacing logical word operators 'and', 'or', 'not' so our later
        operator translation still works even if users type them explicitly.
        """
        import re

        reserved = {"and", "or", "not"}

        def replace_macro(match):
            macro_name = match.group(0)
            if macro_name in reserved:
                return macro_name
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
    
    def _recursive_expand_macros(self, expr, max_iterations=10):
        """Recursively expand macros until no more changes occur or max iterations reached"""
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
        
        previous_expr = None
        iteration = 0
        
        while expr != previous_expr and iteration < max_iterations:
            previous_expr = expr
            # Replace macro names (identifiers) with their values
            expr = re.sub(r'(?<![0-9])\b[A-Za-z_][A-Za-z0-9_]*\b(?![0-9])', replace_macro, expr)
            iteration += 1
            
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
        expr = re.sub(r'(\d+)\s*\(\s*(\d+)\s*\)', r'\1 * \2', expr)
        
        # Remove C-style integer suffixes (L, UL, LL, ULL, etc.)
        expr = re.sub(r'(\d+)[LlUu]+\b', r'\1', expr)

        # Normalize C-style numeric literals to Python ints (hex, bin, octal)
        expr = self._normalize_numeric_literals(expr)
        
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
        # Allow bitwise ops (&, |, ^, ~), shifts (<<, >>) and letters for 'and', 'or', 'not'
        if not re.match(r'^[0-9\s\+\-\*\/\%\(\)\<\>\=\!&\|\^~andortnot ]+$', expr):
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

    def _normalize_numeric_literals(self, expr):
        """Convert C-style numeric literals (hex, bin, oct) to decimal strings.

        - 0x... or 0X... -> decimal
        - 0b... or 0B... -> decimal
        - 0... (octal) -> decimal, but leave single '0' as is and ignore 0x/0b prefixes
        """
        import re

        def repl_hex(m):
            return str(int(m.group(0), 16))

        def repl_bin(m):
            return str(int(m.group(0), 2))

        def repl_oct(m):
            s = m.group(0)
            # avoid replacing just '0'
            if s == '0':
                return s
            return str(int(s, 8))

        # Replace hex first
        expr = re.sub(r'\b0[xX][0-9A-Fa-f]+\b', repl_hex, expr)
        # Replace binary
        expr = re.sub(r'\b0[bB][01]+\b', repl_bin, expr)
        # Replace octal: leading 0 followed by one or more octal digits, not 0x/0b already handled
        expr = re.sub(r'\b0[0-7]+\b', repl_oct, expr)
        return expr