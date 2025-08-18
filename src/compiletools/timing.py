import time
import sys
from contextlib import contextmanager
from collections import defaultdict, OrderedDict


class Timer:
    """Timer class for tracking elapsed time of operations in compiletools.
    
    Supports nested timing contexts and hierarchical reporting based on verbose levels.
    """
    
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.timings = OrderedDict()  # Operation name -> elapsed time
        self.nested_timings = defaultdict(list)  # Parent -> list of child timings
        self.start_times = {}  # Operation name -> start time
        self.operation_stack = []  # Stack for nested operations
        
    def start(self, operation_name):
        """Start timing an operation."""
        if not self.enabled:
            return
            
        current_time = time.perf_counter()
        self.start_times[operation_name] = current_time
        
        # Track nesting
        if self.operation_stack:
            parent = self.operation_stack[-1]
            self.nested_timings[parent].append(operation_name)
        
        self.operation_stack.append(operation_name)
    
    def stop(self, operation_name):
        """Stop timing an operation and record elapsed time."""
        if not self.enabled:
            return 0.0
            
        current_time = time.perf_counter()
        
        if operation_name not in self.start_times:
            return 0.0
            
        elapsed = current_time - self.start_times[operation_name]
        self.timings[operation_name] = elapsed
        
        # Remove from stack
        if self.operation_stack and self.operation_stack[-1] == operation_name:
            self.operation_stack.pop()
        
        del self.start_times[operation_name]
        return elapsed
    
    @contextmanager
    def time_operation(self, operation_name):
        """Context manager for timing operations."""
        self.start(operation_name)
        try:
            yield
        finally:
            self.stop(operation_name)
    
    def get_elapsed(self, operation_name):
        """Get elapsed time for an operation."""
        return self.timings.get(operation_name, 0.0)
    
    def format_time(self, seconds):
        """Format time in microseconds for precision."""
        microseconds = seconds * 1_000_000
        if microseconds < 1000:
            return f"{microseconds:.0f}µs"
        elif microseconds < 1_000_000:
            return f"{microseconds / 1000:.1f}ms"
        elif seconds < 60.0:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m{secs:.1f}s"
    
    def report(self, verbose_level, file=None):
        """Generate timing report based on verbose level."""
        if not self.enabled or not self.timings:
            return
        
        if file is None:
            file = sys.stderr
        
        # Calculate total time from top-level operations only to avoid double-counting
        all_nested = set()
        for children in self.nested_timings.values():
            all_nested.update(children)
        
        top_level_ops = [op for op in self.timings if op not in all_nested]
        total_time = sum(self.timings[op] for op in top_level_ops) if top_level_ops else sum(self.timings.values())
        
        if verbose_level >= 0:
            print(f"Total build time: {self.format_time(total_time)}", file=file)
        
        if verbose_level >= 1:
            print("\nDetailed timing breakdown:", file=file)
            # Each verbose level allows one more level of indentation
            max_depth = verbose_level
            self._report_detailed(file=file, max_depth=max_depth)
    
    def _report_detailed(self, file=None, indent=0, shown_operations=None, max_depth=None):
        """Generate detailed hierarchical timing report."""
        if file is None:
            file = sys.stderr
        
        if shown_operations is None:
            shown_operations = set()
        
        # Find top-level operations (not nested under others)
        top_level = []
        all_nested = set()
        for parent, children in self.nested_timings.items():
            all_nested.update(children)
        
        for op_name in self.timings:
            if op_name not in all_nested:
                top_level.append(op_name)
        
        # Report top-level operations recursively
        for op_name in top_level:
            if op_name not in shown_operations:
                self._report_operation_recursive(op_name, file, indent, shown_operations, max_depth)
    
    def _report_operation_recursive(self, op_name, file, indent, shown_operations, max_depth):
        """Recursively report an operation and all its nested operations."""
        if op_name in shown_operations:
            return
        
        shown_operations.add(op_name)
        elapsed = self.timings.get(op_name, 0.0)
        print(f"{'  ' * indent}{op_name}: {self.format_time(elapsed)}", file=file)
        
        # Report nested operations recursively, respecting max_depth
        if op_name in self.nested_timings and (max_depth is None or indent < max_depth):
            for child_name in self.nested_timings[op_name]:
                if child_name in self.timings:
                    self._report_operation_recursive(child_name, file, indent + 1, shown_operations, max_depth)
    
    def get_summary(self):
        """Get a summary dictionary of timing information."""
        if not self.enabled:
            return {}
        
        return {
            'total_time': sum(self.timings.values()),
            'operation_count': len(self.timings),
            'slowest_operation': max(self.timings.items(), key=lambda x: x[1]) if self.timings else None,
            'operations': dict(self.timings)
        }


# Global timer instance for use throughout compiletools
_global_timer = Timer()


def get_timer():
    """Get the global timer instance."""
    return _global_timer


def initialize_timer(enabled=False):
    """Initialize the global timer."""
    global _global_timer
    _global_timer = Timer(enabled)


def time_operation(operation_name):
    """Context manager decorator for timing operations."""
    return _global_timer.time_operation(operation_name)


def start_timing(operation_name):
    """Start timing an operation using the global timer."""
    _global_timer.start(operation_name)


def stop_timing(operation_name):
    """Stop timing an operation using the global timer."""
    return _global_timer.stop(operation_name)


def report_timing(verbose_level, file=None):
    """Generate timing report using the global timer."""
    _global_timer.report(verbose_level, file)