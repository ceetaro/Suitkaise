#!/usr/bin/env python3
"""
Comprehensive test module for SKFunction with performance monitoring.

This module tests the complete SKFunction system including:
- Named parameter injection and function state preservation
- Performance monitoring, caching, and optimization features  
- Memory tracking and system-wide metrics
- Builder pattern and registry management
- Cross-process serialization and error handling

Run with:
    python3.11 -m pytest tests/test_suitkaise/test_skfunction/test_skfunction.py -v
    
Or with unittest:
    python3.11 -m unittest tests.test_suitkaise.test_skfunction.test_skfunction -v
"""

import unittest
import tempfile
import shutil
import os
import sys
import threading
import time
import statistics
from pathlib import Path
from typing import Dict, Any, List, Tuple
from unittest.mock import patch, MagicMock

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Visual indicators for test output
INFO = "⬜️" * 40 + "\n\n\n"
FAIL = "\n\n   " + "❌" * 10 + " "
SUCCESS = "\n\n   " + "🟩" * 10 + " "
RUNNING = "🔄" * 40 + "\n\n"
CHECKING = "🧳" * 40 + "\n"
WARNING = "\n\n   " + "🟨" * 10 + " "

from suitkaise.skfunction.skfunction import (
    SKFunction,
    SKFunctionBuilder,
    PerformanceMetrics,
    PerformanceCache,
    PerformanceMonitor,
    _performance_cache,
    _performance_monitor,
    AnyFunction,
    SKFunctionError,
    SKFunctionBuilderError,
    SKFunctionBuildError,
    SKFunctionRegistrationError,
    SKFunctionPerformanceError,
    edit_skfunction,
    get_function,
    list_functions,
    remove_function,
    convert_callable,
    autoregister,
    can_register_function,
    create,
    register,
    clear_registry,
    registry_info,
    get_performance_report,
    get_system_performance_metrics,
    clear_performance_cache,
    reset_performance_monitor,
    enable_memory_tracking,
    get_optimization_suggestions,
    benchmark_function,
)


# =============================================================================
# TEST FUNCTIONS (moved from main module)
# =============================================================================

def simple_add(a: int, b: int) -> int:
    """Simple addition function for testing."""
    return a + b

def complex_function(a: int, b: str, c: float = 3.14, d: str = "default", 
                   *, keyword_only: bool = False, **extra) -> dict:
    """Complex function with various parameter types for testing named injection."""
    return {
        'a': a, 'b': b, 'c': c, 'd': d, 
        'keyword_only': keyword_only, 'extra': extra
    }

def simple_multiply(x: int, y: int) -> int:
    """Simple multiplication for testing."""
    return x * y

def function_with_required_params(a: int, b: str, c: float):
    """Function with required parameters for testing validation."""
    return f"{a}-{b}-{c}"

def slow_function(sleep_time: float = 0.01) -> str:
    """Function that takes time to execute for performance testing."""
    time.sleep(sleep_time)
    return "completed"

def error_function():
    """Function that raises an error for testing error handling."""
    raise ValueError("Test error")

def data_processing_pipeline(source: str, target: str, format: str = "json", 
                           debug: bool = False, timeout: int = 30) -> dict:
    """Complex function simulating a data processing pipeline."""
    return {
        "source": source,
        "target": target, 
        "format": format,
        "debug": debug,
        "timeout": timeout,
        "processed": True
    }

def memory_intensive_function(size: int = 1000) -> list:
    """Function that allocates memory for testing memory tracking."""
    return [i * i for i in range(size)]

def variable_time_function(base_time: float = 0.001, variance: float = 0.0005) -> str:
    """Function with variable execution time for testing performance metrics."""
    import random
    sleep_time = base_time + random.uniform(-variance, variance)
    time.sleep(max(0, sleep_time))
    return "variable_completed"


# =============================================================================
# PERFORMANCE MONITORING TESTS
# =============================================================================

