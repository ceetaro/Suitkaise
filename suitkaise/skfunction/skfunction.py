# add license here

# suitkaise/skfunction/skfunction.py

"""
SKFunction - convenient function creation

- can create and register predefined functions with arguments added
- global registry so that you can access these functions from anywhere in the project
- performance tracking
- metadata
- automatic cross process support
- builder for complex functions with lots of arguments
- custom type, AnyFunction, which is Callable | SKFunction

3 ways to create an SKFunction:
1. Simple: function = SKFunction(func, args, kwargs) # optionally add a name and description
2. Builder: SKFunctionBuilder context manager to create step-by-step # optionally add a name and description
3. Auto convert a callable to SKFunction with no arguments.

SKFunctions can auto register themselves in a global registry under their callable name.

Usage:
```python
# Create function with some preset parameters
processor = SKFunction(
    func=data_pipeline,
    args=(source, target),
    kwargs={"format": "json"}
)

# Add specific parameters by name - no need to know positions!
result = processor.call(additional_args=[
    ("debug", True),      # Could be 5th parameter
    ("timeout", 300),     # Could be 8th parameter
    ("workers", 4)        # Could be 3rd parameter
])

# Preserve complete execution context
xml_processor = SKFunction(
    func=data_processor,
    kwargs={"format": "xml", "debug": True, "timeout": 300},
    name="xml_debug_processor"
)

# Reuse with different data, same configuration
for dataset in datasets:
    result = xml_processor.call(additional_args=[
        ("source", dataset.input),
        ("target", dataset.output)
    ])

with SKFunctionBuilder(autoregister=True) as builder:
    builder.add_callable(complex_ml_pipeline)
    builder.add_argument("model_type", "transformer")
    builder.add_kwargs({
        "epochs": 100, "batch_size": 32, "learning_rate": 0.001
    })
    ml_trainer = builder.build()


    # registration
    # there is only one global registry, so we don't need to get it explicitly
    skfunction.register(skf)  # register the function in the global registry

    # autoregister
    @skfunction.autoregister()

    # convert a callable to SKFunction
    @skfunction.convert_callable()
    or...
    convert_callable(the_callable)

    # easy access
    functionrej = get_function("my_function")  # get the function by name
    result = functionrej.call() or result = functionrej()  # call the function
```
"""
import threading
import inspect
import tracemalloc
import weakref
import time
from typing import Callable, Any, Dict, Optional, List, Tuple, Type, Set, Union
from dataclasses import dataclass, field
from contextlib import contextmanager
from enum import Enum, auto
from collections import defaultdict, deque

from suitkaise.rej.rej import Rej, RejSingleton
from suitkaise.cereal import Cereal
import suitkaise.sktime.sktime as sktime

AnyFunction = Union[Callable, 'SKFunction']

# Exceptions

class SKFunctionError(Exception):
    """Something went wrong with SKFunction."""
    pass

class SKFunctionBuilderError(SKFunctionError):
    """Something went wrong with SKFunctionBuilder."""
    pass

class SKFunctionBuildError(SKFunctionBuilderError):
    """Something went wrong while building the SKFunction."""
    pass

class SKFunctionRegistrationError(SKFunctionError):
    """Something went wrong while registering the SKFunction."""
    pass

class SKFunctionPerformanceError(SKFunctionError):
    """Something went wrong with SKFunction performance tracking."""
    pass

# Performance monitoring/caching

@dataclass
class PerformanceMetrics:
    """Performance tracking for SKFunction operations."""

    # basic metrics
    call_count: int = 0
    total_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0

    # memory usage
    peak_memory_usage: int = 0
    total_memory_allocations: int = 0

    # argument processing
    simple_calls: int = 0 # calls w/o additional arguments
    complex_calls: int = 0 # calls with additional arguments
    named_arg_calls: int = 0 # calls using named parameter insertion
    positional_arg_calls: int = 0 # calls using positional argument insertion

    # error metrics
    error_count: int = 0
    last_error: Optional[str] = None

    #optimization
    cache_hits: int = 0
    cache_misses: int = 0
    optimization_applied: bool = False

    # timing history (last 100 calls)
    execution_times: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_execution_time(self) -> float:
        """Calculate average execution time."""
        return self.total_execution_time / max(1, self.call_count)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.call_count == 0:
            return 100.0
        return ((self.call_count - self.error_count) / self.call_count) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_cache_operations = self.cache_hits + self.cache_misses
        if total_cache_operations == 0:
            return 0.0
        return (self.cache_hits / total_cache_operations) * 100
    
    @property
    def complexity_ratio(self) -> float:
        """Ratio of complex calls to simple calls."""
        if self.simple_calls == 0:
            return float('inf') if self.complex_calls > 0 else 0.0
        return self.complex_calls / self.simple_calls

    def record_execution(self, execution_time: float, had_error: bool = False, 
                        was_simple: bool = True, used_named_args: bool = False,
                        memory_usage: int = 0):
        """Record execution metrics."""
        self.call_count += 1
        self.total_execution_time += execution_time
        self.min_execution_time = min(self.min_execution_time, execution_time)
        self.max_execution_time = max(self.max_execution_time, execution_time)
        
        if memory_usage > 0:
            self.peak_memory_usage = max(self.peak_memory_usage, memory_usage)
            self.total_memory_allocations += 1
        
        if had_error:
            self.error_count += 1
        
        if was_simple:
            self.simple_calls += 1
        else:
            self.complex_calls += 1
            if used_named_args:
                self.named_arg_calls += 1
            else:
                self.positional_arg_calls += 1
        
        # Store execution time in history
        self.execution_times.append({
            'time': execution_time,
            'timestamp': sktime.now(),
            'error': had_error,
            'simple': was_simple,
            'named_args': used_named_args
        })

