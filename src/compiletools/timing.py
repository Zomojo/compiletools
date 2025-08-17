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
        """Format time in human-readable format."""
        if seconds < 1.0:
            return f"{seconds * 1000:.1f}ms"
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
        
        total_time = sum(self.timings.values())
        
        if verbose_level >= 1:
            print(f"Total build time: {self.format_time(total_time)}", file=file)
        
        if verbose_level >= 3:
            print("\nDetailed timing breakdown:", file=file)
            self._report_detailed(file=file)
    
    def _report_detailed(self, file=None, indent=0):
        """Generate detailed hierarchical timing report."""
        if file is None:
            file = sys.stderr
        
        # Find top-level operations (not nested under others)
        top_level = []
        all_nested = set()
        for parent, children in self.nested_timings.items():
            all_nested.update(children)
        
        for op_name in self.timings:
            if op_name not in all_nested:
                top_level.append(op_name)
        
        # Report top-level operations
        for op_name in top_level:
            elapsed = self.timings.get(op_name, 0.0)
            print(f"{'  ' * indent}{op_name}: {self.format_time(elapsed)}", file=file)
            
            # Report nested operations
            if op_name in self.nested_timings:
                for child_name in self.nested_timings[op_name]:
                    if child_name in self.timings:
                        child_elapsed = self.timings[child_name]
                        print(f"{'  ' * (indent + 1)}{child_name}: {self.format_time(child_elapsed)}", file=file)
    
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