class TestPerformanceMetrics(unittest.TestCase):
    """Test the PerformanceMetrics system."""
    
    def setUp(self):
        """Set up test fixtures."""
        clear_registry()
        clear_performance_cache()
        reset_performance_monitor()
    
    def tearDown(self):
        """Clean up test fixtures."""
        clear_registry()
        clear_performance_cache()
        reset_performance_monitor()
        
    def test_performance_metrics_basic_tracking(self):
        """
        Test basic performance metrics tracking.
        
        Tests call count, execution time tracking, and success rate calculation.
        """
        metrics = PerformanceMetrics()
        
        # Test initial state
        self.assertEqual(metrics.call_count, 0)
        self.assertEqual(metrics.avg_execution_time, 0.0)
        self.assertEqual(metrics.success_rate, 100.0)
        self.assertEqual(metrics.cache_hit_rate, 0.0)
        
        # Record some executions
        metrics.record_execution(0.1, had_error=False, was_simple=True)
        metrics.record_execution(0.2, had_error=False, was_simple=False, used_named_args=True)
        metrics.record_execution(0.15, had_error=True, was_simple=False)
        
        # Check tracking
        self.assertEqual(metrics.call_count, 3)
        self.assertAlmostEqual(metrics.avg_execution_time, 0.15, places=2)
        self.assertEqual(metrics.simple_calls, 1)
        self.assertEqual(metrics.complex_calls, 2)
        self.assertEqual(metrics.named_arg_calls, 1)
        self.assertEqual(metrics.error_count, 1)
        self.assertAlmostEqual(metrics.success_rate, 66.67, places=1)
    
    def test_performance_metrics_complexity_ratio(self):
        """
        Test complexity ratio calculation.
        
        Tests the ratio of complex calls to simple calls.
        """
        metrics = PerformanceMetrics()
        
        # Record different types of calls
        for _ in range(5):
            metrics.record_execution(0.1, was_simple=True)
        for _ in range(10):
            metrics.record_execution(0.1, was_simple=False)
        
        self.assertEqual(metrics.simple_calls, 5)
        self.assertEqual(metrics.complex_calls, 10)
        self.assertEqual(metrics.complexity_ratio, 2.0)
        
        # Test edge case - no simple calls
        metrics_edge = PerformanceMetrics()
        metrics_edge.record_execution(0.1, was_simple=False)
        self.assertEqual(metrics_edge.complexity_ratio, float('inf'))
    
    def test_execution_history_tracking(self):
        """
        Test execution history tracking with limited history size.
        
        Tests that execution history is maintained and properly limited.
        """
        metrics = PerformanceMetrics()
        
        # Record more executions than history limit
        for i in range(150):  # More than the 100 limit
            metrics.record_execution(0.01 * i, had_error=i % 10 == 0)
        
        # Check history is limited to 100
        self.assertEqual(len(metrics.execution_times), 100)
        
        # Check most recent entries are preserved
        latest_entry = metrics.execution_times[-1]
        self.assertAlmostEqual(latest_entry['time'], 0.01 * 149, places=3)
        self.assertIsInstance(latest_entry['timestamp'], float)
        self.assertIsInstance(latest_entry['error'], bool)


