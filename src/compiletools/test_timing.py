import time
import sys
from io import StringIO
from unittest.mock import Mock
import re
import pytest

import compiletools.timing


class TestTimer:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.timer = compiletools.timing.Timer(enabled=True)
    
    def test_timer_disabled(self):
        """Test that disabled timer doesn't track anything"""
        timer = compiletools.timing.Timer(enabled=False)
        timer.start("test_op")
        time.sleep(0.01)
        elapsed = timer.stop("test_op")
        
        assert elapsed == 0.0
        assert len(timer.timings) == 0
    
    def test_basic_timing(self):
        """Test basic start/stop timing functionality"""
        self.timer.start("test_operation")
        time.sleep(0.01)
        elapsed = self.timer.stop("test_operation")
        
        assert elapsed > 0.0
        assert "test_operation" in self.timer.timings
        assert self.timer.get_elapsed("test_operation") == elapsed
    
    def test_context_manager(self):
        """Test timing with context manager"""
        with self.timer.time_operation("context_test"):
            time.sleep(0.01)
        
        assert "context_test" in self.timer.timings
        assert self.timer.get_elapsed("context_test") > 0.0
    
    def test_nested_timing(self):
        """Test nested timing operations"""
        with self.timer.time_operation("outer"):
            time.sleep(0.01)
            with self.timer.time_operation("inner"):
                time.sleep(0.01)
        
        assert "outer" in self.timer.timings
        assert "inner" in self.timer.timings
        assert "outer" in self.timer.nested_timings
        assert "inner" in self.timer.nested_timings["outer"]
    
    def test_format_time(self):
        """Test time formatting"""
        assert self.timer.format_time(0.0005) == "500µs"
        assert self.timer.format_time(0.0015) == "1.5ms"
        assert self.timer.format_time(1.5) == "1.5s"
        assert self.timer.format_time(65.5) == "1m5.5s"
    
    def test_get_summary(self):
        """Test getting timing summary"""
        self.timer.start("op1")
        time.sleep(0.01)
        self.timer.stop("op1")
        
        self.timer.start("op2")
        time.sleep(0.02)
        self.timer.stop("op2")
        
        summary = self.timer.get_summary()
        
        assert summary['total_time'] > 0.0
        assert summary['operation_count'] == 2
        assert summary['slowest_operation'] is not None
        assert summary['slowest_operation'][0] == "op2"
        assert "op1" in summary['operations']
        assert "op2" in summary['operations']
    
    def test_report_disabled_timer(self):
        """Test report with disabled timer"""
        timer = compiletools.timing.Timer(enabled=False)
        output = StringIO()
        timer.report(verbose_level=1, file=output)
        
        assert output.getvalue() == ""
    
    def test_report_verbose_1(self):
        """Test report at verbose level 1"""
        self.timer.start("test_op")
        time.sleep(0.01)
        self.timer.stop("test_op")
        
        output = StringIO()
        self.timer.report(verbose_level=1, file=output)
        
        output_text = output.getvalue()
        assert "Total build time:" in output_text
    
    def test_report_verbose_3(self):
        """Test report at verbose level 3"""
        with self.timer.time_operation("outer"):
            time.sleep(0.01)
            with self.timer.time_operation("inner"):
                time.sleep(0.01)
        
        output = StringIO()
        self.timer.report(verbose_level=3, file=output)
        
        output_text = output.getvalue()
        assert "Total build time:" in output_text
        assert "Detailed timing breakdown:" in output_text
        assert "outer:" in output_text
        assert "inner:" in output_text
    
    def test_total_time_no_double_counting(self):
        """Test that total time doesn't double-count nested operations"""
        # Create nested timing operations with measurable delays
        self.timer.start("outer_operation")
        time.sleep(0.01)  # outer-only work
        
        self.timer.start("inner_operation_1")
        time.sleep(0.01)  # inner1 work
        self.timer.stop("inner_operation_1")
        
        self.timer.start("inner_operation_2")
        time.sleep(0.01)  # inner2 work
        self.timer.stop("inner_operation_2")
        
        time.sleep(0.01)  # more outer-only work
        self.timer.stop("outer_operation")
        
        # Get actual recorded times
        outer_elapsed = self.timer.get_elapsed("outer_operation")
        inner1_elapsed = self.timer.get_elapsed("inner_operation_1")
        inner2_elapsed = self.timer.get_elapsed("inner_operation_2")
        
        # Calculate what the wrong total would be (if we double-counted)
        wrong_total = outer_elapsed + inner1_elapsed + inner2_elapsed
        
        # Get the report output
        output = StringIO()
        self.timer.report(verbose_level=1, file=output)
        output_text = output.getvalue()
        
        # Extract the reported total time from the output
        match = re.search(r'Total build time: ([\d.]+)(µs|ms|s|m[\d.]+s)', output_text)
        assert match is not None, f"Could not find total time in report: {output_text}"
        
        reported_value = float(match.group(1))
        unit = match.group(2)
        
        # Convert reported value to seconds
        if unit.endswith('µs'):
            reported_total = reported_value / 1_000_000
        elif unit.endswith('ms'):
            reported_total = reported_value / 1000
        elif unit.startswith('m'):  # e.g., "1m5.5s"
            # Parse minutes and seconds
            m_match = re.match(r'(\d+)m([\d.]+)s', unit)
            if m_match:
                minutes = int(match.group(1))
                seconds = float(m_match.group(2))
                reported_total = minutes * 60 + seconds
            else:
                reported_total = reported_value * 60  # just minutes
        else:  # seconds
            reported_total = reported_value
        
        # The critical test: reported total should be close to outer_elapsed (the top-level operation)
        # NOT the sum of all operations (which would be wrong due to double-counting)
        assert reported_total == pytest.approx(outer_elapsed, abs=0.005), \
            f"Reported total {reported_total} should equal outer time {outer_elapsed}, " \
            f"not the sum {wrong_total}"
        
        # Additional check: reported total should be significantly less than the sum
        assert reported_total < wrong_total * 0.8, \
            f"Reported total {reported_total} should be less than 80% of wrong sum {wrong_total}"
        
        # Verify nesting is tracked correctly
        assert "outer_operation" in self.timer.nested_timings
        assert "inner_operation_1" in self.timer.nested_timings["outer_operation"]
        assert "inner_operation_2" in self.timer.nested_timings["outer_operation"]


