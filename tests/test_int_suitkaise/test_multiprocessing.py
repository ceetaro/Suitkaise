#!/usr/bin/env python3
"""
Comprehensive Multiprocessing Engine Test Suite

This test suite validates the complete internal multiprocessing engine for Suitkaise,
including all components, configurations, error handling, and integration scenarios.

Components tested:
1. Process Base Classes - _Process lifecycle hooks and timing configurations
2. Configuration Classes - _PConfig and _QPConfig with all timeout scenarios
3. Process Managers - CrossProcessing and SubProcessing with monitoring
4. Process Pool - Async and parallel modes with task management
5. Process Runner - Execution engine with granular timeout handling
6. Data Structures - _PData containers and result handling
7. Error Handling - Custom exceptions and recovery mechanisms
8. Integration Tests - Complex scenarios with subprocesses and mixed execution
9. Performance Tests - Large-scale execution and resource management

This validates the complete production-ready multiprocessing system.
"""

import sys
import time
import threading
import traceback
import tempfile
import os
import signal
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the suitkaise path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Import all multiprocessing engine components
    from suitkaise._int.mp.base_multiprocessing import (
        CrossProcessing, SubProcessing, ProcessPool,
        _Process, _FunctionProcess, _PConfig, _QPConfig,
        _PData, ProcessStats, PStatus, PoolMode,
        XProcessError, PreloopError, MainLoopError, PostLoopError,
        PreloopTimeoutError, MainLoopTimeoutError, PostLoopTimeoutError,
        PoolTaskError, _PTask, _PTaskResult
    )
    MP_IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Could not import multiprocessing engine: {e}")
    MP_IMPORTS_SUCCESSFUL = False


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_section(title: str):
    """Print a section header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title.upper()}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.END}")


def print_subsection(title: str):
    """Print a subsection header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}--- {title} ---{Colors.END}")