class PerformanceCache:
    """High-performance caching system for SKFunction operations."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._signature_cache: Dict[int, inspect.Signature] = {}
        self._param_info_cache: Dict[int, Dict[str, Dict[str, Any]]] = {}
        self._argument_merge_cache: Dict[str, Tuple] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def get_signature(self, func: Callable) -> Optional[inspect.Signature]:
        """Get cached function signature."""
        func_id = id(func)
        with self._lock:
            if func_id not in self._signature_cache:
                try:
                    if inspect.isfunction(func) or inspect.ismethod(func):
                        self._signature_cache[func_id] = inspect.signature(func)
                    else:
                        return None
                except (ValueError, TypeError):
                    return None
            return self._signature_cache.get(func_id)
        
    def get_param_info(self, func: Callable) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get cached parameter information."""
        func_id = id(func)
        with self._lock:
            if func_id not in self._param_info_cache:
                signature = self.get_signature(func)
                if signature:
                    param_info = {}
                    for param_name, param in signature.parameters.items():
                        param_info[param_name] = {
                            'kind': param.kind,
                            'default': None if param.default is param.empty else param.default,
                            'annotation': None if param.annotation is param.empty else param.annotation,
                            'has_default': param.default is not param.empty
                        }
                    self._param_info_cache[func_id] = param_info
                else:
                    return None
            return self._param_info_cache.get(func_id)
        
    def cache_argument_merge(self, cache_key: str, result: Tuple):
        """Cache argument merge results."""
        with self._lock:
            if len(self._argument_merge_cache) >= self.max_size:
                # Remove oldest 20% when full, not just 10 items
                items_to_remove = max(10, self.max_size // 5)
                oldest_keys = sorted(self._access_times.items(), key=lambda x: x[1])[:items_to_remove]
                for key, _ in oldest_keys:
                    self._argument_merge_cache.pop(key, None)
                    self._access_times.pop(key, None)
            
            self._argument_merge_cache[cache_key] = result
            self._access_times[cache_key] = sktime.now()
    
    def get_cached_argument_merge(self, cache_key: str) -> Optional[Tuple]:
        """Get cached argument merge result."""
        with self._lock:
            if cache_key in self._argument_merge_cache:
                self._access_times[cache_key] = sktime.now()
                return self._argument_merge_cache[cache_key]
            return None
    
    def clear(self):
        """Clear all caches."""
        with self._lock:
            self._signature_cache.clear()
            self._param_info_cache.clear()
            self._argument_merge_cache.clear()
            self._access_times.clear()

# Global performance cache
_performance_cache = PerformanceCache()

class PerformanceMonitor:
    """System-wide performance monitoring for SKFunction operations."""
    
    def __init__(self, max_functions: int = 1000):
        self._function_metrics: Dict[str, PerformanceMetrics] = {}
        self._max_functions = max_functions
        self._function_access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._system_metrics = PerformanceMetrics()
        
        # Enable memory tracking if available
        self._memory_tracking_enabled = False
        try:
            tracemalloc.start()
            self._memory_tracking_enabled = True
        except RuntimeError:
            # Already started or not available
            self._memory_tracking_enabled = False
    
    def start_call_monitoring(self, function_name: str) -> Dict[str, Any]:
        """Thread-safe call monitoring start."""
        start_time = sktime.now()
        start_memory = None
        
        # Atomic memory check
        if self._memory_tracking_enabled:
            try:
                with self._lock:  # Protect memory tracking
                    if tracemalloc.is_tracing():
                        current, peak = tracemalloc.get_traced_memory()
                        start_memory = current
            except Exception:
                pass  # Memory tracking failure shouldn't break functionality
        
        return {
            'start_time': start_time,
            'function_name': function_name,
            'start_memory': start_memory
        }
    
    def end_call_monitoring(self, context: Dict[str, Any], had_error: bool = False, 
                        was_simple: bool = True, used_named_args: bool = False):
        execution_time = sktime.now() - context['start_time']
        function_name = context['function_name']
        memory_usage = 0
        
        if context['start_memory'] is not None:
            try:
                with self._lock:
                    if tracemalloc.is_tracing():
                        current, peak = tracemalloc.get_traced_memory()
                        memory_usage = current - context['start_memory']
            except Exception:
                pass
        
        with self._lock:
            # Clean up old metrics if we're at capacity
            if len(self._function_metrics) >= self._max_functions:
                self._cleanup_old_metrics()
            
            # Create if not exists
            if function_name not in self._function_metrics:
                self._function_metrics[function_name] = PerformanceMetrics()
            
            # Record function-specific metrics
            self._function_metrics[function_name].record_execution(
                execution_time, had_error, was_simple, used_named_args, memory_usage
            )
            self._function_access_times[function_name] = sktime.now()
            
            # ✅ ADD THIS: Update system-wide metrics
            self._system_metrics.record_execution(
                execution_time, had_error, was_simple, used_named_args, memory_usage
            )

    def _cleanup_old_metrics(self):
        """Remove least recently used function metrics."""
        if not self._function_access_times:
            return
            
        # Find oldest 20% to remove
        items_to_remove = max(1, len(self._function_access_times) // 5)
        oldest_functions = sorted(
            self._function_access_times.items(), 
            key=lambda x: x[1]
        )[:items_to_remove]
        
        for func_name, _ in oldest_functions:
            self._function_metrics.pop(func_name, None)
            self._function_access_times.pop(func_name, None)

    def get_function_metrics(self, function_name: str) -> PerformanceMetrics:
        """Get metrics for a specific function."""
        with self._lock:
            if function_name not in self._function_metrics:
                # Return empty metrics if function hasn't been called yet
                return PerformanceMetrics()
            return self._function_metrics[function_name]
    
    def get_system_metrics(self) -> PerformanceMetrics:
        """Get system-wide metrics."""
        with self._lock:
            return self._system_metrics
        
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        with self._lock:
            # Top performers and bottlenecks
            function_stats = {}
            for name, metrics in self._function_metrics.items():
                function_stats[name] = {
                    'calls': metrics.call_count,
                    'avg_time': metrics.avg_execution_time,
                    'total_time': metrics.total_execution_time,
                    'success_rate': metrics.success_rate,
                    'complexity_ratio': metrics.complexity_ratio
                }
            
            # Sort by total execution time to find bottlenecks
            bottlenecks = sorted(
                function_stats.items(),
                key=lambda x: x[1]['total_time'],
                reverse=True
            )[:5]
            
            # Sort by call count to find most used
            most_used = sorted(
                function_stats.items(),
                key=lambda x: x[1]['calls'],
                reverse=True
            )[:5]
            
            return {
                'system_metrics': {
                    'total_calls': self._system_metrics.call_count,
                    'total_execution_time': self._system_metrics.total_execution_time,
                    'avg_execution_time': self._system_metrics.avg_execution_time,
                    'success_rate': self._system_metrics.success_rate,
                    'cache_hit_rate': _performance_cache._access_times.__len__(),
                    'memory_tracking_enabled': self._memory_tracking_enabled
                },
                'bottlenecks': bottlenecks,
                'most_used_functions': most_used,
                'optimization_opportunities': self._identify_optimization_opportunities()
            }
        
    def _identify_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Identify optimization opportunities."""
        opportunities = []
        
        with self._lock:
            for name, metrics in self._function_metrics.items():
                # High complexity ratio suggests optimization potential
                if metrics.complexity_ratio > 0.5 and metrics.call_count > 3:
                    opportunities.append({
                        'function': name,
                        'type': 'argument_optimization',
                        'reason': f'High complexity ratio: {metrics.complexity_ratio:.2f}',
                        'suggestion': 'Consider pre-computing argument combinations'
                    })
                
                # Low cache hit rate
                if metrics.cache_hit_rate < 80 and metrics.call_count > 5:
                    opportunities.append({
                        'function': name,
                        'type': 'caching_optimization',
                        'reason': f'Low cache hit rate: {metrics.cache_hit_rate:.1f}%',
                        'suggestion': 'Review caching strategy'
                    })
                
                # High error rate
                if metrics.success_rate < 100 and metrics.call_count > 2:
                    opportunities.append({
                        'function': name,
                        'type': 'error_handling',
                        'reason': f'Success rate: {metrics.success_rate:.1f}%',
                        'suggestion': 'Improve error handling and validation'
                    })
        
        return opportunities
    
    def inject_test_metrics(self, function_name: str, **kwargs):
        """Inject test metrics for testing purposes."""
        with self._lock:
            metrics = PerformanceMetrics()
            
            # Set test values
            metrics.call_count = kwargs.get('call_count', 10)
            metrics.simple_calls = kwargs.get('simple_calls', 5)
            metrics.complex_calls = kwargs.get('complex_calls', 15)  # High complexity ratio
            metrics.cache_hits = kwargs.get('cache_hits', 2)
            metrics.cache_misses = kwargs.get('cache_misses', 8)  # Low hit rate
            metrics.error_count = kwargs.get('error_count', 2)  # Some errors
            metrics.total_execution_time = kwargs.get('total_execution_time', 1.0)
            
            self._function_metrics[function_name] = metrics
            self._function_access_times[function_name] = sktime.now()

            
    def debug_function_metrics(self) -> Dict[str, Any]:
        """Debug method to see current metrics for all functions."""
        with self._lock:
            debug_info = {}
            for name, metrics in self._function_metrics.items():
                debug_info[name] = {
                    'call_count': metrics.call_count,
                    'complexity_ratio': metrics.complexity_ratio,
                    'cache_hit_rate': metrics.cache_hit_rate,
                    'success_rate': metrics.success_rate,
                    'simple_calls': metrics.simple_calls,
                    'complex_calls': metrics.complex_calls,
                    'total_execution_time': metrics.total_execution_time,
                    'avg_execution_time': metrics.avg_execution_time,
                }
            return debug_info

# Global performance monitor
_performance_monitor = PerformanceMonitor()
    
# Main SKFunction class

class SKFunction:
    """
    Convenient function creation and registration using a function wrapper.

    - Execute multiple times with the same arguments
    - Pass around your application easily
    - Stored in a global registry for easy access
    - Track performance and metadata
    - Serialize for cross-process use
    
    """

    class Dataset:
        """Data structures related to SKFunction storage and metadata."""

        @dataclass
        class FunctionMetadata:
            """
            Comprehensive metadata for each SKFunction.

            This gives context and tracks performance and usage of the function.
            
            """
            name: str = ""
            description: str = ""
            
            # Function information
            func_name: str = ""
            module_name: str = ""
            module_path: Optional[str] = None
            signature: Optional[str] = None
            return_type: Optional[str] = None

            # Creation context
            created_at: float = field(default_factory=sktime.now)
            created_by_process: str = field(default_factory=lambda: str(__import__('os').getpid()))

            # Serialization info
            is_serializable: bool = False
            serialization_mode: str = 'internal'

            # User metadata
            user_added_metadata: Dict[str, Any] = field(default_factory=dict)
            
            # Performance optimization flags
            optimization_level: str = "standard"  # standard, aggressive, conservative
            cache_enabled: bool = True
            
    def __init__(self,
                 func: Callable,
                 args: Optional[Tuple] = None,
                 kwargs: Optional[Dict[str, Any]] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 autoregister: bool = True,
                 metadata: Optional[Dict[str, Any]] = None,
                 optimization_level: str = "standard"):
        """
        Create a new SKFunction.

        Args:
            func: The callable function to wrap
            args: Positional arguments to preset for the function
            kwargs: Keyword arguments to preset for the function
            name: Optional name for the function
            description: Optional description for the function
            autoregister: Whether to automatically register in global registry
            metadata: Optional user-defined metadata
            optimization_level: Performance optimization level (standard/aggressive/conservative)
        """
        if not callable(func):
            raise SKFunctionError(f"The provided function is not callable. Received: {type(func)}")
        
        self.func = func
        self.args = args if args is not None else ()
        self.kwargs = kwargs if kwargs is not None else {}

        # Create comprehensive metadata
        serialization_mode = metadata.get('serialization_mode', 'internal') if metadata else 'internal'

        self.metadata = self.Dataset.FunctionMetadata(
            name=name or getattr(func, '__name__', 'unknown'),
            description=description or "",
            func_name=getattr(func, '__name__', 'unknown'),
            module_name=getattr(func, '__module__', 'unknown'),
            module_path=self._safe_get_file_path(func),
            signature=self._safe_get_signature(func),
            return_type=self._safe_get_return_type(func),
            is_serializable=self._test_serialization(func, serialization_mode),
            serialization_mode=serialization_mode,
            optimization_level=optimization_level,
            user_added_metadata=metadata.copy() if metadata else {}
        )

        self._lock = threading.RLock()

        # Performance monitoring
        self._performance_metrics = PerformanceMetrics()
        
        # Caching for signature and parameter info
        self._signature_cache = _performance_cache.get_signature(func)
        self._param_info_cache = _performance_cache.get_param_info(func)
        
        # Auto-register if requested
        if autoregister:
            self.autoregister()

    def _safe_get_file_path(self, func: Callable) -> Optional[str]:
        """Safely get function file path."""
        try:
            return inspect.getfile(func) if inspect.isfunction(func) else None
        except (TypeError, OSError):
            return None

    def _safe_get_signature(self, func: Callable) -> Optional[str]:
        """Safely get function signature."""
        try:
            sig = _performance_cache.get_signature(func)
            return str(sig) if sig else None
        except:
            return None

    def _safe_get_return_type(self, func: Callable) -> Optional[str]:
        """Safely get function return type."""
        try:
            sig = _performance_cache.get_signature(func)
            if sig and sig.return_annotation != inspect.Signature.empty:
                return str(sig.return_annotation)
        except:
            pass
        return None

    def _test_serialization(self, func: Callable, mode: str = 'internal') -> bool:
        """Test if function components can be serialized."""
        try:
            cereal = Cereal()
            func_serializable = cereal.serializable(func, mode)
            args_serializable = all(cereal.serializable(arg, mode) for arg in self.args)
            kwargs_serializable = all(cereal.serializable(value, mode) for value in self.kwargs.values())
            
            return func_serializable and args_serializable and kwargs_serializable
        
        except Exception:
            return False

    def call(self,
            additional_args: Optional[List[Tuple[str, Any]]] | Optional[Tuple] = None,
            additional_kwargs: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the function with its preset args and kwargs, plus any additional arguments.
        
        This method allows you to add arguments at specific parameter positions, not just
        append to the end. This is why we use the SKFunctionBuilder approach instead of
        simple tuple concatenation.
        
        Args:
            additional_args: Either:
                - List[Tuple[str, Any]]: Named arguments like [("param_name", value), ("other_param", other_value)]
                This allows you to set specific parameters by name at any position
                - Tuple: Positional arguments to append: (value1, value2, value3)
                
            additional_kwargs: Additional keyword arguments to pass
            
        Returns:
            Any: The result of the function call
            
        Examples:
        ```python
            # No position juggling needed!
            result = processor.call(additional_args=[
                ("debug", True),      # Could be 5th parameter
                ("timeout", 300),     # Could be 8th parameter  
                ("format", "json")    # Could be 3rd parameter
            ])
            
            # Or traditional positional (position matters)
            result = processor.call(additional_args=(val1, val2, val3))
        ```
        """
        # Start performance monitoring
        monitor_context = _performance_monitor.start_call_monitoring(self.metadata.name)
        
        is_simple_call = False
        uses_named_args = False
        try:
            # Determine call complexity for metrics
            is_simple_call = not additional_args and not additional_kwargs
            uses_named_args = (isinstance(additional_args, list) and 
                             len(additional_args) > 0 and 
                             isinstance(additional_args[0], tuple))
            
            if is_simple_call:
                # Fast path - no argument processing needed
                result = self.func(*self.args, **self.kwargs)
                if self.metadata.cache_enabled:
                    _performance_monitor._system_metrics.cache_hits += 1
            else:
                # Optimized path - direct merging without temporary objects
                final_args, final_kwargs = self._merge_arguments_optimized(
                    additional_args, additional_kwargs
                )
                result = self.func(*final_args, **final_kwargs)
            
            # Record successful execution
            _performance_monitor.end_call_monitoring(
                monitor_context, 
                had_error=False, 
                was_simple=is_simple_call,
                used_named_args=uses_named_args
            )
            
            return result
            
        except Exception as e:
            # Record failed execution
            _performance_monitor.end_call_monitoring(
                monitor_context,
                had_error=True,
                was_simple=is_simple_call,
                used_named_args=uses_named_args
            )
            
            raise SKFunctionError(f"Failed to execute function '{self.metadata.name}': {e}") from e
        
    def _merge_arguments_optimized(self, additional_args, additional_kwargs) -> Tuple[Tuple, Dict]:
        """
        Optimized argument merging with caching and direct processing.
        
        This replaces the expensive builder-based approach with direct merging.
        """
        # Create cache key for argument combination
        cache_key = None
        if self.metadata.cache_enabled:
            try:
                cache_key = self._create_cache_key(additional_args, additional_kwargs)
                cached_result = _performance_cache.get_cached_argument_merge(cache_key)
                if cached_result:
                    _performance_monitor._system_metrics.cache_hits += 1
                    return cached_result
                else:
                    _performance_monitor._system_metrics.cache_misses += 1
            except:
                pass  # Caching failed, continue without cache
        
        # Start with preset arguments
        final_args = list(self.args)
        final_kwargs = dict(self.kwargs)
        
        # Process additional arguments
        if additional_args:
            if isinstance(additional_args, list) and additional_args:
                # Named parameter injection - the sophisticated feature!
                self._merge_named_parameters(additional_args, final_args, final_kwargs)
            elif isinstance(additional_args, tuple):
                # Positional parameter injection - traditional approach
                final_args.extend(additional_args)
        
        # Merge additional kwargs
        if additional_kwargs:
            final_kwargs.update(additional_kwargs)
        
        result = (tuple(final_args), final_kwargs)
        
        # Cache the result
        if cache_key and self.metadata.cache_enabled:
            try:
                _performance_cache.cache_argument_merge(cache_key, result)
            except:
                pass  # Caching failed, continue
        
        return result
    
    def _merge_named_parameters(self, named_args: List[Tuple[str, Any]], 
                              final_args: List, final_kwargs: Dict):
        """
        Merge named parameters using sophisticated position-independent logic.
        
        This is the core innovation: add parameters by name without knowing positions!
        """
        # Get parameter information (cached)
        param_info = self._param_info_cache
        if not param_info:
            # Fallback to direct kwargs if no signature info
            for param_name, value in named_args:
                final_kwargs[param_name] = value
            return
        
        # Get parameter names in order
        param_names = list(param_info.keys())
        
        for param_name, value in named_args:
            if param_name not in param_info:
                # Parameter not in signature - check if function accepts **kwargs
                accepts_kwargs = any(
                    info['kind'] == inspect.Parameter.VAR_KEYWORD
                    for info in param_info.values()
                )
                if accepts_kwargs:
                    final_kwargs[param_name] = value
                else:
                    raise SKFunctionError(
                        f"Parameter '{param_name}' not found in function signature "
                        f"and function doesn't accept **kwargs. "
                        f"Available parameters: {list(param_info.keys())}"
                    )
                continue
            
            param_details = param_info[param_name]
            param_kind = param_details['kind']
            
            if param_kind == inspect.Parameter.KEYWORD_ONLY:
                # Must be keyword argument
                final_kwargs[param_name] = value
            elif param_kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, 
                              inspect.Parameter.POSITIONAL_ONLY):
                # Can be positional - determine position and update
                try:
                    position = param_names.index(param_name)
                    
                    # Extend args list if needed
                    while len(final_args) <= position:
                        final_args.append(None)
                    
                    # Set the value at the correct position
                    final_args[position] = value
                except ValueError:
                    # Fallback to kwargs if position can't be determined
                    final_kwargs[param_name] = value
            else:
                # VAR_POSITIONAL or VAR_KEYWORD
                final_kwargs[param_name] = value

    def _create_cache_key(self, additional_args, additional_kwargs) -> str:
        """Create a cache key for argument combinations."""
        try:
            # Create a simple hash-based key
            key_parts = []
            
            if additional_args:
                if isinstance(additional_args, list):
                    # Named args - sort by name for consistent caching
                    sorted_args = sorted(additional_args, key=lambda x: x[0] if isinstance(x, tuple) else str(x))
                    key_parts.append(f"named:{sorted_args}")
                else:
                    key_parts.append(f"pos:{additional_args}")
            
            if additional_kwargs:
                # Sort kwargs for consistent caching
                sorted_kwargs = sorted(additional_kwargs.items())
                key_parts.append(f"kwargs:{sorted_kwargs}")
            
            return "|".join(key_parts)
        except:
            # If cache key creation fails, return a simple fallback
            return f"fallback:{id(additional_args)}:{id(additional_kwargs)}"

    def __call__(self, *args, **kwargs) -> Any:
        """Allow direct calling of the SKFunction instance."""
        return self.call(additional_args=args, additional_kwargs=kwargs)

    
    def __repr__(self) -> str:
        """String representation of SKFunction."""
        func_str = f"{self.metadata.module_name}.{self.metadata.func_name}"
        args_str = ', '.join(repr(arg) for arg in self.args)
        kwargs_str = ', '.join(f"{k}={repr(v)}" for k, v in self.kwargs.items())
        all_args = ', '.join(filter(None, [args_str, kwargs_str]))
        
        metrics = _performance_monitor.get_function_metrics(self.metadata.name)
        
        return (f"SKFunction({func_str}({all_args}), "
                f"calls={metrics.call_count}, "
                f"avg_time={metrics.avg_execution_time:.4f}s)")

    # Properties for easy access to performance metrics
    @property
    def call_count(self) -> int:
        """Number of times this function has been executed."""
        try:
            return _performance_monitor.get_function_metrics(self.metadata.name).call_count
        except KeyError:
            return 0
    
    @property
    def avg_execution_time(self) -> float:
        """Average execution time of this function."""
        try:
            return _performance_monitor.get_function_metrics(self.metadata.name).avg_execution_time
        except KeyError:
            return 0.0

    @property
    def total_execution_time(self) -> float:
        """Total execution time of all calls to this function."""
        try:
            return _performance_monitor.get_function_metrics(self.metadata.name).total_execution_time
        except KeyError:
            return 0.0

    @property
    def success_rate(self) -> float:
        """Success rate percentage of this function."""
        try:
            return _performance_monitor.get_function_metrics(self.metadata.name).success_rate
        except KeyError:
            return 100.0

    @property
    def performance_metrics(self) -> PerformanceMetrics:
        """Get detailed performance metrics for this function."""
        try:
            return _performance_monitor.get_function_metrics(self.metadata.name)
        except KeyError:
            return PerformanceMetrics()

    @property
    def last_called(self) -> Optional[float]:
        """Timestamp of last execution."""
        try:
            history = _performance_monitor.get_function_metrics(self.metadata.name).execution_times
            return history[-1]['timestamp'] if history else None
        except KeyError:
            return None
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive information about this SKFunction."""
        metrics = _performance_monitor.get_function_metrics(self.metadata.name)
        
        return {
            # Basic metadata
            'name': self.metadata.name,
            'description': self.metadata.description,
            'func_name': self.metadata.func_name,
            'module_name': self.metadata.module_name,
            'module_path': self.metadata.module_path,
            'signature': self.metadata.signature,
            'return_type': self.metadata.return_type,
            
            # Function composition
            'args_count': len(self.args),
            'kwargs_count': len(self.kwargs),
            'preset_args': self.args,
            'preset_kwargs': self.kwargs,
            
            # Performance metrics
            'call_count': metrics.call_count,
            'avg_execution_time': metrics.avg_execution_time,
            'total_execution_time': metrics.total_execution_time,
            'min_execution_time': metrics.min_execution_time,
            'max_execution_time': metrics.max_execution_time,
            'success_rate': metrics.success_rate,
            'cache_hit_rate': metrics.cache_hit_rate,
            
            # Advanced metrics
            'simple_calls': metrics.simple_calls,
            'complex_calls': metrics.complex_calls,
            'named_arg_calls': metrics.named_arg_calls,
            'positional_arg_calls': metrics.positional_arg_calls,
            'complexity_ratio': metrics.complexity_ratio,
            
            # System info
            'is_serializable': self.metadata.is_serializable,
            'optimization_level': self.metadata.optimization_level,
            'cache_enabled': self.metadata.cache_enabled,
            'created_at': self.metadata.created_at,
            'created_by_process': self.metadata.created_by_process,
            
            # User metadata
            'user_metadata': self.metadata.user_added_metadata,
        }
    
    def get_performance_analysis(self) -> Dict[str, Any]:
        """Get detailed performance analysis and optimization suggestions."""
        metrics = _performance_monitor.get_function_metrics(self.metadata.name)
        
        analysis = {
            'performance_summary': {
                'total_calls': metrics.call_count,
                'success_rate': f"{metrics.success_rate:.1f}%",
                'avg_execution_time': f"{metrics.avg_execution_time:.4f}s",
                'cache_hit_rate': f"{metrics.cache_hit_rate:.1f}%"
            },
            'call_patterns': {
                'simple_calls': metrics.simple_calls,
                'complex_calls': metrics.complex_calls,
                'named_parameter_usage': f"{metrics.named_arg_calls}/{metrics.complex_calls}" if metrics.complex_calls > 0 else "0/0",
                'complexity_ratio': f"{metrics.complexity_ratio:.2f}"
            },
            'optimization_suggestions': []
        }
        
        # Generate optimization suggestions
        if metrics.complexity_ratio > 3.0:
            analysis['optimization_suggestions'].append(
                "High complexity ratio detected. Consider pre-computing common argument combinations."
            )
        
        if metrics.cache_hit_rate < 30 and metrics.call_count > 10:
            analysis['optimization_suggestions'].append(
                "Low cache hit rate. Consider adjusting caching strategy or argument patterns."
            )
        
        if metrics.success_rate < 95 and metrics.call_count > 5:
            analysis['optimization_suggestions'].append(
                f"Success rate is {metrics.success_rate:.1f}%. Review error handling and input validation."
            )
        
        if metrics.avg_execution_time > 0.1:
            analysis['optimization_suggestions'].append(
                "Relatively slow execution time. Consider profiling the underlying function."
            )
        
        return analysis
    
    def autoregister(self) -> None:
        """Register this SKFunction in the global registry."""
        try:
            skfrej = RejSingleton.get_registry("SKFunctions")
            if skfrej is None:
                raise SKFunctionRegistrationError("Global SKFunctions registry not found.")
            skfrej.register(self.metadata.name, self)
        except Exception as e:
            raise SKFunctionRegistrationError(
                f"Failed to register SKFunction '{self.metadata.name}': {e}"
            ) from e

    def to_dict(self) -> Dict[str, Any]:
        """Convert this SKFunction to a dictionary representation."""
        return self.get_info()
    
class SKFunctionBuilder:
    """
    Builder for more control creating SKFunctions.

    Use the builder when you have a really complex function with many arguments
    and you want to build it step-by-step.
    
    ```python
    with SKFunctionBuilder(autoregister=True) as builder:
        builder.add_callable(do_work)
        builder.add_argument("param_name", value)
        builder.add_argument("another_param", another_value)
        builder.add_kwargs({'key': value})
        skf = builder.build(name="my_function",
                            description="This is my function that does work",
                            metadata={"key": "value"})
    ```
    """

    def __init__(self, autoregister: bool = False, editing_existing: bool = False):
        self.func: Optional[Callable] = None
        self.provided_args: List[Tuple[str, Any]] = []
        self.provided_kwargs: Dict[str, Any] = {}
        self.name: Optional[str] = None
        self.description: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.autoregister: bool = autoregister
        self.editing_existing: bool = editing_existing
        self.optimization_level: str = "standard"

        # Cached function information
        self.signature: Optional[inspect.Signature] = None
        self.param_info: Dict[str, Dict[str, Any]] = {}

        # Build state
        self.built = False
        self.skfunction: Optional[SKFunction] = None

    def __enter__(self):
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager with automatic registration."""
        if exc_type is not None:
            return False  # Don't suppress exceptions
        
        if not self.built:
            raise SKFunctionBuildError("You must call build() before exiting the context manager.")
        
        if self.skfunction is None:
            raise SKFunctionBuildError("Something went wrong while building the SKFunction.")

        # Handle registration
        if self.autoregister:
            try:
                skfrej = RejSingleton.get_registry("SKFunctions")
                if skfrej is None:
                    raise SKFunctionRegistrationError("Global SKFunctions registry not found.")
                
                if not self.editing_existing:
                    skfrej.register(self.skfunction.metadata.name, self.skfunction)
                else:
                    skfrej.update(self.skfunction.metadata.name, self.skfunction)
            except Exception as e:
                print(f"Warning: Failed to register function in context manager: {e}")


    def add_callable(self, func: Callable) -> 'SKFunctionBuilder':
        """Add a callable to build an SKFunction for."""
        if not callable(func):
            raise SKFunctionBuilderError(f"The provided function is not callable. Received: {type(func)}")
        
        if self.func is not None and not self.editing_existing:
            raise SKFunctionBuilderError(
                "A function has already been set. Use editing_existing=True to edit an existing SKFunction."
            )
        
        self.func = func
        
        # Cache signature and parameter info
        self.signature = _performance_cache.get_signature(func)
        self.param_info = _performance_cache.get_param_info(func) or {}
        
        return self
    
    def add_skfunction(self, skfunction: 'SKFunction') -> 'SKFunctionBuilder':
        """Add an existing SKFunction to the builder for editing."""
        if not isinstance(skfunction, SKFunction):
            raise SKFunctionBuilderError(f"Expected SKFunction instance, got {type(skfunction)}")
        
        # Copy function and cache info
        self.add_callable(skfunction.func)
        
        # Copy existing arguments
        if skfunction.args:
            for i, arg_value in enumerate(skfunction.args):
                if self.signature and i < len(list(self.signature.parameters.keys())):
                    param_name = list(self.signature.parameters.keys())[i]
                    self.provided_args.append((param_name, arg_value))
                else:
                    self.provided_args.append((f"arg_{i}", arg_value))
        
        # Copy existing kwargs
        if skfunction.kwargs:
            self.provided_kwargs.update(skfunction.kwargs)
        
        # Copy metadata
        self.name = skfunction.metadata.name
        self.description = skfunction.metadata.description
        self.metadata.update(skfunction.metadata.user_added_metadata)
        self.optimization_level = skfunction.metadata.optimization_level
        
        return self


    def add_argument(self, param_name: str, value: Any, override_existing: bool = False) -> 'SKFunctionBuilder':
        """Add an argument by parameter name with validation."""
        if self.func is None:
            raise SKFunctionBuilderError("No valid callable function has been set. Use add_callable() first.")
        
        # Check for existing parameter
        existing_index = next(
            (i for i, item in enumerate(self.provided_args) 
             if isinstance(item, tuple) and item[0] == param_name), 
            None
        )
        existing_in_kwargs = param_name in self.provided_kwargs
        
        if (existing_index is not None or existing_in_kwargs) and not override_existing:
            return self  # Skip without warning for performance
        
        # Remove existing if overriding
        if override_existing:
            if existing_index is not None:
                self.provided_args.pop(existing_index)
            if existing_in_kwargs:
                del self.provided_kwargs[param_name]
        
        # Validate and add parameter
        if self.param_info and param_name not in self.param_info:
            # Check if function accepts **kwargs
            accepts_kwargs = any(
                info['kind'] == inspect.Parameter.VAR_KEYWORD
                for info in self.param_info.values()
            )
            if not accepts_kwargs:
                raise SKFunctionBuildError(
                    f"Parameter '{param_name}' not found in function signature "
                    f"and function doesn't accept **kwargs. "
                    f"Available parameters: {list(self.param_info.keys())}"
                )
            self.provided_kwargs[param_name] = value
            return self
        
        # Determine parameter placement
        if self.param_info and param_name in self.param_info:
            param_info = self.param_info[param_name]
            param_kind = param_info['kind']
            
            if param_kind == inspect.Parameter.KEYWORD_ONLY:
                self.provided_kwargs[param_name] = value
            elif param_kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, 
                              inspect.Parameter.POSITIONAL_ONLY):
                # Add as positional argument
                positional_params = [
                    name for name, info in self.param_info.items()
                    if info['kind'] in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                      inspect.Parameter.POSITIONAL_ONLY)
                ]
                
                if param_name in positional_params:
                    position = positional_params.index(param_name)
                    while len(self.provided_args) <= position:
                        self.provided_args.append(None)
                    self.provided_args[position] = (param_name, value)
            else:
                self.provided_kwargs[param_name] = value
        else:
            self.provided_kwargs[param_name] = value
        
        return self
    

    def add_kwargs(self, kwargs: Dict[str, Any]) -> 'SKFunctionBuilder':
        """Add multiple keyword arguments."""
        for param_name, value in kwargs.items():
            self.add_argument(param_name, value)
        return self
    
    def set_name(self, name: str) -> 'SKFunctionBuilder':
        """Set the name for the SKFunction being built."""
        self.name = name
        return self
    
    def set_description(self, description: str) -> 'SKFunctionBuilder':
        """Set the description for the SKFunction being built."""
        self.description = description
        return self
    
    def set_optimization_level(self, level: str) -> 'SKFunctionBuilder':
        """Set the optimization level (standard/aggressive/conservative)."""
        if level not in ["standard", "aggressive", "conservative"]:
            raise SKFunctionBuilderError(f"Invalid optimization level: {level}")
        self.optimization_level = level
        return self
    
    def add_metadata(self, metadata: Dict[str, Any], override_existing: bool = False) -> 'SKFunctionBuilder':
        """Add user metadata to the SKFunction being built."""
        if override_existing:
            self.metadata.update(metadata)
        else:
            for key, value in metadata.items():
                if key not in self.metadata:
                    self.metadata[key] = value
        return self

    def validate(self) -> bool:
        """Validate that the builder has enough information to create an SKFunction."""
        if self.func is None:
            return False
        
        if not self.param_info:
            return True  # Can't validate without signature
        
        # Build argument mapping for validation
        final_args_mapping = {}
        param_names = list(self.param_info.keys())
        
        for i, item in enumerate(self.provided_args):
            if item is not None and isinstance(item, tuple) and len(item) == 2:
                param_name, param_value = item
                final_args_mapping[param_name] = param_value
            elif item is not None and i < len(param_names):
                final_args_mapping[param_names[i]] = item
        
        final_args_mapping.update(self.provided_kwargs)
        
        # Check required parameters
        required_params = [
            name for name, info in self.param_info.items()
            if not info['has_default'] and info['kind'] != inspect.Parameter.VAR_KEYWORD
        ]
        
        missing_required = [param for param in required_params if param not in final_args_mapping]
        
        if missing_required:
            raise SKFunctionBuildError(f"Missing required parameters: {', '.join(missing_required)}")
        
        return True
          

    def build(self) -> SKFunction:
        """Build the optimized SKFunction."""
        if not self.validate():
            raise SKFunctionBuildError("Builder validation failed")
        
        # Extract final arguments
        final_args = []
        for item in self.provided_args:
            if item is not None:
                if isinstance(item, tuple) and len(item) == 2:
                    final_args.append(item[1])
                else:
                    final_args.append(item)
        
        # Create the SKFunction with optimization level
        sk_func = SKFunction(
            func=self.func,
            args=tuple(final_args),
            kwargs=self.provided_kwargs,
            name=self.name,
            description=self.description,
            autoregister=False,  # Handle registration in __exit__
            metadata=self.metadata,
            optimization_level=self.optimization_level
        )
        
        self.built = True
        self.skfunction = sk_func
        return sk_func

