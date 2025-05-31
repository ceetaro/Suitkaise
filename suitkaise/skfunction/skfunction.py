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
    # simple creation
    skf = SKFunction(
        do_work,
        args=(1, 2),
        kwargs={"name": value},
        name="my_function",
        description="This is my function that does work")
    
    # call the function
    skf.call() or skf()  # both work

    # builder creation
    with SKFunctionBuilder(autoregister=True) as builder:
        builder.add_callable(do_work) or builder.add_skfunction(an_existing_skfunction)
        builder.add_argument("param_name", value)
        builder.add_kwargs({'key': value})
        # can do:
        builder.add_metadata({"key": "value"})
        builder.add_name("my_function")
        builder.add_description("This is my function that does work")

        # can also add name, description, metadata directly when building
        skf = builder.build(name="my_function",
                            description="This is my function that does work",
                            metadata={"key": "value"})
        # or just...
        skf = builder.build()

        **on exit, if autoregister is True, the function will be registered if it hasn't been already.**

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
from typing import Callable, Any, Dict, Optional, List, Tuple, Type, Set, Union
from dataclasses import dataclass, field
from contextlib import contextmanager
from enum import Enum, auto

from suitkaise.rej.rej import Rej, RejSingleton
from suitkaise.cereal import Cereal
import suitkaise.sktime.sktime as sktime

AnyFunction = Union[Callable, 'SKFunction']

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

# =============================================================================
# MODULE-LEVEL TEST FUNCTIONS (so they can be serialized)
# =============================================================================

def simple_add(a: int, b: int) -> int:
    """Simple addition function for testing."""
    return a + b

def complex_function(a: int, b: str, c: float = 3.14, d: str = "default", 
                   *, keyword_only: bool = False, **extra) -> dict:
    """Complex function with various parameter types."""
    return {
        'a': a, 'b': b, 'c': c, 'd': d, 
        'keyword_only': keyword_only, 'extra': extra
    }

def simple_multiply(x: int, y: int) -> int:
    """Simple multiplication for testing."""
    return x * y

class TestClass:
    """Test class with methods."""
    def __init__(self, value: int):
        self.value = value
    
    def add_to_value(self, amount: int) -> int:
        return self.value + amount

def function_with_required_params(a: int, b: str, c: float):
    """Function with required parameters for testing validation."""
    return f"{a}-{b}-{c}"

def test_function(x: int, y: int) -> int:
    """Test function for convert_callable testing."""
    return x * y + 1

def error_function():
    """Function that raises an error for testing."""
    raise ValueError("Test error")