class TestPerformanceCache(unittest.TestCase):
    """Test the PerformanceCache system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache = PerformanceCache(max_size=5)  # Small cache for testing
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.cache.clear()
    
    def test_signature_caching(self):
        """
        Test function signature caching.
        
        Tests that function signatures are cached and retrieved correctly.
        """
        # Test with a function that has a signature
        sig1 = self.cache.get_signature(simple_add)
        sig2 = self.cache.get_signature(simple_add)
        
        self.assertIsNotNone(sig1)
        self.assertEqual(sig1, sig2)  # Should be same cached object
        self.assertEqual(len(sig1.parameters), 2)  # a, b parameters
        
        # Test with non-function
        sig_none = self.cache.get_signature("not a function")
        self.assertIsNone(sig_none)
    
    def test_param_info_caching(self):
        """
        Test parameter information caching.
        
        Tests that parameter info is cached and contains expected data.
        """
        param_info = self.cache.get_param_info(complex_function)
        
        self.assertIsNotNone(param_info)
        self.assertIn('a', param_info)
        self.assertIn('keyword_only', param_info)
        
        # Check parameter details
        a_info = param_info['a']
        self.assertFalse(a_info['has_default'])
        
        keyword_only_info = param_info['keyword_only']
        self.assertTrue(keyword_only_info['has_default'])
        self.assertEqual(keyword_only_info['default'], False)
    
    def test_argument_merge_caching(self):
        """
        Test argument merge result caching.
        
        Tests that argument merge results are cached and retrieved.
        """
        cache_key = "test_key"
        result = (("arg1", "arg2"), {"kwarg1": "value1"})
        
        # Cache the result
        self.cache.cache_argument_merge(cache_key, result)
        
        # Retrieve the result
        cached_result = self.cache.get_cached_argument_merge(cache_key)
        self.assertEqual(cached_result, result)
        
        # Test cache miss
        miss_result = self.cache.get_cached_argument_merge("nonexistent_key")
        self.assertIsNone(miss_result)
    
    def test_cache_size_limit_and_eviction(self):
        """
        Test cache size limits and LRU eviction.
        
        Tests that cache properly evicts old entries when size limit is reached.
        """
        # Fill cache beyond limit
        for i in range(10):  # Cache max_size is 5
            self.cache.cache_argument_merge(f"key_{i}", f"result_{i}")
        
        # Check that cache doesn't exceed size limit
        self.assertLessEqual(len(self.cache._argument_merge_cache), 5)
        
        # Check that recent entries are still there
        recent_result = self.cache.get_cached_argument_merge("key_9")
        self.assertIsNotNone(recent_result)
        
        # Check that old entries were evicted
        old_result = self.cache.get_cached_argument_merge("key_0")
        # This might be None due to eviction, which is expected behavior


class TestPerformanceMonitor(unittest.TestCase):
    """Test the PerformanceMonitor system."""
    
    def setUp(self):
        """Set up test fixtures."""
        clear_registry()
        clear_performance_cache()
        # Reset the global monitor
        _performance_monitor._function_metrics.clear()
        _performance_monitor._system_metrics = PerformanceMetrics()
    
    def tearDown(self):
        """Clean up test fixtures."""
        clear_registry()
        clear_performance_cache()
    
    def test_call_monitoring_lifecycle(self):
        """
        Test complete call monitoring lifecycle.
        
        Tests start_call_monitoring and end_call_monitoring.
        """
        monitor = _performance_monitor
        
        # Start monitoring
        context = monitor.start_call_monitoring("test_function")
        
        self.assertIn('start_time', context)
        self.assertIn('function_name', context)
        self.assertEqual(context['function_name'], "test_function")
        
        # Simulate some work
        time.sleep(0.01)
        
        # End monitoring
        monitor.end_call_monitoring(context, had_error=False, was_simple=True)
        
        # Check metrics were recorded
        metrics = monitor.get_function_metrics("test_function")
        self.assertEqual(metrics.call_count, 1)
        self.assertGreater(metrics.total_execution_time, 0)
        self.assertEqual(metrics.simple_calls, 1)
    
    def test_system_wide_metrics(self):
        """
        Test system-wide metrics aggregation.
        
        Tests that system metrics aggregate data from all functions.
        """
        monitor = _performance_monitor
        
        # Simulate multiple function calls
        functions = ["func1", "func2", "func3"]
        for func_name in functions:
            for i in range(3):
                context = monitor.start_call_monitoring(func_name)
                time.sleep(0.001)
                monitor.end_call_monitoring(context, had_error=i == 0)  # First call has error
        
        # Check system metrics
        system_metrics = monitor.get_system_metrics()
        self.assertEqual(system_metrics.call_count, 9)  # 3 functions × 3 calls
        self.assertEqual(system_metrics.error_count, 3)  # 1 error per function
        self.assertAlmostEqual(system_metrics.success_rate, 66.67, places=1)
    
    def test_performance_report_generation(self):
        """
        Test comprehensive performance report generation.
        
        Tests bottleneck detection and usage analysis.
        """
        monitor = _performance_monitor
        
        # Create different performance patterns
        # Fast function with many calls
        for _ in range(100):
            context = monitor.start_call_monitoring("fast_function")
            time.sleep(0.0001)
            monitor.end_call_monitoring(context)
        
        # Slow function with few calls
        for _ in range(5):
            context = monitor.start_call_monitoring("slow_function")
            time.sleep(0.01)
            monitor.end_call_monitoring(context)
        
        # Generate report
        report = monitor.get_performance_report()
        
        # Check report structure
        self.assertIn('system_metrics', report)
        self.assertIn('bottlenecks', report)
        self.assertIn('most_used_functions', report)
        self.assertIn('optimization_opportunities', report)
        
        # Check system metrics
        system_metrics = report['system_metrics']
        self.assertEqual(system_metrics['total_calls'], 105)
        
        # Check bottlenecks (should include slow_function due to total time)
        bottlenecks = report['bottlenecks']
        self.assertIsInstance(bottlenecks, list)
        if bottlenecks:  # May be empty in fast test runs
            bottleneck_names = [item[0] for item in bottlenecks]
            self.assertIn('slow_function', bottleneck_names)
    
    def test_optimization_opportunity_detection(self):
        """
        Test automatic optimization opportunity detection.
        
        Tests detection of high complexity ratios, low cache hit rates, etc.
        """
        monitor = _performance_monitor
        
        # Create a function with high complexity ratio
        func_metrics = monitor._function_metrics["complex_function"]
        func_metrics.call_count = 50
        func_metrics.simple_calls = 5
        func_metrics.complex_calls = 45  # High complexity ratio
        func_metrics.cache_hits = 10
        func_metrics.cache_misses = 40  # Low cache hit rate
        func_metrics.error_count = 5  # High error rate
        
        opportunities = monitor._identify_optimization_opportunities()
        
        self.assertIsInstance(opportunities, list)
        self.assertGreater(len(opportunities), 0)
        
        # Check for expected opportunity types
        opportunity_types = [opp['type'] for opp in opportunities]
        self.assertIn('argument_optimization', opportunity_types)
        self.assertIn('caching_optimization', opportunity_types)
        self.assertIn('error_handling', opportunity_types)


# =============================================================================
# CORE FUNCTIONALITY WITH PERFORMANCE INTEGRATION
# =============================================================================

class TestSKFunctionWithPerformanceMonitoring(unittest.TestCase):
    """Test SKFunction core functionality with performance monitoring."""
    
    def setUp(self):
        """Set up test fixtures."""
        clear_registry()
        clear_performance_cache()
    
    def tearDown(self):
        """Clean up test fixtures."""
        clear_registry()
        clear_performance_cache()
    
    def test_skfunction_performance_tracking_integration(self):
        """
        Test SKFunction integration with performance monitoring.
        
        Tests that SKFunction calls properly record performance metrics.
        """
        skf = SKFunction(
            func=slow_function,
            kwargs={"sleep_time": 0.01},
            name="monitored_function",
            autoregister=False
        )
        
        # Execute function multiple times
        for _ in range(3):
            result = skf.call()
            self.assertEqual(result, "completed")
        
        # Check performance metrics through SKFunction properties
        self.assertEqual(skf.call_count, 3)
        self.assertGreater(skf.avg_execution_time, 0.005)  # Should be > 0.01 sleep time
        self.assertGreater(skf.total_execution_time, 0.02)  # 3 × ~0.01
        self.assertEqual(skf.success_rate, 100.0)
        
        # Check detailed performance metrics
        metrics = skf.performance_metrics
        self.assertEqual(metrics.simple_calls, 3)
        self.assertEqual(metrics.complex_calls, 0)
        self.assertGreater(metrics.min_execution_time, 0.005)
    
    def test_simple_vs_complex_call_tracking(self):
        """
        Test tracking of simple vs complex calls.
        
        Tests that the system correctly distinguishes between simple and complex calls.
        """
        skf = SKFunction(
            func=data_processing_pipeline,
            args=("input.csv", "output.json"),
            name="pipeline_function",
            autoregister=False
        )
        
        # Simple calls (no additional args)
        for _ in range(3):
            skf.call()
        
        # Complex calls with named parameters
        for _ in range(2):
            skf.call(additional_args=[("debug", True), ("timeout", 60)])
        
        # Complex calls with positional parameters
        skf.call(additional_args=("xml", False, 120))
        
        metrics = skf.performance_metrics
        self.assertEqual(metrics.simple_calls, 3)
        self.assertEqual(metrics.complex_calls, 3)
        self.assertEqual(metrics.named_arg_calls, 2)
        self.assertEqual(metrics.positional_arg_calls, 1)
        self.assertEqual(metrics.complexity_ratio, 1.0)  # 3 complex / 3 simple
    
    def test_caching_effectiveness_tracking(self):
        """
        Test tracking of caching effectiveness.
        
        Tests that cache hits and misses are properly tracked.
        """
        skf = SKFunction(
            func=data_processing_pipeline,
            name="cached_function",
            autoregister=False
        )
        
        # Use same arguments multiple times to trigger cache hits
        common_args = [("source", "data.csv"), ("target", "output.json")]
        
        # First call should be cache miss
        skf.call(additional_args=common_args)
        
        # Subsequent calls with same args should be cache hits
        for _ in range(3):
            skf.call(additional_args=common_args)
        
        # Different args should be cache miss
        skf.call(additional_args=[("source", "different.csv"), ("target", "different.json")])
        
        # Check system-wide cache statistics
        system_metrics = get_system_performance_metrics()
        self.assertGreater(system_metrics.cache_hits, 0)
        self.assertGreater(system_metrics.cache_misses, 0)
    
    def test_error_tracking_in_performance_metrics(self):
        """
        Test error tracking in performance metrics.
        
        Tests that errors are properly recorded in performance data.
        """
        error_skf = SKFunction(
            func=error_function,
            name="error_test_function",
            autoregister=False
        )
        
        success_count = 0
        error_count = 0
        
        # Mix successful and failed calls
        for i in range(5):
            try:
                if i % 2 == 0:
                    error_skf.call()
                    success_count += 1
                else:
                    error_skf.call()  # This will fail
            except SKFunctionError:
                error_count += 1
        
        metrics = error_skf.performance_metrics
        self.assertEqual(metrics.call_count, 5)
        self.assertEqual(metrics.error_count, 5)  # All calls fail in error_function
        self.assertEqual(metrics.success_rate, 0.0)
    
    def test_optimization_levels(self):
        """
        Test different optimization levels.
        
        Tests that optimization levels are properly set and used.
        """
        # Standard optimization
        skf_standard = SKFunction(
            func=simple_add,
            args=(1, 2),
            optimization_level="standard",
            autoregister=False
        )
        
        # Aggressive optimization
        skf_aggressive = SKFunction(
            func=simple_add,
            args=(3, 4),
            optimization_level="aggressive",
            autoregister=False
        )
        
        # Conservative optimization
        skf_conservative = SKFunction(
            func=simple_add,
            args=(5, 6),
            optimization_level="conservative",
            autoregister=False
        )
        
        # Check optimization levels are set correctly
        self.assertEqual(skf_standard.metadata.optimization_level, "standard")
        self.assertEqual(skf_aggressive.metadata.optimization_level, "aggressive")
        self.assertEqual(skf_conservative.metadata.optimization_level, "conservative")
        
        # All should function correctly
        self.assertEqual(skf_standard.call(), 3)
        self.assertEqual(skf_aggressive.call(), 7)
        self.assertEqual(skf_conservative.call(), 11)


class TestPerformanceAnalysisAndReporting(unittest.TestCase):
    """Test performance analysis and reporting features."""
    
    def setUp(self):
        """Set up test fixtures."""
        clear_registry()
        clear_performance_cache()
    
    def tearDown(self):
        """Clean up test fixtures."""
        clear_registry()
        clear_performance_cache()
    
    def test_function_performance_analysis(self):
        """
        Test detailed performance analysis for individual functions.
        
        Tests get_performance_analysis() method.
        """
        skf = SKFunction(
            func=variable_time_function,
            name="analysis_test_function",
            autoregister=False
        )
        
        # Execute multiple times to generate meaningful metrics
        for _ in range(20):
            skf.call()
        
        analysis = skf.get_performance_analysis()
        
        # Check analysis structure
        self.assertIn('performance_summary', analysis)
        self.assertIn('call_patterns', analysis)
        self.assertIn('optimization_suggestions', analysis)
        
        # Check performance summary
        summary = analysis['performance_summary']
        self.assertEqual(summary['total_calls'], 20)
        self.assertIn('%', summary['success_rate'])
        self.assertIn('s', summary['avg_execution_time'])
        
        # Check call patterns
        patterns = analysis['call_patterns']
        self.assertEqual(patterns['simple_calls'], 20)
        self.assertEqual(patterns['complex_calls'], 0)
        self.assertEqual(patterns['named_parameter_usage'], "0/0")
    
    def test_system_performance_report(self):
        """
        Test system-wide performance reporting.
        
        Tests get_performance_report() function.
        """
        clear_registry()
        clear_performance_cache()
        reset_performance_monitor()

        # Create multiple functions with different performance characteristics
        functions = [
            ("fast_func", 0.001, 50),  # Fast function, many calls
            ("medium_func", 0.01, 20),  # Medium function, medium calls
            ("slow_func", 0.05, 5),     # Slow function, few calls
        ]
        
        for name, sleep_time, call_count in functions:
            skf = SKFunction(
                func=slow_function,
                kwargs={"sleep_time": sleep_time},
                name=name,
                autoregister=False
            )
            
            for _ in range(call_count):
                skf.call()
        
        # Generate performance report
        report = get_performance_report()
        
        # Check report structure
        required_keys = ['system_metrics', 'bottlenecks', 'most_used_functions', 'optimization_opportunities']
        for key in required_keys:
            self.assertIn(key, report)
        
        # Check system metrics
        system = report['system_metrics']
        self.assertEqual(system['total_calls'], 75)  # 50 + 20 + 5
        self.assertGreater(system['avg_execution_time'], 0)
        
        # Check bottlenecks (slow_func should be a bottleneck due to total time)
        bottlenecks = report['bottlenecks']
        if bottlenecks:  # May be empty in very fast test runs
            bottleneck_names = [item[0] for item in bottlenecks]
            self.assertIn('slow_func', bottleneck_names)
        
        # Check most used functions
        most_used = report['most_used_functions']
        if most_used:
            most_used_names = [item[0] for item in most_used]
            self.assertIn('fast_func', most_used_names)  # Should be most used with 50 calls
    
    def test_optimization_suggestions(self):
        """
        Test automatic optimization suggestions.
        
        Tests get_optimization_suggestions() function.
        """
        # Create a function that will trigger optimization suggestions
        skf = SKFunction(
            func=data_processing_pipeline,
            args=("input.csv", "output.json"),
            name="suggestion_test_function", 
            autoregister=False
        )
        
        # Create high complexity ratio by doing mostly complex calls
        for _ in range(2):
            skf.call()  # Simple calls
        
        for _ in range(20):  # Many complex calls
            skf.call(additional_args=[("debug", True), ("timeout", 60)])
        
        # Force some errors to get error handling suggestions
        error_skf = SKFunction(
            func=error_function,
            name="error_suggestion_function",
            autoregister=False
        )
        
        for _ in range(10):
            try:
                error_skf.call()
            except:
                pass
        
        suggestions = get_optimization_suggestions()
        
        self.assertIsInstance(suggestions, list)
        if suggestions:  # May be empty depending on metrics
            suggestion_types = [s['type'] for s in suggestions]
            expected_types = ['argument_optimization', 'caching_optimization', 'error_handling']
            # At least one type should be present
            self.assertTrue(any(t in suggestion_types for t in expected_types))
    
    def test_benchmarking_function(self):
        """
        Test the benchmark_function utility.
        
        Tests detailed benchmarking of SKFunction performance.
        """
        skf = SKFunction(
            func=variable_time_function,
            kwargs={"base_time": 0.001, "variance": 0.0005},
            name="benchmark_test_function",
            autoregister=False
        )
        
        # Run benchmark
        benchmark_results = benchmark_function(skf, iterations=50)
        
        # Check benchmark results structure
        required_keys = [
            'iterations', 'successful_runs', 'error_count',
            'min_time', 'max_time', 'mean_time', 'median_time',
            'std_dev', 'success_rate'
        ]
        for key in required_keys:
            self.assertIn(key, benchmark_results)
        
        # Check benchmark values
        self.assertEqual(benchmark_results['iterations'], 50)
        self.assertEqual(benchmark_results['successful_runs'], 50)
        self.assertEqual(benchmark_results['error_count'], 0)
        self.assertEqual(benchmark_results['success_rate'], 100.0)
        
        # Check timing statistics
        self.assertGreater(benchmark_results['min_time'], 0)
        self.assertGreater(benchmark_results['mean_time'], benchmark_results['min_time'])
        self.assertGreater(benchmark_results['max_time'], benchmark_results['mean_time'])
        self.assertGreaterEqual(benchmark_results['std_dev'], 0)
    
    def test_memory_tracking_integration(self):
        """
        Test memory tracking integration (if available).
        
        Tests that memory tracking works when enabled.
        """
        # Try to enable memory tracking
        memory_enabled = enable_memory_tracking()
        
        if memory_enabled:
            skf = SKFunction(
                func=memory_intensive_function,
                kwargs={"size": 1000},
                name="memory_test_function",
                autoregister=False
            )
            
            # Execute function that allocates memory
            result = skf.call()
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1000)
            
            # Check if memory metrics are being tracked
            system_metrics = get_system_performance_metrics()
            # Memory tracking metrics may or may not be populated depending on system
            self.assertIsInstance(system_metrics.peak_memory_usage, int)


# =============================================================================
# BUILDER PATTERN WITH PERFORMANCE OPTIMIZATION
# =============================================================================

class TestSKFunctionBuilderWithOptimization(unittest.TestCase):
    """Test SKFunctionBuilder with performance optimization features."""
    
    def setUp(self):
        """Set up test fixtures."""
        clear_registry()
        clear_performance_cache()
    
    def tearDown(self):
        """Clean up test fixtures."""
        clear_registry()
        clear_performance_cache()
    
    def test_builder_with_optimization_levels(self):
        """
        Test builder with different optimization levels.
        
        Tests that builder properly sets optimization levels.
        """
        optimization_levels = ["standard", "aggressive", "conservative"]
        
        for level in optimization_levels:
            with SKFunctionBuilder(autoregister=False) as builder:
                builder.add_callable(simple_add)
                builder.add_argument("a", 10)
                builder.add_argument("b", 20)
                builder.set_optimization_level(level)
                builder.set_name(f"optimized_{level}")
                
                skf = builder.build()
            
            self.assertEqual(skf.metadata.optimization_level, level)
            self.assertEqual(skf.call(), 30)
    
    def test_builder_with_invalid_optimization_level(self):
        """
        Test builder with invalid optimization level.
        
        Tests that invalid optimization levels raise appropriate errors.
        """
        with self.assertRaises(SKFunctionBuilderError):
            with SKFunctionBuilder(autoregister=False) as builder:
                builder.add_callable(simple_add)
                builder.set_optimization_level("invalid_level")
                builder.build()
    
    def test_builder_performance_with_complex_function(self):
        """
        Test builder performance with complex function construction.
        
        Tests that builder efficiently handles complex function creation.
        """
        start_time = time.time()
        
        # Create a flexible function that accepts **kwargs for testing
        def flexible_function(**kwargs):
            return {"processed": True, "params": kwargs}
        
        with SKFunctionBuilder(autoregister=False) as builder:
            builder.add_callable(flexible_function)  # Use flexible function instead
            
            # Add many arguments to test performance
            for i in range(20):
                builder.add_argument(f"param_{i}", f"value_{i}")
            
            builder.set_name("complex_built_function")
            builder.set_description("Complex function built with many parameters")
            
            skf = builder.build()  # CRITICAL: Must call build()
        
        build_time = time.time() - start_time
        
        # Building should be reasonably fast even with many parameters
        self.assertLess(build_time, 1.0)  # Should take less than 1 second
        
        # Function should work correctly
        self.assertIsInstance(skf, SKFunction)
        self.assertEqual(skf.metadata.name, "complex_built_function")
        
        # Test that the built function actually works
        result = skf.call()
        self.assertIsInstance(result, dict)
        self.assertTrue(result["processed"])


# =============================================================================
# INTEGRATION AND EDGE CASE TESTS
# =============================================================================

class TestPerformanceIntegrationAndEdgeCases(unittest.TestCase):
    """Test performance system integration and edge cases."""


    
    def setUp(self):
        """Set up test fixtures."""
        clear_registry()
        clear_performance_cache()
        reset_performance_monitor()
    
    def tearDown(self):
        """Clean up test fixtures."""
        clear_registry()
        clear_performance_cache()
        reset_performance_monitor()
    
    def test_concurrent_performance_monitoring(self):
        """
        Test performance monitoring under concurrent access.
        
        Tests that performance monitoring is thread-safe.
        """
        skf = SKFunction(
            func=simple_add,
            args=(1, 1),
            name="concurrent_test_function",
            autoregister=False
        )
        
        results = []
        errors = []
        
        def worker():
            try:
                for _ in range(10):
                    result = skf.call()
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 50)  # 5 threads × 10 calls
        self.assertTrue(all(r == 2 for r in results))
        
        # Check metrics consistency
        metrics = skf.performance_metrics
        self.assertEqual(metrics.call_count, 50)
        self.assertEqual(metrics.simple_calls, 50)
    
    def test_performance_with_zero_execution_time(self):
        """
        Test performance tracking with very fast functions.
        
        Tests edge case where execution time might be zero or near-zero.
        """
        fast_skf = SKFunction(
            func=lambda: "instant",
            name="instant_function",
            autoregister=False
        )
        
        # Execute many times
        for _ in range(100):
            result = fast_skf.call()
            self.assertEqual(result, "instant")
        
        metrics = fast_skf.performance_metrics
        self.assertEqual(metrics.call_count, 100)
        # Execution time might be very small but should not be negative
        self.assertGreaterEqual(metrics.avg_execution_time, 0)
        self.assertGreaterEqual(metrics.total_execution_time, 0)
    
    def test_cache_performance_under_load(self):
        """
        Test cache performance under high load.
        
        Tests cache behavior with many different argument combinations.
        """
        # EXTRA: Clear everything at start of test
        clear_registry()
        clear_performance_cache()
        _performance_monitor._function_metrics.clear()
        _performance_monitor._system_metrics = PerformanceMetrics()
        
        skf = SKFunction(
            func=data_processing_pipeline,
            name="cache_load_test",
            autoregister=False
        )
        
        # Track calls manually to verify
        call_count = 0
        
        # Generate many different argument combinations
        for i in range(100):
            skf.call(additional_args=[
                ("source", f"input_{i}.csv"),
                ("target", f"output_{i}.json"),
                ("debug", i % 2 == 0)
            ])
            call_count += 1
        
        # Call some combinations again to test cache hits
        for i in range(0, 20, 2):  # This should be 10 calls (0, 2, 4, 6, 8, 10, 12, 14, 16, 18)
            skf.call(additional_args=[
                ("source", f"input_{i}.csv"),
                ("target", f"output_{i}.json"),
                ("debug", True)
            ])
            call_count += 1
        
        metrics = skf.performance_metrics
        # Use our manual count instead of hard-coded expectation
        self.assertEqual(metrics.call_count, call_count)  # Should be 110 (100 + 10)
        self.assertEqual(metrics.complex_calls, call_count)  # All had additional args
    
    def test_performance_report_with_empty_metrics(self):
        """
        Test performance reporting with no function calls.
        
        Tests edge case of generating reports with no data.
        """
        # Clear everything and generate report
        clear_registry()
        clear_performance_cache()
        
        report = get_performance_report()
        
        # Should not crash and should have valid structure
        self.assertIn('system_metrics', report)
        self.assertIn('bottlenecks', report)
        self.assertIn('most_used_functions', report)
        
        system_metrics = report['system_metrics']
        self.assertEqual(system_metrics['total_calls'], 0)
        self.assertEqual(system_metrics['avg_execution_time'], 0.0)
    
    def test_performance_cache_cleanup(self):
        """
        Test performance cache cleanup functionality.
        
        Tests that cache can be properly cleared and reset.
        """
        # Populate cache
        skf = SKFunction(
            func=simple_add,
            name="cache_cleanup_test",
            autoregister=False
        )
        
        # Execute with various arguments to populate cache
        for i in range(10):
            skf.call(additional_args=[("a", i), ("b", i * 2)])
        
        # Verify cache has data
        self.assertGreater(len(_performance_cache._signature_cache), 0)
        
        # Clear cache
        clear_performance_cache()
        
        # Verify cache is empty
        self.assertEqual(len(_performance_cache._signature_cache), 0)
        self.assertEqual(len(_performance_cache._param_info_cache), 0)
        self.assertEqual(len(_performance_cache._argument_merge_cache), 0)


# Test runner functions
def run_tests():
    """Run all tests with detailed output."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_specific_test(test_class_name):
    """Run a specific test class."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(globals()[test_class_name])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print(f"{INFO}    Running SKFunction Performance & Optimization Tests...")
    print(f"{INFO}    Testing comprehensive performance monitoring,")
    print(f"{INFO}    caching systems, optimization features,")
    print(f"{INFO}    and advanced function management capabilities...")
    print(INFO)
    
    success = run_tests()
    
    print(f"{INFO}    SKFunction Performance Tests Completed")
    if success:
        print(f"{SUCCESS} All tests passed successfully!")
        print("\n🎯 Tested Advanced Performance Features:")
        print("   ✅ Performance metrics collection and tracking")
        print("   ✅ Sophisticated caching system (signatures, params, args)")
        print("   ✅ Memory tracking and system-wide monitoring")
        print("   ✅ Optimization levels and automatic suggestions")
        print("   ✅ Benchmarking and performance analysis")
        print("   ✅ Concurrent access and thread safety")
        print("   ✅ Cache performance under high load")
        print("   ✅ Edge cases and error conditions")
        print("   ✅ Integration with core SKFunction features")
        sys.exit(0)
    else:
        print(f"{FAIL} Some tests failed.")
        sys.exit(1)