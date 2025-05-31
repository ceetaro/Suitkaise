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
            is_serializable=Cereal.serializable(obj=func, serialization_mode=serialization_mode),
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
        Execute the function with its preset args and kwargs,
        along with any additional arguments provided. Additional arguments will
        be ignored if the function has preset arguments that conflict with them.

        Args:
            additional_args: additional positional arguments to pass to the function.
            additional_kwargs: additional keyword arguments to pass to the function.

        Returns:
            Any: the result of the function call.

        Raises:
            SKFunctionError: if the function execution fails.
        
        """
        stopwatch = sktime.Stopwatch()
        start_time = stopwatch.start()


        try:
            if additional_args or additional_kwargs:
                with SKFunctionBuilder() as builder:
                    builder.add_skfunction(self)
                    if additional_args:
                        if isinstance(additional_args, list):
                            for arg in additional_args:
                                builder.add_argument(arg[0], arg[1])
                        elif isinstance(additional_args, tuple):
                            builder.add_args_from_tuple(additional_args)
                    if additional_kwargs:
                        for key, value in additional_kwargs.items():
                            builder.add_kwargs({key: value})

                    skfunction = builder.build()
            else:
                skfunction = self

            result = skfunction.call()
            execution_time = stopwatch.stop()
            with self._lock:
                self.metadata.record_execution(execution_time)

            return result
        
        except Exception as e:
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
    def is_serializable(self) -> bool:
        """Whether this SKFunction can be serialized for cross-process use."""
        return self.metadata.is_serializable
    
    def get_info(self) -> Dict[str, Any]:
        """Get info about this SKFunction."""
        user_metadata = {}
        if Cereal.serializable(self.user_added_metadata):
            user_metadata = self.metadata.user_added_metadata
        else:
            for key, value in self.metadata.user_added_metadata.items():
                if not Cereal.serializable(value):
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
            skfrej = RejSingleton.get_registry("SKFunctions")
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
        if not self.built:
            raise SKFunctionBuildError("You must call build() before exiting the context manager.")
        if self.skfunction is None:
            raise SKFunctionBuildError("Something went wrong while building the SKFunction.")
        
        skfrej = RejSingleton.get_registry("SKFunctions")
        if skfrej is None:
            raise SKFunctionRegistrationError("Global SKFunctions registry not found.")
        
        if self.autoregister and not self.editing_existing:
            # register the function in the global registry
            skfrej.register(self.skfunction.metadata.name, self.skfunction)

        elif self.autoregister and self.editing_existing:
            # re-register the existing SKFunction
            skfrej.update(self.skfunction.metadata.name, self.skfunction)

 
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
        
        
        """

    def edit_skfunction(self, skfunction: 'SKFunction') -> 'SKFunctionBuilder':
        """
        Edit an existing SKFunction by adding its properties to the builder.
        Sets editing_existing to True, and might update autoregister.

        Args:
            skfunction: the SKFunction to edit.

        Returns:
            SKFunctionBuilder: self for method chaining.
        
        """
        
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
        
        # check if parameter exists in the function signature
        if not override_existing and param_name in self.param_info:
            print(
                f"Parameter '{param_name}' already exists in the function signature. "
                f"Use override_existing=True to override.")
            return self
        
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
                    
                    self.provided_args[position] = value
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
    
    def validate(self) -> bool:
        """
        Validate that the builder has enough information to create an SKFunction.
        
        Returns:
            True if valid, False otherwise
        """
        if self.func is None:
            print("Error: No function set. Call add_callable() first.")
            return False
        
        if not self.signature:
            # Can't validate without signature, but allow it
            return True
        
        # Check required parameters
        positional_params = [
            name for name, info in self.param_info.items()
            if info['kind'] in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                              inspect.Parameter.POSITIONAL_ONLY)
        ]
        
        required_params = [
            name for name in positional_params
            if not self.param_info[name]['has_default']
        ]
        
        # Check if we have enough positional arguments
        provided_positional = len([arg for arg in self.provided_args if arg is not None])
        if provided_positional < len(required_params):
            # Check if missing required params are in kwargs
            missing = []
            for i in range(provided_positional, len(required_params)):
                param_name = required_params[i]
                if param_name not in self.provided_kwargs:
                    missing.append(param_name)
            
            if missing:
                print(f"Error: Missing required parameters: {', '.join(missing)}")
                return False
        
        # Check keyword-only required parameters
        keyword_only_required = [
            name for name, info in self.param_info.items()
            if (info['kind'] == inspect.Parameter.KEYWORD_ONLY and 
                not info['has_default'])
        ]
        
        for param_name in keyword_only_required:
            if param_name not in self.provided_kwargs:
                print(f"Error: Missing required keyword-only parameter: {param_name}")
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
        
        # Filter out None values from positional args
        final_args = tuple(arg for arg in self.provided_args if arg is not None)
        
        # Create the SKFunction
        sk_func = SKFunction(
            func=self.func,
            args=final_args,
            kwargs=self.provided_kwargs,
            description=self.description
        )
        
        self.built = True
        self.skfunction = sk_func
        return sk_func


        




        



                
            

        




            

def edit_skfunction(skfunction: 'SKFunction',
                    additional_args: Optional[List[Tuple[str, Any]]] = None,
                    additional_kwargs: Optional[Dict[str, Any]] = None,
                    new_name: Optional[str] = None,
                    new_description: Optional[str] = None,
                    new_metadata: Optional[Dict[str, Any]] = None) -> 'SKFunction':
    """
    Edit an existing SKFunction by adding new arguments, changing name or description.

    Args:
        skfunction: the SKFunction to edit.
        additional_args: additional positional arguments to add.
        additional_kwargs: additional keyword arguments to add.
        new_name: new name for the SKFunction.
        new_description: new description for the SKFunction.
        new_metadata: new metadata dictionary to update.

    Returns:
        SKFunction: a new SKFunction instance with the updated properties.

    """
    if not isinstance(skfunction, SKFunction):
        raise SKFunctionError("The provided object is not an SKFunction instance.")
    
    skfrej = RejSingleton.get_registry("SKFunctions")
    if skfrej is None:
        raise SKFunctionError("Global SKFunctions registry not found.")
    
    if skfunction.metadata.name not in skfrej:
        reregister = False
    else:
        reregister = True
    
    with SKFunctionBuilder(autoregister=reregister, editing_existing=True) as builder:
        builder.add_skfunction(skfunction)

        if additional_args:
            for arg in additional_args:
                builder.add_argument(arg[0], arg[1], override_existing=True)

        if additional_kwargs:
            for key, value in additional_kwargs.items():
                builder.add_kwargs({key: value}, override_existing=True)

        if new_name:
            builder.set_name(new_name)
        if new_description:
            builder.set_description(new_description)
        if new_metadata:
            builder.add_metadata(new_metadata, override_existing=True)

        skf = builder.build()

    return skf
    