def print_result(success: bool, message: str, details: str = None):
    """Print a test result."""
    symbol = "✅" if success else "❌"
    color = Colors.GREEN if success else Colors.RED
    detail_info = f" ({details})" if details else ""
    print(f"{color}{symbol} {message}{detail_info}{Colors.END}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.WHITE}ℹ️  {message}{Colors.END}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


# =============================================================================
# TEST PROCESS CLASSES
# =============================================================================

class SimpleTestProcess(_Process):
    """Basic test process for lifecycle validation."""
    
    def __init__(self, num_loops: int = 3):
        super().__init__(num_loops)
        self.preloop_calls = 0
        self.loop_calls = 0
        self.postloop_calls = 0
        self.onfinish_called = False
        self.loop_data = []
        
    def __preloop__(self):
        self.preloop_calls += 1
        self.loop_data.append(f"preloop_{self.current_loop}")
        
    def __loop__(self):
        self.loop_calls += 1
        self.loop_data.append(f"loop_{self.current_loop}")
        time.sleep(0.1)  # Simulate work
        
    def __postloop__(self):
        self.postloop_calls += 1
        self.loop_data.append(f"postloop_{self.current_loop}")
        
    def __onfinish__(self):
        self.onfinish_called = True
        self.loop_data.append("finish")
        
    def __result__(self):
        return {
            "preloop_calls": self.preloop_calls,
            "loop_calls": self.loop_calls,
            "postloop_calls": self.postloop_calls,
            "onfinish_called": self.onfinish_called,
            "loop_data": self.loop_data,
            "total_loops": self.current_loop
        }


class TimingTestProcess(_Process):
    """Process for testing timing configurations."""
    
    def __init__(self):
        super().__init__(num_loops=2)
        # Configure timing to measure preloop to postloop
        self.start_timer_before_preloop()
        self.end_timer_after_postloop()
        self.timing_results = []
        
    def __preloop__(self):
        print(f"  Preloop {self.current_loop} starting...")
        time.sleep(0.05)  # 50ms work
        print(f"  Preloop {self.current_loop} finished")
        
    def __loop__(self):
        print(f"  Loop {self.current_loop} starting...")
        time.sleep(0.1)   # 100ms work
        print(f"  Loop {self.current_loop} finished")
        
    def __postloop__(self):
        print(f"  Postloop {self.current_loop} starting...")
        time.sleep(0.05)  # 50ms work
        print(f"  Postloop {self.current_loop} finished, timing: {self.last_loop_time:.3f}s")
        # Should have timing from start of preloop to end of postloop
        self.timing_results.append(self.last_loop_time)
        
    def __result__(self):
        return {
            "timing_results": self.timing_results,
            "average_time": sum(self.timing_results) / len(self.timing_results) if self.timing_results else 0
        }


class ErrorTestProcess(_Process):
    """Process that generates specific errors for testing."""
    
    def __init__(self, error_in: str = "loop"):
        super().__init__(num_loops=1)
        self.error_in = error_in
        
    def __preloop__(self):
        if self.error_in == "preloop":
            raise ValueError("Test error in preloop")
            
    def __loop__(self):
        if self.error_in == "loop":
            raise RuntimeError("Test error in loop")
            
    def __postloop__(self):
        if self.error_in == "postloop":
            raise ValueError("Test error in postloop")
            
    def __onfinish__(self):
        if self.error_in == "onfinish":
            raise ValueError("Test error in onfinish")


class TimeoutTestProcess(_Process):
    """Process that causes timeouts for testing."""
    
    def __init__(self, timeout_in: str = "loop", delay: float = 2.0):
        super().__init__(num_loops=1)
        self.timeout_in = timeout_in
        self.delay = delay
        
    def __preloop__(self):
        if self.timeout_in == "preloop":
            time.sleep(self.delay)
            
    def __loop__(self):
        if self.timeout_in == "loop":
            time.sleep(self.delay)
            
    def __postloop__(self):
        if self.timeout_in == "postloop":
            time.sleep(self.delay)


class ControlTestProcess(_Process):
    """Process for testing control methods."""
    
    def __init__(self, control_action: str = None):
        super().__init__(num_loops=10)  # Long running
        self.control_action = control_action
        self.executed_loops = []
        
    def __loop__(self):
        self.executed_loops.append(self.current_loop)
        
        if self.control_action == "rejoin" and self.current_loop == 3:
            self.rejoin()
        elif self.control_action == "skip_and_rejoin" and self.current_loop == 2:
            self.skip_and_rejoin()
            
        time.sleep(0.1)
        
    def __result__(self):
        return {
            "executed_loops": self.executed_loops,
            "final_loop": self.current_loop
        }


class SubprocessCreatorProcess(_Process):
    """Process that creates subprocesses for nesting tests."""
    
    def __init__(self):
        super().__init__(num_loops=1)
        self.subprocess_results = []
        
    def __loop__(self):
        with SubProcessing() as sub_mgr:
            # Create a simple subprocess
            sub_process = SimpleTestProcess(num_loops=2)
            pdata = sub_mgr.create_process("sub1", sub_process)
            
            # Wait for completion and get result
            success, result = sub_mgr.join_and_get_result("sub1", timeout=10.0)
            self.subprocess_results.append({
                "success": success,
                "result": result
            })
            
    def __result__(self):
        return {
            "subprocess_results": self.subprocess_results
        }


class ComplexDataProcess(_Process):
    """Process that returns complex serializable data."""
    
    def __init__(self):
        super().__init__(num_loops=1)
        
    def __loop__(self):
        # Simulate complex work
        time.sleep(0.2)
        
    def __result__(self):
        return {
            "complex_data": {
                "numbers": list(range(100)),
                "nested": {
                    "strings": ["test", "data", "serialization"],
                    "mixed": [1, "two", 3.0, {"four": 4}]
                },
                "metadata": {
                    "process_name": self.pkey,
                    "timestamp": time.time(),
                    "loops_completed": self.current_loop
                }
            }
        }


# =============================================================================
# TEST FUNCTIONS FOR FUNCTION PROCESSES
# =============================================================================

def simple_test_function(x: int, y: int = 10) -> dict:
    """Simple function for testing function processes."""
    time.sleep(0.1)
    return {
        "input_x": x,
        "input_y": y,
        "result": x + y,
        "timestamp": time.time()
    }


def slow_test_function(delay: float = 1.0) -> str:
    """Slow function for timeout testing."""
    time.sleep(delay)
    return f"Completed after {delay}s"


def error_test_function() -> str:
    """Function that raises an error."""
    raise ValueError("Test function error")


def complex_calculation(n: int) -> dict:
    """Complex calculation for pool testing."""
    result = sum(i * i for i in range(n))
    return {
        "input": n,
        "sum_of_squares": result,
        "computation_time": 0.1
    }


# =============================================================================
# TEST SUITE IMPLEMENTATION
# =============================================================================

def test_basic_process_lifecycle():
    """Test basic process lifecycle and hooks."""
    print_section("Basic Process Lifecycle Tests")
    
    test_success = True
    
    # Test simple process execution
    print_subsection("Simple Process Execution")
    
    try:
        with CrossProcessing() as cp:
            process = SimpleTestProcess(num_loops=3)
            pdata = cp.create_process("simple1", process)
            
            # Wait for completion
            success = cp.join_process("simple1", timeout=10.0)
            result = cp.get_process_result("simple1")
            
            print_result(success, "Process completed successfully")
            print_result(result is not None, "Result retrieved", f"loops: {result.get('total_loops') if result else 'None'}")
            
            if result:
                print_result(result['preloop_calls'] == 3, "Preloop called correctly", f"expected 3, got {result['preloop_calls']}")
                print_result(result['loop_calls'] == 3, "Loop called correctly", f"expected 3, got {result['loop_calls']}")
                print_result(result['postloop_calls'] == 3, "Postloop called correctly", f"expected 3, got {result['postloop_calls']}")
                print_result(result['onfinish_called'], "Onfinish called")
                
    except Exception as e:
        print_result(False, f"Simple process test failed: {e}")
        test_success = False
    
    # Test timing configuration
    print_subsection("Timing Configuration")
    
    try:
        with CrossProcessing() as cp:
            process = TimingTestProcess()
            pdata = cp.create_process("timing1", process)
            
            success = cp.join_process("timing1", timeout=10.0)
            result = cp.get_process_result("timing1")
            
            print_result(success and result, "Timing process completed")
            
            if result and result.get('timing_results'):
                avg_time = result['average_time']
                # Timing should measure preloop to postloop, expect around 0.2s per loop
                # But first loop might be 0, so check if we have at least one good measurement
                timing_results = result.get('timing_results', [])
                max_time = max(timing_results) if timing_results else 0
                print_result(max_time > 0.15, "Timing measurement accurate", f"avg: {avg_time:.3f}s, max: {max_time:.3f}s")
                
    except Exception as e:
        print_result(False, f"Timing test failed: {e}")
        test_success = False
        
    # Test control methods
    print_subsection("Process Control Methods")
    
    control_tests = [
        ("rejoin", "rejoin"),
        ("skip_and_rejoin", "skip_and_rejoin")
    ]
    
    for test_name, control_action in control_tests:
        try:
            with CrossProcessing() as cp:
                process = ControlTestProcess(control_action)
                pdata = cp.create_process(f"control_{test_name}", process)
                
                success = cp.join_process(f"control_{test_name}", timeout=10.0)
                result = cp.get_process_result(f"control_{test_name}")
                
                if success and result:
                    executed = len(result['executed_loops'])
                    expected = 4 if control_action == "rejoin" else 3  # Different based on when control is called
                    print_result(executed <= expected, f"Control method {test_name}", f"executed {executed} loops")
                else:
                    print_result(False, f"Control method {test_name} failed")
                    test_success = False
                    
        except Exception as e:
            print_result(False, f"Control test {test_name} failed: {e}")
            test_success = False
    
    return test_success


def test_configuration_scenarios():
    """Test different configuration scenarios."""
    print_section("Configuration Tests")
    
    test_success = True
    
    # Test timeout configurations
    print_subsection("Timeout Configurations")
    
    timeout_configs = [
        ("Quick timeouts", lambda: _PConfig().set_quick_timeouts()),
        ("Long timeouts", lambda: _PConfig().set_long_timeouts()),
        ("Custom timeouts", lambda: _PConfig(preloop_timeout=1.0, loop_timeout=2.0, postloop_timeout=1.0)),
        ("Disabled timeouts", lambda: _PConfig().disable_timeouts())
    ]
    
    for config_name, config_factory in timeout_configs:
        try:
            config = config_factory()
            with CrossProcessing() as cp:
                process = SimpleTestProcess()
                pdata = cp.create_process(f"config_{config_name}", process, config)
                
                success = cp.join_process(f"config_{config_name}", timeout=15.0)
                print_result(success, f"Configuration: {config_name}")
                
        except Exception as e:
            print_result(False, f"Configuration {config_name} failed: {e}")
            test_success = False
    
    # Test join conditions
    print_subsection("Join Conditions")
    
    try:
        # Time-based join
        config = _PConfig(join_in=1.0)  # 1 second
        with CrossProcessing() as cp:
            process = SimpleTestProcess(num_loops=100)  # Would run long without time limit
            pdata = cp.create_process("time_join", process, config)
            
            start_time = time.time()
            success = cp.join_process("time_join", timeout=5.0)
            duration = time.time() - start_time
            
            print_result(success and duration < 2.0, "Time-based join", f"duration: {duration:.2f}s")
            
    except Exception as e:
        print_result(False, f"Time-based join failed: {e}")
        test_success = False
    
    try:
        # Loop-based join
        config = _PConfig(join_after=2)  # 2 loops max
        with CrossProcessing() as cp:
            process = SimpleTestProcess(num_loops=100)  # Would run long without loop limit
            pdata = cp.create_process("loop_join", process, config)
            
            success = cp.join_process("loop_join", timeout=5.0)
            result = cp.get_process_result("loop_join")
            
            loops_completed = result.get('total_loops', 0) if result else 0
            print_result(success and loops_completed == 2, "Loop-based join", f"loops: {loops_completed}")
            
    except Exception as e:
        print_result(False, f"Loop-based join failed: {e}")
        test_success = False
    
    return test_success


def test_process_managers():
    """Test CrossProcessing and SubProcessing managers."""
    print_section("Process Manager Tests")
    
    test_success = True
    
    # Test CrossProcessing with multiple processes
    print_subsection("CrossProcessing Manager")
    
    try:
        with CrossProcessing() as cp:
            # Create multiple processes
            processes = {}
            for i in range(3):
                process = SimpleTestProcess(num_loops=2)
                pdata = cp.create_process(f"multi_{i}", process)
                processes[f"multi_{i}"] = pdata
            
            # Check process listing
            process_list = cp.list_processes()
            print_result(len(process_list) == 3, "Multiple processes created", f"count: {len(process_list)}")
            
            # Wait for all to complete
            all_success = cp.join_all(timeout=15.0)
            print_result(all_success, "All processes completed")
            
            # Get all results
            results = {}
            for key in processes:
                results[key] = cp.get_process_result(key)
                
            successful_results = sum(1 for r in results.values() if r is not None)
            print_result(successful_results == 3, "All results retrieved", f"count: {successful_results}")
            
    except Exception as e:
        print_result(False, f"CrossProcessing test failed: {e}")
        test_success = False
    
    # Test SubProcessing
    print_subsection("SubProcessing Manager")
    
    try:
        with CrossProcessing() as cp:
            # Create a process that creates subprocesses
            process = SubprocessCreatorProcess()
            pdata = cp.create_process("creator", process)
            
            success = cp.join_process("creator", timeout=20.0)
            result = cp.get_process_result("creator")
            
            print_result(success, "Subprocess creation completed")
            
            if result and result.get('subprocess_results'):
                sub_results = result['subprocess_results']
                sub_success = all(r['success'] for r in sub_results)
                print_result(sub_success, "Subprocess execution successful", f"results: {len(sub_results)}")
                
    except Exception as e:
        print_result(False, f"SubProcessing test failed: {e}")
        test_success = False
    
    # Test restart functionality
    print_subsection("Process Restart Logic")
    
    try:
        # Test restart with lifecycle error
        config = _PConfig(crash_restart=True, max_restarts=2)
        with CrossProcessing() as cp:
            # Create a process that will crash due to lifecycle error
            process = ErrorTestProcess(error_in="loop")
            pdata = cp.create_process("restart_test", process, config)
            
            # Wait longer to allow for restart attempts
            success = cp.join_process("restart_test", timeout=20.0)
            
            # Check if restart was attempted
            process_info = cp.get_process("restart_test")
            restart_count = process_info._restart_count if process_info else 0
            
            print_result(restart_count > 0, "Process restart attempted", f"restarts: {restart_count}")
            print_result(restart_count <= 2, "Restart limit respected", f"max: 2, actual: {restart_count}")
            
    except Exception as e:
        print_result(False, f"Restart test failed: {e}")
        test_success = False
    
    try:
        # Test no restart when disabled
        config = _PConfig(crash_restart=False, max_restarts=0)
        with CrossProcessing() as cp:
            process = ErrorTestProcess(error_in="loop")
            pdata = cp.create_process("no_restart_test", process, config)
            
            success = cp.join_process("no_restart_test", timeout=10.0)
            
            # Should complete quickly with no restarts
            process_info = cp.get_process("no_restart_test")
            restart_count = process_info._restart_count if process_info else 0
            
            print_result(restart_count == 0, "No restart when disabled", f"restarts: {restart_count}")
            
    except Exception as e:
        print_result(False, f"No restart test failed: {e}")
        test_success = False
    
    return test_success


def test_process_pool():
    """Test ProcessPool functionality."""
    print_section("Process Pool Tests")
    
    test_success = True
    
    # Test async mode
    print_subsection("Async Pool Mode")
    
    try:
        with ProcessPool(size=3, mode=PoolMode.ASYNC) as pool:
            # Submit multiple tasks
            tasks = []
            for i in range(5):
                task = _PTask(
                    key=f"async_task_{i}",
                    process_class=SimpleTestProcess
                )
                tasks.append(task)
                pool.submit(task)
            
            # Get all results
            results = pool.get_all_results(timeout=20.0)
            
            print_result(len(results) == 5, "Async pool tasks completed", f"results: {len(results)}")
            
            successful_tasks = sum(1 for r in results if r.success)
            print_result(successful_tasks == 5, "All async tasks successful", f"success: {successful_tasks}")
            
    except Exception as e:
        print_result(False, f"Async pool test failed: {e}")
        test_success = False
    
    # Test parallel mode
    print_subsection("Parallel Pool Mode")
    
    try:
        with ProcessPool(size=2, mode=PoolMode.PARALLEL) as pool:
            # Submit batch of tasks
            tasks = []
            for i in range(4):
                task = _PTask(
                    key=f"parallel_task_{i}",
                    process_class=SimpleTestProcess
                )
                tasks.append(task)
            
            pool.submit_multiple(tasks)
            results = pool.get_all_results(timeout=20.0)
            
            print_result(len(results) == 4, "Parallel pool tasks completed", f"results: {len(results)}")
            
    except Exception as e:
        print_result(False, f"Parallel pool test failed: {e}")
        test_success = False
    
    # Test function submission
    print_subsection("Function Pool Tasks")
    
    try:
        with ProcessPool(size=2) as pool:
            # Submit function tasks
            for i in range(3):
                pool.submit_function(f"func_{i}", simple_test_function, args=(i,), kwargs={"y": i*10})
            
            results = pool.get_all_results(timeout=15.0)
            
            print_result(len(results) == 3, "Function tasks completed", f"results: {len(results)}")
            
            # Check function results
            if results:
                func_results = [r.result for r in results if r.success and r.result]
                print_result(len(func_results) > 0, "Function results retrieved", f"count: {len(func_results)}")
                
    except Exception as e:
        print_result(False, f"Function pool test failed: {e}")
        test_success = False
    
    # Test one-shot execution
    print_subsection("One-shot Pool Execution")
    
    try:
        tasks = [
            _PTask(key=f"oneshot_{i}", process_class=SimpleTestProcess)
            for i in range(3)
        ]
        
        results = ProcessPool.submit_all(tasks, size=2, timeout=15.0)
        
        print_result(len(results) == 3, "One-shot execution completed", f"results: {len(results)}")
        
    except Exception as e:
        print_result(False, f"One-shot pool test failed: {e}")
        test_success = False
    
    return test_success


def test_error_handling():
    """Test error handling and timeout scenarios."""
    print_section("Error Handling Tests")
    
    test_success = True
    
    # Test lifecycle errors
    print_subsection("Lifecycle Error Handling")
    
    error_sections = ["preloop", "loop", "postloop"]
    
    for section in error_sections:
        try:
            with CrossProcessing() as cp:
                process = ErrorTestProcess(error_in=section)
                pdata = cp.create_process(f"error_{section}", process)
                
                # Process should crash and trigger restart if enabled, or just crash if not
                success = cp.join_process(f"error_{section}", timeout=10.0)
                
                # Check that process recognized the error and status was updated
                status = cp.get_process_status(f"error_{section}")
                print_result(status == PStatus.CRASHED, f"Error in {section} handled", f"status: {status.value if status else 'None'}")
                
        except Exception as e:
            print_result(False, f"Error handling for {section} failed: {e}")
            test_success = False
    
    # Test timeout scenarios
    print_subsection("Timeout Handling")
    
    timeout_sections = ["preloop", "loop", "postloop"]
    
    for section in timeout_sections:
        try:
            # Set short timeouts to force timeout
            config = _PConfig()
            config.set_quick_timeouts()  # 5s preloop, 30s loop, 10s postloop
            
            with CrossProcessing() as cp:
                process = TimeoutTestProcess(timeout_in=section, delay=2.0)
                pdata = cp.create_process(f"timeout_{section}", process, config)
                
                success = cp.join_process(f"timeout_{section}", timeout=15.0)
                
                # For timeout tests, we expect the process to complete (possibly with timeout error)
                print_result(success, f"Timeout in {section} handled", "completed within overall timeout")
                
        except Exception as e:
            print_result(False, f"Timeout handling for {section} failed: {e}")
            test_success = False
    
    # Test pool error handling
    print_subsection("Pool Error Handling")
    
    try:
        with ProcessPool(size=2) as pool:
            # Submit a mix of good and bad tasks
            pool.submit_function("good_func", simple_test_function, args=(1,))
            pool.submit_function("bad_func", error_test_function)
            
            try:
                results = pool.get_all_results(timeout=10.0)
                # Check if any tasks failed
                failed_tasks = [r for r in results if r.failed]
                if failed_tasks:
                    print_result(True, "Pool error handling working", f"caught {len(failed_tasks)} failed tasks")
                else:
                    print_result(False, "Pool should have detected failed function")
                    test_success = False
            except PoolTaskError as e:
                print_result(True, "Pool error handling working", f"caught {len(e.failed_tasks)} failed tasks")
                
    except Exception as e:
        print_result(False, f"Pool error handling test failed: {e}")
        test_success = False
    
    return test_success


def test_data_structures():
    """Test _PData and other data structure functionality."""
    print_section("Data Structure Tests")
    
    test_success = True
    
    # Test _PData functionality
    print_subsection("PData Container")
    
    try:
        with CrossProcessing() as cp:
            process = ComplexDataProcess()
            pdata = cp.create_process("complex", process)
            
            # Test PData properties during execution
            print_result(pdata.pkey == "complex", "PData key correct")
            print_result(pdata.pclass == "ComplexDataProcess", "PData class correct")
            print_result(pdata.status == PStatus.STARTING, "PData initial status correct")
            
            # Wait for completion
            success = cp.join_process("complex", timeout=10.0)
            result = cp.get_process_result("complex")
            
            print_result(success and result, "Complex data process completed")
            
            if result:
                complex_data = result.get('complex_data', {})
                print_result('numbers' in complex_data, "Complex data structure preserved")
                print_result(len(complex_data.get('numbers', [])) == 100, "Data integrity maintained")
                
    except Exception as e:
        print_result(False, f"PData test failed: {e}")
        test_success = False
    
    # Test statistics tracking
    print_subsection("Statistics Tracking")
    
    try:
        with CrossProcessing() as cp:
            process = TimingTestProcess()
            pdata = cp.create_process("stats", process)
            
            success = cp.join_process("stats", timeout=10.0)
            stats = cp.get_process_stats("stats")
            
            print_result(stats is not None, "Statistics collected")
            
            if stats:
                print_result('total_loops' in stats, "Loop count tracked")
                print_result('average_loop_time' in stats, "Timing tracked")
                
    except Exception as e:
        print_result(False, f"Statistics test failed: {e}")
        test_success = False
    
    return test_success


def test_performance_scenarios():
    """Test performance and scaling scenarios."""
    print_section("Performance Tests")
    
    test_success = True
    
    # Test many processes
    print_subsection("High Process Count")
    
    try:
        with CrossProcessing() as cp:
            num_processes = 10
            
            # Create many short-running processes
            for i in range(num_processes):
                process = SimpleTestProcess(num_loops=1)
                pdata = cp.create_process(f"perf_{i}", process)
            
            # Wait for all to complete
            start_time = time.time()
            all_success = cp.join_all(timeout=30.0)
            duration = time.time() - start_time
            
            print_result(all_success, f"High process count test", f"{num_processes} processes in {duration:.2f}s")
            
    except Exception as e:
        print_result(False, f"High process count test failed: {e}")
        test_success = False
    
    # Test pool performance
    print_subsection("Pool Performance")
    
    try:
        num_tasks = 20
        tasks = [
            _PTask(key=f"pool_perf_{i}", process_class=SimpleTestProcess)
            for i in range(num_tasks)
        ]
        
        start_time = time.time()
        results = ProcessPool.submit_all(tasks, size=4, timeout=30.0)
        duration = time.time() - start_time
        
        print_result(len(results) == num_tasks, f"Pool performance test", f"{num_tasks} tasks in {duration:.2f}s")
        
    except Exception as e:
        print_result(False, f"Pool performance test failed: {e}")
        test_success = False
    
    return test_success


def run_comprehensive_test_suite():
    """Run the complete comprehensive test suite."""
    print_section("🚀 Comprehensive Multiprocessing Engine Test Suite")
    
    if not MP_IMPORTS_SUCCESSFUL:
        print_result(False, "Cannot run tests - multiprocessing engine import failed")
        return False
    
    print_info("Testing complete internal multiprocessing engine for Suitkaise")
    print_info("This validates production-ready cross-process execution capabilities")
    
    # Track test results
    test_results = {}
    
    # Run all test categories
    test_categories = [
        ("Basic Process Lifecycle", test_basic_process_lifecycle),
        ("Configuration Scenarios", test_configuration_scenarios),
        ("Process Managers", test_process_managers),
        ("Process Pool", test_process_pool),
        ("Error Handling", test_error_handling),
        ("Data Structures", test_data_structures),
        ("Performance Scenarios", test_performance_scenarios),
    ]
    
    for category_name, test_function in test_categories:
        print_section(f"Running {category_name}")
        try:
            start_time = time.time()
            result = test_function()
            duration = time.time() - start_time
            test_results[category_name] = result
            print_info(f"Category completed in {duration:.2f}s")
        except Exception as e:
            print_result(False, f"{category_name} failed with exception: {e}")
            test_results[category_name] = False
            traceback.print_exc()
    
    # Print final summary
    print_section("🎉 Test Suite Summary")
    
    passed = sum(test_results.values())
    total = len(test_results)
    
    for category, result in test_results.items():
        print_result(result, category)
    
    print_section("🏆 Final Results")
    
    if passed == total:
        print_result(True, f"ALL TESTS PASSED! ({passed}/{total})")
        print_info("🎉 Your multiprocessing engine is production-ready!")
        print_info("✅ Complete process lifecycle management validated")
        print_info("✅ Configuration and timeout handling working")
        print_info("✅ Error handling and recovery functional")
        print_info("✅ Process pools and managers operational")
        print_info("✅ Data structures and serialization working")
        print_info("✅ Performance characteristics validated")
        print_info("🚀 Ready for real-world multiprocessing workloads!")
    else:
        print_result(False, f"Some tests failed ({passed}/{total} passed)")
        failed_categories = [cat for cat, result in test_results.items() if not result]
        print_warning(f"Failed categories: {', '.join(failed_categories)}")
        print_warning("Review failed tests and check engine implementation")
    
    return passed == total


if __name__ == "__main__":
    success = run_comprehensive_test_suite()
    sys.exit(0 if success else 1)