# =============================================================================
# MAIN SKFUNCTION CLASS
# =============================================================================

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
            
            func_name: str = ""
            module_name: str = ""
            module_path: Optional[str] = None

            # type info
            signature: Optional[str] = None
            return_type: Optional[str] = None

            # creation context
            created_at: float = field(default_factory=sktime.now)
            created_by_process: str = field(default_factory=lambda: str(__import__('os').getpid()))

            # execution tracking
            call_count: int = 0
            last_called: Optional[float] = None
            last_execution_time: float = 0.0
            total_execution_time: float = 0.0

            # serialization info
            is_serializable: bool = False
            serialization_mode: str = 'internal'

            # user added data
            user_added_metadata: Dict[str, Any] = field(default_factory=dict)

            def record_execution(self, execution_time: float, error: bool = False):
                """
                Record the execution time of the function call.

                Args:
                    execution_time (float): Time taken to execute the function.
                """
                self.call_count += 1
                self.last_called = sktime.now()
                self.last_execution_time = execution_time
                self.total_execution_time += execution_time
                self.error_occurred = error

            @property
            def avg_execution_time(self) -> float:
                """
                Calculate the average execution time.

                Returns:
                    float: Average execution time per call.
                """
                if self.call_count == 0:
                    return 0.0
                return self.total_execution_time / self.call_count
            
            @property
            def average_execution_time(self) -> float:
                """Alias for avg_execution_time."""
                return self.avg_execution_time
            
    def __init__(self,
                 func: Callable,
                 args: Optional[Tuple] = None,
                 kwargs: Optional[Dict[str, Any]] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 autoregister: bool = True,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Create a new SKFunction.

        Args:
            func: the callable function to wrap.
            args: positional arguments to preset for the function.
            kwargs: keyword arguments to preset for the function.
            name: optional name for the function.
            description: optional description for the function.
            autoregister: whether to automatically register this function in the default global registry.
            metadata: optional user-defined metadata to attach to the function.

        """
        if not callable(func):
            raise SKFunctionError(f"The provided function is not callable. Received: {type(func)}")
        
        self.func = func
        self.args = args if args is not None else ()
        self.kwargs = kwargs if kwargs is not None else {}

        # create metadata
        serialization_mode = metadata.get('serialization_mode', 'internal') if metadata else 'internal'

        self.metadata = self.Dataset.FunctionMetadata(
            name=name or func.__name__,
            description=description or "",
            func_name=func.__name__,
            module_name=func.__module__,
            module_path=inspect.getfile(func) if inspect.isfunction(func) else None,
            signature=str(inspect.signature(func)) if inspect.isfunction(func) else None,
            return_type=str(inspect.signature(func).return_annotation) if inspect.isfunction(func) else None,
            is_serializable=Cereal().serializable(func, mode=serialization_mode),
            serialization_mode=serialization_mode,
        )

        self._lock = threading.RLock()

        # test serialization
        self._test_serialization(mode=serialization_mode)

        # autoregister if requested
        if autoregister:
            self.autoregister()

    def _test_serialization(self, mode: str = 'internal'):
        """Test if this function can be serialized using SKPickle."""
        try:
            cereal = Cereal()
            func_serializable = cereal.serializable(self.func, mode)
            args_serializable = all(cereal.serializable(arg, mode) for arg in self.args)
            kwargs_serializable = all(cereal.serializable(value, mode) for value in self.kwargs.values())

            # all components must be serializable
            self.metadata.is_serializable = func_serializable and args_serializable and kwargs_serializable

        except Exception as e:
            self.metadata.is_serializable = False

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
            
        Example:
            # Original function: def process(a, b, c, d, e, f, g)
            # SKFunction created with: args=(1, 2, 3)  # Sets a=1, b=2, c=3
            # Now add values at specific positions:
            result = skf.call(additional_args=[("e", 5), ("g", 7)])  # Sets e=5, g=7
            
        Raises:
            SKFunctionError: If the function execution fails
        """
        stopwatch = sktime.Stopwatch()
        stopwatch.start()
        
        try:
            # If no additional arguments, call the function directly with preset args/kwargs
            if not additional_args and not additional_kwargs:
                result = self.func(*self.args, **self.kwargs)
            else:
                # Use builder to intelligently merge arguments
                with SKFunctionBuilder(autoregister=False) as builder:
                    builder.add_skfunction(self)
                    
                    if additional_args:
                        if isinstance(additional_args, list):
                            # Named arguments: [("param_name", value), ...]
                            for arg_name, arg_value in additional_args:
                                builder.add_argument(arg_name, arg_value, override_existing=True)
                        elif isinstance(additional_args, tuple):
                            # Positional arguments: (value1, value2, ...)
                            builder.add_args_from_tuple(additional_args)
                    
                    if additional_kwargs:
                        builder.add_kwargs(additional_kwargs)
                    
                    # Build the temporary function and call it directly
                    temp_skfunction = builder.build()
                    # Call the underlying function directly, NOT the call() method (avoids recursion)
                    result = temp_skfunction.func(*temp_skfunction.args, **temp_skfunction.kwargs)
            
            # Record successful execution
            execution_time = stopwatch.stop()
            with self._lock:
                self.metadata.record_execution(execution_time, error=False)
            
            return result
            
        except Exception as e:
            # Record failed execution
            execution_time = stopwatch.stop()
            with self._lock:
                self.metadata.record_execution(execution_time, error=True)
            
            raise SKFunctionError(f"Failed to execute function '{self.metadata.name}': {e}") from e  

    def __call__(self, *args, **kwargs) -> Any:
        """
        Allow direct calling of the SKFunction instance.
        
        """
        return self.call(additional_args=args, additional_kwargs=kwargs)
    
    def __repr__(self) -> str:
        """String representation of SKFunction."""
        func_str = f"{self.metadata.module_name}.{self.metadata.func_name}"
        args_str = ', '.join(repr(arg) for arg in self.args)
        kwargs_str = ', '.join(f"{k}={repr(v)}" for k, v in self.kwargs.items())
        all_args = ', '.join(filter(None, [args_str, kwargs_str]))
        
        return f"SKFunction({func_str}({all_args}), calls={self.metadata.call_count})"

    # Properties for easy access to common metadata
    @property
    def call_count(self) -> int:
        """Number of times this function has been executed."""
        return self.metadata.call_count
    
    @property
    def last_called(self) -> Optional[float]:
        """Timestamp of last execution."""
        return self.metadata.last_called
    
    @property
    def avg_execution_time(self) -> float:
        """Average execution time of this function."""
        return self.metadata.avg_execution_time
    
    @property
    def average_execution_time(self) -> float:
        """Alias for avg_execution_time."""
        return self.metadata.avg_execution_time
    
    @property
    def total_execution_time(self) -> float:
        """Total execution time of all calls to this function."""
        return self.metadata.total_execution_time
    
    @property
    def is_serializable(self) -> bool:
        """Whether this SKFunction can be serialized for cross-process use."""
        return self.metadata.is_serializable
    
    def get_info(self) -> Dict[str, Any]:
        """Get info about this SKFunction."""
        user_metadata = {}
        if Cereal().serializable(self.metadata.user_added_metadata):
            user_metadata = self.metadata.user_added_metadata
        else:
            for key, value in self.metadata.user_added_metadata.items():
                if not Cereal().serializable(value):
                    user_metadata[key] = str(value)
        return {
            'name': self.metadata.name,
            'description': self.metadata.description,
            'user_added_metadata': user_metadata,
            'func_name': self.metadata.func_name,
            'module_name': self.metadata.module_name,
            'module_path': self.metadata.module_path,
            'signature': self.metadata.signature,
            'return_type': self.metadata.return_type,
            'args_count': len(self.args),
            'kwargs_count': len(self.kwargs),
            'call_count': self.metadata.call_count,
            'last_called': self.metadata.last_called,
            'average_execution_time': self.metadata.average_execution_time,
            'total_execution_time': self.metadata.total_execution_time,
            'is_serializable': self.metadata.is_serializable,
            'created_at': self.metadata.created_at,
            'created_by_process': self.metadata.created_by_process,
            'description': self.metadata.description,
        }
    
    def autoregister(self) -> None:
        """
        Auto register this SKFunction in the global registry.

        All SKFunctions are automatically registered in a global registry
        "SKFunctions" for easy access by name.

        Raises:
            SKFunctionRegistrationError: if registration fails.
        
        """
        try:
            skfrej = RejSingleton.get_registry("SKFunctions")  # Keep serialization checking enabled
            if skfrej is None:
                raise SKFunctionRegistrationError("Global SKFunctions registry not found.")
            skfrej.register(self.metadata.name, self)

        except Exception as e:
            raise SKFunctionRegistrationError(f"Failed to register SKFunction '{self.metadata.name}': {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this SKFunction to a dictionary representation.

        Returns:
            Dict[str, Any]: Dictionary containing all relevant metadata and info.
        
        """
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

    def __init__(self,
                 autoregister: bool = False,
                 editing_existing: bool = False):
        self.func: Optional[Callable] = None # if an SKFunction is added, this will be the callable
        self.provided_args: List[Tuple[str, Any]] = []  # positional arguments
        self.provided_kwargs: Dict[str, Any] = {}  # keyword arguments
        self.name: Optional[str] = None  # name of the SKFunction
        self.description: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.autoregister: bool = autoregister  # whether to automatically register the SKFunction in the global registry
        self.editing_existing: bool = editing_existing  # whether we are editing an existing SKFunction

        self.signature: Optional[inspect.Signature] = None  # function signature if available
        self.param_info: Dict[str, Dict[str, Any]] = {}  # parameter info for each argument

        self.built = False  # whether the SKFunction has been built yet
        self.skfunction: Optional[SKFunction] = None  # the resulting SKFunction after build

    def __enter__(self):
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        # If an exception occurred during the with block, don't require build()
        if exc_type is not None:
            return False  # Don't suppress the exception
        
        if not self.built:
            raise SKFunctionBuildError("You must call build() before exiting the context manager.")
        
        # Only register if build() was successful and no exceptions occurred
        if self.skfunction is None:
            raise SKFunctionBuildError("Something went wrong while building the SKFunction.")

        # Only try to register if no exceptions occurred
        try:
            skfrej = RejSingleton.get_registry("SKFunctions")  # Keep serialization checking enabled
            if skfrej is None:
                raise SKFunctionRegistrationError("Global SKFunctions registry not found.")
            
            if self.autoregister and not self.editing_existing:
                # register the function in the global registry
                skfrej.register(self.skfunction.metadata.name, self.skfunction)

            elif self.autoregister and self.editing_existing:
                # re-register the existing SKFunction
                skfrej.update(self.skfunction.metadata.name, self.skfunction)
        except Exception as e:
            print(f"Warning: Failed to register function in context manager: {e}")

    def add_callable(self, func: Callable) -> 'SKFunctionBuilder':
        """
        Add a callable to build an SKFunction for.

        Args:
            func: the callable function to wrap.

        """
        if not callable(func):
            raise SKFunctionBuilderError(f"The provided function is not callable. Received: {type(func)}")
        
        if self.func is not None and not self.editing_existing:
            raise SKFunctionBuilderError(
                "A function has already been set. " \
                "Use editing_existing=True to edit an existing SKFunction.")
        
        self.func = func
        try:
            self.signature = inspect.signature(func) if inspect.isfunction(func) else None

            # store parameter info
            if self.signature:
                for param_name, param in self.signature.parameters.items():
                    self.param_info[param_name] = {
                        'kind': param.kind,
                        'default': None if param.default is param.empty else param.default,
                        'annotation': None if param.annotation is param.empty else param.annotation,
                        'has_default': param.default is not param.empty
                    }
            
            print(f"Added function {getattr(func, '__name__', str(func))} with signature {self.signature}")
            
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not inspect function signature: {e}")
        
        return self
    
    def add_skfunction(self, skfunction: 'SKFunction') -> 'SKFunctionBuilder':
        """
        Add an existing SKFunction to the builder.

        This copies all properties from the SKFunction to the builder,
        allowing you to edit it like you would creating a new SKFunction.

        Args:
            skfunction: the SKFunction to add.

        """
        if not isinstance(skfunction, SKFunction):
            raise SKFunctionBuilderError(
                f"Expected SKFunction instance, got {type(skfunction)}")
        
        # Copy the callable function
        self.add_callable(skfunction.func)
        
        # Copy existing arguments (convert back to list of tuples for builder)
        if skfunction.args:
            for i, arg_value in enumerate(skfunction.args):
                # Try to match positional args to parameter names
                if self.signature and i < len(list(self.signature.parameters.keys())):
                    param_name = list(self.signature.parameters.keys())[i]
                    self.provided_args.append((param_name, arg_value))
                else:
                    # If we can't match to param name, add as positional
                    self.provided_args.append((f"arg_{i}", arg_value))
        
        # Copy existing keyword arguments
        if skfunction.kwargs:
            self.provided_kwargs.update(skfunction.kwargs)
        
        # Copy metadata
        self.name = skfunction.metadata.name
        self.description = skfunction.metadata.description
        self.metadata.update(skfunction.metadata.user_added_metadata)
        
        print(f"Added SKFunction '{skfunction.metadata.name}' to builder")
        return self

    def edit_skfunction(self, skfunction: 'SKFunction') -> 'SKFunctionBuilder':
        """
        Edit an existing SKFunction by adding its properties to the builder.
        Sets editing_existing to True, and might update autoregister.

        Args:
            skfunction: the SKFunction to edit.

        Returns:
            SKFunctionBuilder: self for method chaining.
        
        """
        self.editing_existing = True
        skfrej = RejSingleton.get_registry("SKFunctions")
        if skfrej is None:
            raise SKFunctionBuilderError("Global SKFunctions registry not found.")
        if self.autoregister is False and skfunction.metadata.name in skfrej:
            print(f"The SKFunction '{skfunction.metadata.name}' is already registered. "
                  f"Setting autoregister to True to update it.")
            self.autoregister = True
        
        return self.add_skfunction(skfunction)

    def add_argument(self,
                    param_name: str,
                    value: Any,
                    override_existing: bool = False) -> 'SKFunctionBuilder':
        """
        Add an argument by parameter name.

        Args:
            param_name: name of the parameter to add.
            value: value to set for this parameter.
            override_existing: whether to override an existing parameter with the same name.
        
        """
        if self.func is None or not callable(self.func):
            raise SKFunctionBuilderError("No valid callable function has been set. Use add_callable() first.")
        
        # Check if we already have this parameter set (handle None values properly)
        existing_param_index = None
        for i, item in enumerate(self.provided_args):
            if item is not None and isinstance(item, tuple) and len(item) == 2:
                existing_name, existing_value = item
                if existing_name == param_name:
                    existing_param_index = i
                    break
        
        existing_in_kwargs = param_name in self.provided_kwargs
        
        if (existing_param_index is not None or existing_in_kwargs) and not override_existing:
            print(f"Parameter '{param_name}' already provided. Use override_existing=True to override.")
            return self
        
        # Remove existing if overriding
        if override_existing:
            if existing_param_index is not None:
                self.provided_args.pop(existing_param_index)
            if existing_in_kwargs:
                del self.provided_kwargs[param_name]
        
        # Check if parameter exists in function signature
        if self.signature and param_name not in self.param_info:
            # Check if function accepts **kwargs
            accepts_kwargs = any(
                info['kind'] == inspect.Parameter.VAR_KEYWORD
                for info in self.param_info.values()
            )
            if not accepts_kwargs:
                raise SKFunctionBuildError(
                    f"Parameter '{param_name}' not found in function signature "
                    f"and function doesn't accept **kwargs"
                )
            # Add to kwargs if function accepts **kwargs
            self.provided_kwargs[param_name] = value
            print(f"Added '{param_name}' to kwargs: {value}")
            return self
        
        # Validate type if annotation exists
        if self.signature and param_name in self.param_info:
            param_info = self.param_info[param_name]
            annotation = param_info['annotation']
            if annotation is not None and value is not None:
                # Basic type checking (could be enhanced)
                if hasattr(annotation, '__origin__'):
                    # Handle generic types like List[str], Dict[str, int], etc.
                    pass  # Skip complex type checking for now
                elif not isinstance(value, annotation):
                    print(f"Warning: Parameter '{param_name}' expects {annotation}, got {type(value)}")
        
        # Determine if this should be positional or keyword
        if self.signature and param_name in self.param_info:
            param_info = self.param_info[param_name]
            param_kind = param_info['kind']
            
            if param_kind == inspect.Parameter.KEYWORD_ONLY:
                # Must be keyword argument
                self.provided_kwargs[param_name] = value
                print(f"Added keyword-only argument '{param_name}': {value}")
            elif param_kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, 
                            inspect.Parameter.POSITIONAL_ONLY):
                # Add as positional argument in correct position
                positional_params = [
                    name for name, info in self.param_info.items()
                    if info['kind'] in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                    inspect.Parameter.POSITIONAL_ONLY)
                ]
                
                if param_name in positional_params:
                    position = positional_params.index(param_name)
                    
                    # Extend args list if needed
                    while len(self.provided_args) <= position:
                        self.provided_args.append(None)
                    
                    self.provided_args[position] = (param_name, value)
                    print(f"Added positional argument '{param_name}' at position {position}: {value}")
            else:
                # VAR_POSITIONAL or VAR_KEYWORD
                self.provided_kwargs[param_name] = value
                print(f"Added variable argument '{param_name}': {value}")
        else:
            # No signature info, add as keyword argument
            self.provided_kwargs[param_name] = value
            print(f"Added argument '{param_name}': {value}")
        
        return self

    def add_kwargs(self, kwargs: Dict[str, Any]) -> 'SKFunctionBuilder':
        """
        Add multiple keyword arguments.
        
        Args:
            kwargs: Dictionary of keyword arguments
            
        Returns:
            self for method chaining
        """
        for param_name, value in kwargs.items():
            self.add_argument(param_name, value)
        return self
    
    def set_name(self, name: str) -> 'SKFunctionBuilder':
        """
        Set the name for the SKFunction being built.
        
        Args:
            name: Human-readable name for the function
            
        Returns:
            SKFunctionBuilder: self for method chaining
        """
        self.name = name
        return self
    
    def set_description(self, description: str) -> 'SKFunctionBuilder':
        """
        Set the description for the SKFunction being built.
        
        Args:
            description: Description of what this function does
            
        Returns:
            SKFunctionBuilder: self for method chaining
        """
        self.description = description
        return self
    
    def add_metadata(self, 
                    metadata: Dict[str, Any], 
                    override_existing: bool = False) -> 'SKFunctionBuilder':
        """
        Add user metadata to the SKFunction being built.
        
        Args:
            metadata: Dictionary of metadata to add
            override_existing: Whether to override existing metadata keys
            
        Returns:
            SKFunctionBuilder: self for method chaining
        """
        if override_existing:
            self.metadata.update(metadata)
        else:
            # Only add keys that don't exist
            for key, value in metadata.items():
                if key not in self.metadata:
                    self.metadata[key] = value
                else:
                    print(f"Warning: Metadata key '{key}' already exists. "
                        f"Use override_existing=True to override.")
        return self

    def add_args_from_tuple(self, args: Tuple) -> 'SKFunctionBuilder':
        """Add positional arguments, appending to existing arguments."""
        
        if not self.signature:
            # No signature info, just append with generated names
            start_index = len(self.provided_args)
            for i, arg_value in enumerate(args):
                self.provided_args.append((f"arg_{start_index + i}", arg_value))
            return self
        
        # Get existing argument count to know where to start
        existing_positional_count = len([item for item in self.provided_args if item is not None])
        param_names = list(self.signature.parameters.keys())
        
        for i, arg_value in enumerate(args):
            param_index = existing_positional_count + i
            if param_index < len(param_names):
                param_name = param_names[param_index]
                self.add_argument(param_name, arg_value, override_existing=True)
            else:
                # Beyond available parameters, add to kwargs
                self.provided_kwargs[f"extra_arg_{param_index}"] = arg_value
        
        return self

    def validate(self) -> bool:
        """Validate that the builder has enough information to create an SKFunction."""
        if self.func is None:
            print("Error: No function set. Call add_callable() first.")
            return False
        
        if not self.signature:
            return True  # Can't validate without signature
        
        # Build a complete argument mapping
        final_args_mapping = {}
        
        # Map positional arguments by position
        param_names = list(self.signature.parameters.keys())
        for i, item in enumerate(self.provided_args):
            if item is not None and isinstance(item, tuple) and len(item) == 2:
                param_name, param_value = item
                final_args_mapping[param_name] = param_value
            elif item is not None:
                # Direct value, map by position
                if i < len(param_names):
                    final_args_mapping[param_names[i]] = item
        
        # Add keyword arguments
        final_args_mapping.update(self.provided_kwargs)
        
        # Check required parameters
        required_params = [
            name for name, info in self.param_info.items()
            if not info['has_default'] and info['kind'] != inspect.Parameter.VAR_KEYWORD
        ]
        
        missing_required = [param for param in required_params if param not in final_args_mapping]
        
        if missing_required:
            print(f"Error: Missing required parameters: {', '.join(missing_required)}")
            return False
        
        return True        

    def build(self) -> SKFunction:
        """
        Build the SKFunction.
        
        Returns:
            The constructed SKFunction
            
        Raises:
            SKFunctionBuildError: If validation fails
        """
        if not self.validate():
            raise SKFunctionBuildError("Builder validation failed")
        
        # Extract values from provided_args (they're stored as tuples of (name, value))
        final_args = []
        for item in self.provided_args:
            if item is not None:
                if isinstance(item, tuple) and len(item) == 2:
                    final_args.append(item[1])  # Take the value part
                else:
                    final_args.append(item)  # Direct value
        
        final_args = tuple(final_args)
        
        # Create the SKFunction
        sk_func = SKFunction(
            func=self.func,
            args=final_args,
            kwargs=self.provided_kwargs,
            name=self.name,
            description=self.description,
            autoregister=False  # We'll handle registration in __exit__
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
    Edit an existing SKFunction by creating a modified copy.
    
    This creates a new SKFunction based on the existing one but with 
    modifications you specify. The new function can optionally replace
    the old one in the registry.
    
    Args:
        skfunction: The SKFunction to edit
        additional_args: Additional positional arguments to add
        additional_kwargs: Additional keyword arguments to add  
        new_name: New name for the function
        new_description: New description for the function
        new_metadata: New metadata to add/update
        
    Returns:
        SKFunction: A new SKFunction instance with the modifications
        
    Example:
        original_func = get_function("my_function")
        modified_func = edit_skfunction(
            original_func,
            additional_kwargs={"debug": True},
            new_name="my_function_debug"
        )
    """
    if not isinstance(skfunction, SKFunction):
        raise SKFunctionError("The provided object is not an SKFunction instance.")
    
    # Check if function is registered so we know whether to re-register
    skfrej = RejSingleton.get_registry("SKFunctions")
    was_registered = skfunction.metadata.name in skfrej if skfrej else False
    
    with SKFunctionBuilder(autoregister=was_registered, editing_existing=True) as builder:
        # Load the existing function
        builder.edit_skfunction(skfunction)
        
        # Add any additional arguments
        if additional_args:
            builder.add_args_from_tuple(additional_args)
        
        if additional_kwargs:
            builder.add_kwargs(additional_kwargs)
        
        # Update properties if provided
        if new_name:
            builder.set_name(new_name)
        if new_description:
            builder.set_description(new_description)
        if new_metadata:
            builder.add_metadata(new_metadata, override_existing=True)
        
        # Build the modified function
        modified_func = builder.build()
    
    return modified_func

def get_function(name: str) -> Optional['SKFunction']:
    """
    Get a registered SKFunction by name from the global registry.
    
    Args:
        name: Name of the function to retrieve
        
    Returns:
        SKFunction or None: The function if found, None otherwise
        
    Example:
        my_func = get_function("database_connect")
        if my_func:
            result = my_func.call()
    """
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")  # Keep serialization checking enabled
        return skfrej.get(name)
    except Exception as e:
        print(f"Warning: Could not access function registry: {e}")
        return None

def list_functions() -> List[str]:
    """
    Get a list of all registered function names.
    
    Returns:
        List[str]: List of function names in the registry
    """
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")  # Keep serialization checking enabled
        return skfrej.list_keys()
    except Exception as e:
        print(f"Warning: Could not access function registry: {e}")
        return []

def remove_function(name: str) -> bool:
    """
    Remove a function from the global registry.
    
    Args:
        name: Name of the function to remove
        
    Returns:
        bool: True if function existed and was removed, False otherwise
    """
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")  # Keep serialization checking enabled
        return skfrej.remove(name)
    except Exception as e:
        print(f"Warning: Could not access function registry: {e}")
        return False

def convert_callable(func: Callable, 
                    name: Optional[str] = None,
                    description: Optional[str] = None,
                    autoregister: bool = True) -> 'SKFunction':
    """
    Convert a regular callable to an SKFunction.
    
    Args:
        func: The callable to convert
        name: Optional name (defaults to function's __name__)
        description: Optional description
        autoregister: Whether to register in global registry
        
    Returns:
        SKFunction: The wrapped function
        
    Example:
        def my_func(x, y):
            return x + y
        
        sk_func = convert_callable(my_func, description="Adds two numbers")
    """
    return SKFunction(
        func=func,
        name=name or getattr(func, '__name__', 'unknown'),
        description=description or "",
        autoregister=autoregister
    )

def autoregister(name: Optional[str] = None, 
                description: Optional[str] = None):
    """
    Decorator to automatically convert a function to SKFunction and register it.
    
    Args:
        name: Optional name for the function
        description: Optional description
        
    Returns:
        The decorated function as an SKFunction
        
    Example:
        @autoregister(description="Calculates factorial")
        def factorial(n):
            return 1 if n <= 1 else n * factorial(n-1)
        
        # factorial is now an SKFunction and registered globally
        result = factorial.call([5])  # or factorial(5)
    """
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
    """
    Check if a function can be registered in the cross-process registry.
    
    Args:
        func: Function to test
        
    Returns:
        bool: True if it can be registered, False otherwise
    """
    try:
        cereal = Cereal()
        return cereal.serializable(func, mode='internal')
    except:
        return False

# =============================================================================
# COMPREHENSIVE TESTS
# =============================================================================

if __name__ == "__main__":
    def run_comprehensive_tests():
        """Run comprehensive tests for SKFunction and SKFunctionBuilder."""
        print("🧪 Starting SKFunction Comprehensive Tests...")
        print("=" * 80)
        
        # Test counters
        passed = 0
        total = 0
        
        def test(name: str, test_func):
            nonlocal passed, total
            total += 1
            try:
                print(f"\n🔍 Testing: {name}")
                test_func()
                print(f"   ✅ PASSED: {name}")
                passed += 1
            except Exception as e:
                print(f"   ❌ FAILED: {name}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
        
        # =====================================================================
        # Basic SKFunction Tests
        # =====================================================================
        
        def test_basic_skfunction_creation():
            """Test creating a basic SKFunction."""
            skf = SKFunction(
                func=simple_add,
                args=(5, 3),
                name="test_add",
                description="Test addition function",
                autoregister=False
            )
            
            assert skf.metadata.name == "test_add"
            assert skf.metadata.description == "Test addition function"
            assert skf.args == (5, 3)
            assert skf.kwargs == {}
            assert callable(skf.func)
            
            # Test calling
            result = skf.call()
            assert result == 8, f"Expected 8, got {result}"
            
            # Test call count tracking
            assert skf.call_count == 1
            
            print(f"   Created SKFunction: {skf}")
        
        test("Basic SKFunction Creation", test_basic_skfunction_creation)
        
        def test_skfunction_with_kwargs():
            """Test SKFunction with keyword arguments."""
            skf = SKFunction(
                func=complex_function,
                args=(42, "test"),
                kwargs={"c": 2.71, "keyword_only": True},
                name="test_complex",
                autoregister=False
            )
            
            result = skf.call()
            expected = {
                'a': 42, 'b': "test", 'c': 2.71, 'd': "default",
                'keyword_only': True, 'extra': {}
            }
            assert result == expected
            
            print(f"   Result: {result}")
        
        test("SKFunction with Kwargs", test_skfunction_with_kwargs)
        
        def test_skfunction_call_with_additional_args():
            """Test calling SKFunction with additional arguments."""
            # Create function with partial args
            skf = SKFunction(
                func=complex_function,
                args=(10,),  # Only provide 'a'
                name="partial_function",
                autoregister=False
            )
            
            # Call with additional named arguments
            result = skf.call(
                additional_args=[("b", "hello"), ("d", "world")],
                additional_kwargs={"keyword_only": True, "extra_key": "extra_value"}
            )
            
            expected = {
                'a': 10, 'b': "hello", 'c': 3.14, 'd': "world",
                'keyword_only': True, 'extra': {"extra_key": "extra_value"}
            }
            assert result == expected
            
            print(f"   Result with additional args: {result}")
        
        test("SKFunction Call with Additional Args", test_skfunction_call_with_additional_args)
        
        def test_skfunction_call_with_positional_args():
            """Test calling SKFunction with additional positional arguments."""
            skf = SKFunction(
                func=simple_add,
                args=(5,),  # Only provide first argument
                name="partial_add",
                autoregister=False
            )
            
            # Add second argument positionally
            result = skf.call(additional_args=(3,))
            assert result == 8
            
            print(f"   Result with positional args: {result}")
        
        test("SKFunction Call with Positional Args", test_skfunction_call_with_positional_args)
        
        def test_skfunction_performance_tracking():
            """Test performance tracking features."""
            skf = SKFunction(
                func=simple_multiply,
                args=(6, 7),
                autoregister=False
            )
            
            # Call multiple times
            for i in range(3):
                result = skf.call()
                assert result == 42
            
            # Check performance tracking
            assert skf.call_count == 3
            assert skf.last_called is not None
            assert skf.total_execution_time > 0
            assert skf.avg_execution_time > 0
            
            print(f"   Call count: {skf.call_count}")
            print(f"   Avg execution time: {skf.avg_execution_time:.6f}s")
        
        test("SKFunction Performance Tracking", test_skfunction_performance_tracking)
        
        def test_skfunction_direct_call():
            """Test calling SKFunction directly using __call__."""
            skf = SKFunction(
                func=simple_add,
                args=(2, 3),
                autoregister=False
            )
            
            # Call directly
            result = skf()
            assert result == 5
            
            # Test with partial function - create new one for this test
            partial_skf = SKFunction(
                func=simple_add,
                args=(10,),  # Only first arg
                autoregister=False
            )
            result2 = partial_skf(20)  # Add second arg
            assert result2 == 30
            
            print(f"   Direct call result: {result}")
            print(f"   Partial call result: {result2}")
        
        test("SKFunction Direct Call", test_skfunction_direct_call)
        
        # =====================================================================
        # SKFunctionBuilder Tests
        # =====================================================================
        
        def test_basic_builder():
            """Test basic SKFunctionBuilder functionality."""
            with SKFunctionBuilder(autoregister=False) as builder:
                builder.add_callable(simple_add)
                builder.add_argument("a", 10, override_existing=True)
                builder.add_argument("b", 20, override_existing=True)
                builder.set_name("builder_add")
                builder.set_description("Built with builder")
                
                skf = builder.build()
            
            assert skf.metadata.name == "builder_add"
            assert skf.metadata.description == "Built with builder"
            
            result = skf.call()
            assert result == 30
            
            print(f"   Built function: {skf}")
        
        test("Basic Builder", test_basic_builder)
        
        def test_builder_with_complex_function():
            """Test builder with a complex function signature."""
            with SKFunctionBuilder(autoregister=False) as builder:
                builder.add_callable(complex_function)
                builder.add_argument("a", 100, override_existing=True)
                builder.add_argument("b", "builder_test", override_existing=True)
                builder.add_kwargs({"c": 1.41, "keyword_only": True})
                builder.add_metadata({"test_key": "test_value"})
                
                skf = builder.build()
            
            result = skf.call()
            expected = {
                'a': 100, 'b': "builder_test", 'c': 1.41, 'd': "default",
                'keyword_only': True, 'extra': {}
            }
            assert result == expected
            
            print(f"   Complex function result: {result}")
        
        test("Builder with Complex Function", test_builder_with_complex_function)
        
        def test_builder_add_skfunction():
            """Test builder.add_skfunction() method."""
            # Create original SKFunction
            original = SKFunction(
                func=simple_multiply,
                args=(3, 4),
                name="original_multiply",
                description="Original function",
                autoregister=False
            )
            
            # Use builder to modify it
            with SKFunctionBuilder(autoregister=False) as builder:
                builder.add_skfunction(original)
                builder.add_argument("x", 5, override_existing=True)  # Override first arg
                builder.set_name("modified_multiply")
                
                modified = builder.build()
            
            # Original should still work
            assert original.call() == 12  # 3 * 4
            
            # Modified should use new args
            assert modified.call() == 20  # 5 * 4
            assert modified.metadata.name == "modified_multiply"
            
            print(f"   Original result: {original.call()}")
            print(f"   Modified result: {modified.call()}")
        
        test("Builder add_skfunction", test_builder_add_skfunction)
        
        def test_builder_validation():
            """Test builder validation for missing required parameters."""
            # This should fail validation
            with SKFunctionBuilder(autoregister=False) as builder:
                builder.add_callable(function_with_required_params)
                builder.add_argument("a", 1, override_existing=True)
                # Missing 'b' and 'c'
                
                try:
                    skf = builder.build()
                    assert False, "Should have failed validation"
                except SKFunctionBuildError:
                    print("   Correctly caught validation error")
        
        test("Builder Validation", test_builder_validation)
        
        # =====================================================================
        # Registry Tests (using module-level functions that can be serialized)
        # =====================================================================
        
        def test_autoregister():
            """Test automatic registration functionality."""
            # Create with autoregister=True (default) using module-level function
            skf = SKFunction(
                func=simple_add,
                args=(7, 8),
                name="registered_add"
            )
            
            # Should be in registry
            retrieved = get_function("registered_add")
            assert retrieved is not None
            assert retrieved.metadata.name == "registered_add"
            assert retrieved.call() == 15
            
            # Clean up
            removed = remove_function("registered_add")
            assert removed == True
            
            print(f"   Retrieved from registry: {retrieved}")
        
        test("Autoregister", test_autoregister)
        
        def test_registry_functions():
            """Test registry utility functions."""
            # Create some test functions using module-level functions
            skf1 = SKFunction(simple_add, name="test_func1")
            skf2 = SKFunction(simple_multiply, name="test_func2")
            
            # List functions
            functions = list_functions()
            assert "test_func1" in functions
            assert "test_func2" in functions
            
            # Get specific function
            retrieved = get_function("test_func1")
            assert retrieved is not None
            assert retrieved.metadata.name == "test_func1"
            
            # Remove functions
            assert remove_function("test_func1") == True
            assert remove_function("test_func2") == True
            assert get_function("test_func1") is None
            
            print(f"   Found functions: {[f for f in functions if f.startswith('test_func')]}")
        
        test("Registry Functions", test_registry_functions)
        
        # =====================================================================
        # Decorator Tests
        # =====================================================================
        
        def test_convert_callable():
            """Test convert_callable function."""            
            skf = convert_callable(
                test_function, 
                name="converted_func",
                description="Converted function",
                autoregister=False
            )
            
            assert skf.metadata.name == "converted_func"
            assert skf.metadata.description == "Converted function"
            
            # Test with preset args
            skf_with_args = SKFunction(
                func=skf.func,
                args=(3, 4),
                autoregister=False
            )
            result = skf_with_args.call()
            assert result == 13  # 3 * 4 + 1
            
            print(f"   Converted function result: {result}")
        
        test("Convert Callable", test_convert_callable)
        
        def test_autoregister_decorator():
            """Test @autoregister decorator."""
            @autoregister(name="decorated_func", description="Decorated function")
            def factorial(n: int) -> int:
                return 1 if n <= 1 else n * factorial.func(n-1)  # Use .func to avoid SKFunction overhead
            
            # Should be registered
            retrieved = get_function("decorated_func")
            assert retrieved is not None
            
            # Test calling (need to provide args since decorator doesn't preset them)
            skf_with_args = SKFunction(
                func=factorial.func,
                args=(5,),
                autoregister=False
            )
            result = skf_with_args.call()
            assert result == 120  # 5!
            
            # Clean up
            remove_function("decorated_func")
            
            print(f"   Factorial result: {result}")
        
        test("Autoregister Decorator", test_autoregister_decorator)
        
        # =====================================================================
        # Module-level edit_skfunction Tests
        # =====================================================================
        
        def test_module_edit_skfunction():
            """Test module-level edit_skfunction function."""
            # Create original function
            original = SKFunction(
                func=complex_function,
                args=(1, "original"),
                name="editable_func",
                description="Original description",
                autoregister=False
            )
            
            # Edit it
            modified = edit_skfunction(
                original,
                additional_args=(99,),  # This should be added positionally
                additional_kwargs={"keyword_only": True},
                new_name="edited_func",
                new_description="Edited description"
            )
            
            # Original should be unchanged
            orig_result = original.call()
            assert orig_result['a'] == 1
            assert orig_result['b'] == "original"
            
            # Modified should have changes
            mod_result = modified.call()
            assert mod_result['a'] == 1  # From original args
            assert mod_result['b'] == "original"  # From original args  
            assert mod_result['keyword_only'] == True  # From additional_kwargs
            assert modified.metadata.name == "edited_func"
            assert modified.metadata.description == "Edited description"
            
            print(f"   Original result: {orig_result}")
            print(f"   Modified result: {mod_result}")
        
        test("Module-level edit_skfunction", test_module_edit_skfunction)
        
        # =====================================================================
        # Error Handling Tests
        # =====================================================================
        
        def test_error_handling():
            """Test error handling in SKFunction calls."""            
            skf = SKFunction(
                func=error_function,
                name="error_func",
                autoregister=False
            )
            
            try:
                skf.call()
                assert False, "Should have raised SKFunctionError"
            except SKFunctionError as e:
                assert "Test error" in str(e)
                print(f"   Correctly caught error: {e}")
            
            # Check that error was recorded
            assert skf.call_count == 1  # Should still count failed calls
        
        test("Error Handling", test_error_handling)
        
        def test_invalid_function():
            """Test creating SKFunction with invalid function."""
            try:
                SKFunction(func="not a function", autoregister=False)
                assert False, "Should have raised SKFunctionError"
            except SKFunctionError as e:
                assert "not callable" in str(e)
                print(f"   Correctly caught invalid function error: {e}")
        
        test("Invalid Function", test_invalid_function)
        
        # =====================================================================
        # Serialization Tests
        # =====================================================================
        
        def test_serialization_check():
            """Test the serialization checking utility."""
            # Module-level function should be serializable
            assert can_register_function(simple_add) == True
            
            # Local function should not be
            def local_func():
                return 42
            
            assert can_register_function(local_func) == False
            
            print("   Serialization checking works correctly")
        
        test("Serialization Check", test_serialization_check)
        
        def test_non_serializable_functions():
            """Test that we can still work with non-serializable functions if we don't register them."""
            
            # Define a local function (not serializable)
            def local_function(x, y):
                return x * y * 2
            
            # Create SKFunction but don't auto-register
            skf = SKFunction(
                func=local_function,
                args=(3, 4),
                name="local_func",
                autoregister=False  # Key: don't try to register non-serializable
            )
            
            # Should still work for local use
            result = skf.call()
            assert result == 24
            
            # Just can't be registered for cross-process use (which is correct behavior)
            print("   Non-serializable function works locally but can't be registered (correct)")
        
        test("Non-serializable Functions", test_non_serializable_functions)
        
        # =====================================================================
        # Print Results
        # =====================================================================
        
        print("\n" + "=" * 80)
        print(f"🏁 Test Results: {passed}/{total} passed")
        if passed == total:
            print("🎉 All SKFunction tests passed!")
            print("\n🎯 Key Features Tested:")
            print("   ✅ Basic SKFunction creation and calling")
            print("   ✅ Complex argument handling (named, positional, kwargs)")
            print("   ✅ Performance tracking and metadata")
            print("   ✅ SKFunctionBuilder with validation")
            print("   ✅ Registry management (register, retrieve, remove)")
            print("   ✅ Decorators and utility functions")
            print("   ✅ Error handling and edge cases")
            print("   ✅ Serialization safety and cross-process support")
        else:
            print(f"⚠️  {total - passed} tests failed")
        print("=" * 80)
        
        # Clean up any remaining test functions
        test_functions = [f for f in list_functions() if f.startswith(('test_', 'registered_', 'decorated_', 'editable_', 'error_'))]
        for func_name in test_functions:
            remove_function(func_name)
        
        if test_functions:
            print(f"🧹 Cleaned up {len(test_functions)} test functions from registry")
    
    # Run the tests
    run_comprehensive_tests()