# =============================================================================
# MODULE-LEVEL UTILITY FUNCTIONS
# =============================================================================

def edit_skfunction(skfunction: 'SKFunction',
                    additional_args: Optional[Tuple] = None,
                    additional_kwargs: Optional[Dict[str, Any]] = None,
                    new_name: Optional[str] = None,
                    new_description: Optional[str] = None,
                    new_metadata: Optional[Dict[str, Any]] = None) -> 'SKFunction':
    """
    Edit an existing SKFunction by creating an optimized modified copy.
    
    Creates a new SKFunction based on the existing one with modifications.
    The new function can optionally replace the old one in the registry.
    """
    if not isinstance(skfunction, SKFunction):
        raise SKFunctionError("The provided object is not an SKFunction instance.")
    
    # Check if function is registered
    skfrej = RejSingleton.get_registry("SKFunctions")
    was_registered = skfunction.metadata.name in skfrej if skfrej else False
    
    with SKFunctionBuilder(autoregister=was_registered, editing_existing=True) as builder:
        builder.add_skfunction(skfunction)
        
        if additional_args:
            for i, arg_value in enumerate(additional_args):
                builder.add_argument(f"additional_arg_{i}", arg_value)
        
        if additional_kwargs:
            builder.add_kwargs(additional_kwargs)
        
        if new_name:
            builder.set_name(new_name)
        if new_description:
            builder.set_description(new_description)
        if new_metadata:
            builder.add_metadata(new_metadata, override_existing=True)
        
        modified_func = builder.build()
    
    return modified_func

