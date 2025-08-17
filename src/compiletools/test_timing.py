import unittest
import time
import sys
from io import StringIO
from unittest.mock import Mock, patch

import compiletools.timing


class TestTimer(unittest.TestCase):
    
    def setUp(self):
        self.timer = compiletools.timing.Timer(enabled=True)
    
    def test_timer_disabled(self):
        """Test that disabled timer doesn't track anything"""
        timer = compiletools.timing.Timer(enabled=False)
        timer.start("test_op")
        time.sleep(0.01)
        elapsed = timer.stop("test_op")
        
        self.assertEqual(elapsed, 0.0)
        self.assertEqual(len(timer.timings), 0)
    
    def test_basic_timing(self):
        """Test basic start/stop timing functionality"""
        self.timer.start("test_operation")
        time.sleep(0.01)
        elapsed = self.timer.stop("test_operation")
        
        self.assertGreater(elapsed, 0.0)
        self.assertIn("test_operation", self.timer.timings)
        self.assertEqual(self.timer.get_elapsed("test_operation"), elapsed)
    
    def test_context_manager(self):
        """Test timing with context manager"""
        with self.timer.time_operation("context_test"):
            time.sleep(0.01)
        
        self.assertIn("context_test", self.timer.timings)
        self.assertGreater(self.timer.get_elapsed("context_test"), 0.0)
    
    def test_nested_timing(self):
        """Test nested timing operations"""
        with self.timer.time_operation("outer"):
            time.sleep(0.01)
            with self.timer.time_operation("inner"):
                time.sleep(0.01)
        
        self.assertIn("outer", self.timer.timings)
        self.assertIn("inner", self.timer.timings)
        self.assertIn("outer", self.timer.nested_timings)
        self.assertIn("inner", self.timer.nested_timings["outer"])
    
    def test_format_time(self):
        """Test time formatting"""
        self.assertEqual(self.timer.format_time(0.0005), "500µs")
        self.assertEqual(self.timer.format_time(0.0015), "1.5ms")
        self.assertEqual(self.timer.format_time(1.5), "1.5s")
        self.assertEqual(self.timer.format_time(65.5), "1m5.5s")
    
    def test_get_summary(self):
        """Test getting timing summary"""
        self.timer.start("op1")
        time.sleep(0.01)
        self.timer.stop("op1")
        
        self.timer.start("op2")
        time.sleep(0.02)
        self.timer.stop("op2")
        
        summary = self.timer.get_summary()
        
        self.assertGreater(summary['total_time'], 0.0)
        self.assertEqual(summary['operation_count'], 2)
        self.assertIsNotNone(summary['slowest_operation'])
        self.assertEqual(summary['slowest_operation'][0], "op2")
        self.assertIn("op1", summary['operations'])
        self.assertIn("op2", summary['operations'])
    
    def test_report_disabled_timer(self):
        """Test report with disabled timer"""
        timer = compiletools.timing.Timer(enabled=False)
        output = StringIO()
        timer.report(verbose_level=1, file=output)
        
        self.assertEqual(output.getvalue(), "")
    
    def test_report_verbose_1(self):
        """Test report at verbose level 1"""
        self.timer.start("test_op")
        time.sleep(0.01)
        self.timer.stop("test_op")
        
        output = StringIO()
        self.timer.report(verbose_level=1, file=output)
        
        output_text = output.getvalue()
        self.assertIn("Total build time:", output_text)
    
    def test_report_verbose_3(self):
        """Test report at verbose level 3"""
        with self.timer.time_operation("outer"):
            time.sleep(0.01)
            with self.timer.time_operation("inner"):
                time.sleep(0.01)
        
        output = StringIO()
        self.timer.report(verbose_level=3, file=output)
        
        output_text = output.getvalue()
        self.assertIn("Total build time:", output_text)
        self.assertIn("Detailed timing breakdown:", output_text)
        self.assertIn("outer:", output_text)
        self.assertIn("inner:", output_text)


class TestGlobalTimerFunctions(unittest.TestCase):
    
    def setUp(self):
        compiletools.timing.initialize_timer(enabled=True)
    
    def tearDown(self):
        compiletools.timing.initialize_timer(enabled=False)
    
    def test_global_timer_initialization(self):
        """Test global timer initialization"""
        compiletools.timing.initialize_timer(enabled=True)
        timer = compiletools.timing.get_timer()
        self.assertTrue(timer.enabled)
        
        compiletools.timing.initialize_timer(enabled=False)
        timer = compiletools.timing.get_timer()
        self.assertFalse(timer.enabled)
    
    def test_global_timer_operations(self):
        """Test global timer operations"""
        compiletools.timing.start_timing("global_test")
        time.sleep(0.01)
        elapsed = compiletools.timing.stop_timing("global_test")
        
        self.assertGreater(elapsed, 0.0)
        
        timer = compiletools.timing.get_timer()
        self.assertIn("global_test", timer.timings)
    
    def test_global_context_manager(self):
        """Test global timer context manager"""
        with compiletools.timing.time_operation("global_context"):
            time.sleep(0.01)
        
        timer = compiletools.timing.get_timer()
        self.assertIn("global_context", timer.timings)
        self.assertGreater(timer.get_elapsed("global_context"), 0.0)
    
    def test_global_report(self):
        """Test global timer reporting"""
        with compiletools.timing.time_operation("report_test"):
            time.sleep(0.01)
        
        output = StringIO()
        compiletools.timing.report_timing(verbose_level=1, file=output)
        
        output_text = output.getvalue()
        self.assertIn("Total build time:", output_text)


class TestTimingIntegration(unittest.TestCase):
    """Test timing integration with other components"""
    
    def test_timing_with_args_object(self):
        """Test timing behavior with args objects that have time attribute"""
        # Mock args object with time=True
        args = Mock()
        args.time = True
        args.verbose = 1
        
        # This would be called in actual code
        timer_enabled = hasattr(args, 'time') and args.time
        self.assertTrue(timer_enabled)
        
        # Mock args object with time=False
        args.time = False
        timer_enabled = hasattr(args, 'time') and args.time
        self.assertFalse(timer_enabled)
        
        # Mock args object without time attribute
        delattr(args, 'time')
        timer_enabled = hasattr(args, 'time') and args.time
        self.assertFalse(timer_enabled)


if __name__ == '__main__':
    unittest.main()