class TestGlobalTimerFunctions:
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        compiletools.timing.initialize_timer(enabled=True)
        yield
        compiletools.timing.initialize_timer(enabled=False)
    
    def test_global_timer_initialization(self):
        """Test global timer initialization"""
        compiletools.timing.initialize_timer(enabled=True)
        timer = compiletools.timing.get_timer()
        assert timer.enabled
        
        compiletools.timing.initialize_timer(enabled=False)
        timer = compiletools.timing.get_timer()
        assert not timer.enabled
    
    def test_global_timer_operations(self):
        """Test global timer operations"""
        compiletools.timing.start_timing("global_test")
        time.sleep(0.01)
        elapsed = compiletools.timing.stop_timing("global_test")
        
        assert elapsed > 0.0
        
        timer = compiletools.timing.get_timer()
        assert "global_test" in timer.timings
    
    def test_global_context_manager(self):
        """Test global timer context manager"""
        with compiletools.timing.time_operation("global_context"):
            time.sleep(0.01)
        
        timer = compiletools.timing.get_timer()
        assert "global_context" in timer.timings
        assert timer.get_elapsed("global_context") > 0.0
    
    def test_global_report(self):
        """Test global timer reporting"""
        with compiletools.timing.time_operation("report_test"):
            time.sleep(0.01)
        
        output = StringIO()
        compiletools.timing.report_timing(verbose_level=1, file=output)
        
        output_text = output.getvalue()
        assert "Total build time:" in output_text


class TestTimingIntegration:
    """Test timing integration with other components"""
    
    def test_timing_with_args_object(self):
        """Test timing behavior with args objects that have time attribute"""
        # Mock args object with time=True
        args = Mock()
        args.time = True
        args.verbose = 1
        
        # This would be called in actual code
        timer_enabled = hasattr(args, 'time') and args.time
        assert timer_enabled
        
        # Mock args object with time=False
        args.time = False
        timer_enabled = hasattr(args, 'time') and args.time
        assert not timer_enabled
        
        # Mock args object without time attribute
        delattr(args, 'time')
        timer_enabled = hasattr(args, 'time') and args.time
        assert not timer_enabled