def get_function(name: str) -> Optional['SKFunction']:
    """Get a registered SKFunction by name from the global registry."""
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")
        return skfrej.get(name)
    except Exception:
        return None

def list_functions() -> List[str]:
    """Get a list of all registered function names."""
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")
        return skfrej.list_keys()
    except Exception:
        return []

def remove_function(name: str) -> bool:
    """Remove a function from the global registry."""
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")
        return skfrej.remove(name)
    except Exception:
        return False


def convert_callable(func: Callable, 
                    name: Optional[str] = None,
                    description: Optional[str] = None,
                    autoregister: bool = True) -> 'SKFunction':
    """Convert a regular callable to an optimized SKFunction."""
    return SKFunction(
        func=func,
        name=name or getattr(func, '__name__', 'unknown'),
        description=description or "",
        autoregister=autoregister
    )

def autoregister(name: Optional[str] = None, description: Optional[str] = None):
    """Decorator to automatically convert a function to SKFunction and register it."""
    def decorator(func):
        sk_func = convert_callable(
            func, 
            name=name or func.__name__,
            description=description,
            autoregister=True
        )
        return sk_func
    return decorator

def can_register_function(func: Callable) -> bool:
    """Check if a function can be registered in the cross-process registry."""
    try:
        cereal = Cereal()
        return cereal.serializable(func, mode='internal')
    except:
        return False

def get_performance_report() -> Dict[str, Any]:
    """Get comprehensive performance report for all SKFunctions."""
    return _performance_monitor.get_performance_report()

def get_system_performance_metrics() -> PerformanceMetrics:
    """Get system-wide performance metrics."""
    return _performance_monitor.get_system_metrics()

def clear_performance_cache():
    """Clear the global performance cache."""
    _performance_cache.clear()

def reset_performance_monitor():
    """Reset the performance monitor to a clean state."""
    _performance_monitor._function_metrics.clear()
    _performance_monitor._system_metrics = PerformanceMetrics()

def enable_memory_tracking():
    """Enable memory tracking for performance monitoring."""
    try:
        import tracemalloc
        tracemalloc.start()
        _performance_monitor._memory_tracking_enabled = True
        return True
    except Exception:
        return False
    
def get_optimization_suggestions() -> List[Dict[str, Any]]:
    """Get optimization suggestions for all registered functions."""
    report = get_performance_report()
    return report.get('optimization_opportunities', [])

def benchmark_function(func: SKFunction, iterations: int = 100) -> Dict[str, Any]:
    """Benchmark a specific SKFunction."""
    import statistics
    
    execution_times = []
    errors = 0
    
    for _ in range(iterations):
        try:
            start_time = time.perf_counter()
            func.call()
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)
        except Exception:
            errors += 1
    
    if not execution_times:
        return {"error": "All benchmark iterations failed"}
    
    return {
        "iterations": iterations,
        "successful_runs": len(execution_times),
        "error_count": errors,
        "min_time": min(execution_times),
        "max_time": max(execution_times),
        "mean_time": statistics.mean(execution_times),
        "median_time": statistics.median(execution_times),
        "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
        "success_rate": (len(execution_times) / iterations) * 100
    }

def create(func, *args, name: str = None, description: str = None, 
                   autoregister: bool = True, **kwargs) -> SKFunction:
    """Convenience function to create an SKFunction with preset arguments."""
    return SKFunction(
        func=func,
        args=args,
        kwargs=kwargs,
        name=name,
        description=description,
        autoregister=autoregister
    )

def register(func, name: str = None, description: str = None) -> SKFunction:
    """Register a function in the global registry."""
    if isinstance(func, SKFunction):
        if name:
            func.metadata.name = name
        if description:
            func.metadata.description = description
        func.autoregister()
        return func
    else:
        return SKFunction(
            func=func,
            name=name or getattr(func, '__name__', 'unknown'),
            description=description or "",
            autoregister=True
        )
    
def clear_registry() -> int:
    """Clear all functions from the global registry."""
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")
        return skfrej.clear()
    except Exception:
        return 0

def registry_info() -> dict:
    """Get information about the global function registry."""
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")
        return skfrej.get_info()
    except Exception:
        return {
            'total_items': 0,
            'keys': [],
            'error': 'Registry not accessible'
        }