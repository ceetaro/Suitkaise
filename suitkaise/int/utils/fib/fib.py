# -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0 or the GNU General Public License v3.
#
# ~~ Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
#
# ~~ GNU General Public License, Version 3 (http://www.gnu.org/licenses/gpl-3.0.html)
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -------------------------------------------------------------------------------------

# suitkaise/int/utils/fib/function_instance_builder.py

"""
Expected usage: with FunctionInstanceBuilder() as FIB:

This module provides the FunctionInstance class, which is a container
for holding a function with specific arguments and metadata.

It also provides a builder for creating FunctionInstance objects,
FunctionInstanceBuilder, which uses a context manager to better
organize the creation of FunctionInstance objects.

"""

import inspect
import importlib
from typing import Any, Dict, Callable, Optional, List, Tuple, Union
from functools import partial

class FunctionInstance:
    """
    Container holding a function with specific arguments and metadata.

    This represents a callable function with predefined arguments, that
    can be executed later, and potentially serialized between different
    processes.
    
    """
    def __init__(self,
                 func: Callable,
                 args: Tuple = None,
                 kwargs: Dict[str, Any] = None,
                 module_name: str = None,
                 module_path: str = None,
                 func_name: str = None):
        self.func = func
        self.args = args if args is not None else ()
        self.kwargs = kwargs if kwargs is not None else {}
        self.module_path = module_path
        self.module_name = module_name or getattr(func, '__module__', None)
        self.func_name = func_name or getattr(func, '__name__', str(func))


    def execute(self) -> Any:
        """Execute the function with its arguments."""
        return self.func(*self.args, **self.kwargs)
    
    def __call__(self) -> Any:
        """Allows direct calling of the instance."""
        return self.execute()
    
    def __repr__(self) -> str:
        """String representation of the FunctionInstance."""
        func_str = f"{self.module_name}.{self.func_name}" if self.module_name else self.func_name
        args_str = ', '.join(repr(arg) for arg in self.args)
        kwargs_str = ', '.join(f"{k}={repr(v)}" for k, v in self.kwargs.items())
        all_args = ', '.join(filter(None, [args_str, kwargs_str]))
        return f"FunctionInstance({func_str}({all_args}))"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the FunctionInstance to a dictionary."""
        return {
            'module_name': self.module_name,
            'func_name': self.func_name,
            'args': self.args,
            'kwargs': self.kwargs
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FunctionInstance':
        """Create a FunctionInstance from a dictionary."""
        module_name = data['module_name']
        func_name = data['func_name']
        args = data['args']
        kwargs = data['kwargs']

        # import the module and get the function
        try:
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not import function {func_name} from module {module_name}: {e}")
        
        return cls(func, args, kwargs, module_name, func_name)
    

class FunctionInstanceBuilder:
    """
    Builder for creating FunctionInstance objects.

    Uses context manager to better organize the creation of FunctionInstance objects.
    For now, we don't do anything on __exit__, but we may in the future.

    Provides a step by step process to build a FunctionInstance, from adding
    the function and module themselves to adding arguments and kwargs with more
    clarity and precision.
    
    """
    def __init__(self):
        self.func = None
        self.module_name = None
        self.module_path = None
        self.func_name = None
        self.provided_args = [] # only args given to FIB
        self.provided_kwargs = {} # only kwargs given to FIB
        self.signature = None
        self.param_info = {} # maps param names to their metadata
        self.built = False

    def __enter__(self):
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        if not self.built:
            print("FunctionInstanceBuilder was not built. "
                  "Please call build() before exiting the context "
                  "if you would like to store the FunctionInstance.\n")

    def add_callable(self, func: Callable) -> 'FunctionInstanceBuilder':
        """
        Add a callable function to build an instance for.
        
        Args:
            func: The function to add (must be a callable object)
            
        Returns:
            self for method chaining
        """
        import sys
        import inspect
        
        if not callable(func):
            raise ValueError(f"Expected a callable function, got {type(func)}")
            
        # Store function information
        self.func = func
        self.module_name = func.__module__
        self.func_name = func.__name__
        
        # Get the module path
        module_obj = sys.modules.get(self.module_name)
        self.module_path = getattr(module_obj, '__file__', None)
        
        print(f"Using callable {self.module_name}.{self.func_name}")
        
        # Inspect function signature
        try:
            # Get parameter information
            self.signature = inspect.signature(self.func)
            
            # Store detailed information about each parameter
            for param_name, param in self.signature.parameters.items():
                self.param_info[param_name] = {
                    'kind': param.kind,
                    'default': None if param.default is param.empty else param.default,
                    'annotation': None if param.annotation is param.empty else param.annotation,
                    'has_default': param.default is not param.empty
                }
            
            print(f"Function signature: {self.signature}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Could not inspect function signature: {e}")
        
        return self


    def add_argument(self, param_name: str, 
                     value: Any,
                     override_value=False,
                     kwargs_only: bool = False) -> 'FunctionInstanceBuilder':
        """
        Add an argument to the function instance, either as a 
        positional or keyword argument.

        If the argument is not in the function signature, it will be added
        to the kwargs instead, if the function accepts kwargs.

        Args:
            param_name: The name of the parameter to add
            value: The value to assign to the parameter
            override_value: Whether to override existing values
            kwargs_only: Whether to force the argument to be added as a keyword argument

        Returns:
            self for method chaining

        """
        if not self.func:
            raise ValueError("Function not set. Please add a function first "
                             "using add_callable()\n")
        
        # ensure the parameter exists in the function
        if param_name not in self.param_info:
            # check if the function accepts arbitrary kwargs
            accepts_kwargs = any(
                param['kind'] == inspect.Parameter.VAR_KEYWORD
                for param in self.param_info.values()
            )
            if not accepts_kwargs:
                print(f"Warning: Function '{self.func_name}' does not accept "
                      f"keyword arguments. Argument '{param_name}' will not be added.\n")
                return self
            
            self.provided_kwargs[param_name] = value
            print(f"Added '{param_name}' to kwargs: {value}")
            return self
        
        # get parameter info
        param_info = self.param_info[param_name]
        param_kind = param_info['kind']

        # validate type if annotation exists
        annotation = param_info['annotation']
        if annotation is not None:
            if not isinstance(value, annotation) and value is not None:
                raise TypeError(
                    f"Parameter '{param_name}' expected type {annotation}, "
                    f"but got {type(value)} instead.\n"
                    )
                
        # determine if this should be a positional or keyword argument
        if kwargs_only:
            # Force the argument to be added as a keyword argument
            if param_name in self.provided_kwargs:
                if override_value or self.provided_kwargs[param_name] is None:
                    self.provided_kwargs[param_name] = value
                    print(f"Overriding keyword argument '{param_name}': {value}")
                else:
                    raise ValueError(f"Keyword argument '{param_name}' "
                                     f"already set with value {self.provided_kwargs[param_name]}.\n")
            else:
                self.provided_kwargs[param_name] = value
                print(f"Added keyword argument '{param_name}': {value}")
        elif param_kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                            inspect.Parameter.POSITIONAL_ONLY):
            # get the position of this parameter
            positional_params = [
                name for name, info in self.param_info.items()
                if info['kind'] in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                    inspect.Parameter.POSITIONAL_ONLY)
            ]
            position = positional_params.index(param_name)

            # check if we already have a value for this position
            if position < len(self.provided_args):
                # if we already have a value, check if we are overriding it
                if override_value or self.provided_args[position] is None:
                    self.provided_args[position] = value
                    print(f"Overriding positional argument '{param_name}' "
                          f"at position {position}: {value}")
                else:
                    raise ValueError(f"Positional argument '{param_name}' "
                                     f"already set at position {position}.\n")
                
            while len(self.provided_args) <= position:
                self.provided_args.append(None)

            # set the value at the correct position
            self.provided_args[position] = value
            print(f"Added positional argument '{param_name}' at "
                  f"position {position}: {value}")
            
        elif param_kind == inspect.Parameter.KEYWORD_ONLY:
            # check if we are overriding a keyword argument
            if param_name in self.provided_kwargs:
                if override_value or self.provided_kwargs[param_name] is None:
                    self.provided_kwargs[param_name] = value
                    print(f"Overriding keyword argument '{param_name}': {value}")
                else:
                    raise ValueError(f"Keyword argument '{param_name}' "
                                     f"already set with value {self.provided_kwargs[param_name]}.\n")
            else:
                self.provided_kwargs[param_name] = value
                print(f"Added keyword argument '{param_name}': {value}")

        elif param_kind == inspect.Parameter.VAR_POSITIONAL:
            if not isinstance(value, (list, tuple)):
                value = (value,)

            self.provided_args.extend(value)
            print(f"Added variable positional arguments '{param_name}': {value}")

        elif param_kind == inspect.Parameter.VAR_KEYWORD:
            if not isinstance(value, dict):
                raise ValueError(f"Expected a dictionary for variable keyword arguments, "
                                 f"got {type(value)} instead.\n")
            
            self.provided_kwargs.update(value)
            print(f"Added variable keyword arguments '{param_name}': {value}")

        return self
    
    def add_keyword_argument(self, param_name: str, value: Any,
                                override_value: bool = False) -> 'FunctionInstanceBuilder':
            """
            Add a keyword argument to the function instance.
    
            Args:
                param_name: The name of the parameter to add
                value: The value to assign to the parameter
                override_value: Whether to override existing values
    
            Returns:
                self for method chaining
    
            """
            return self.add_argument(param_name, value, override_value, kwargs_only=True)   
    
    def add_args(self,
                              args: List[Tuple[str, Any]],
                              override_values: bool = False,
                              kwargs_only: bool = False) -> 'FunctionInstanceBuilder':
        """
        Add multiple arguments to the function instance.

        Args:
            args: A list of tuples containing parameter names and values
            override_value: Whether to override existing values

        Returns:
            self for method chaining

        """
        for param_name, value in args:
            self.add_argument(param_name, value, override_values, kwargs_only)
        
        return self
    

    def add_kwargs(self, 
                   override_value: bool = False,
                   kwargs: Dict[str, Any] = None) -> 'FunctionInstanceBuilder':
        """
        Add keyword arguments to the function instance.

        Args:
            kwargs: A dictionary of keyword arguments

        Returns:
            self for method chaining

        """
        for param_name, value in kwargs.items():
            self.add_argument(param_name, value, override_value, kwargs_only=True)
        
        return self
    
    def validate(self) -> bool:
        """
        Validate that all required arguments are provided.

        Returns:
            bool: True if valid, False otherwise
        
        """
        if not self.func:
            raise ValueError("Function not set. Please add a function first "
                             "using add_callable()\n")
        
        # check that all required parameters have provided values
        positional_params = [
            name for name, info in self.param_info.items()
            if info['kind'] in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                inspect.Parameter.POSITIONAL_ONLY)
        ]
        required_params = [
            name for name in positional_params
            if not self.param_info[name]['has_default']
        ]

        # check if we have enough positional arguments for the required parameters
        if len(self.provided_args) < len(required_params):
            # check if any missing required parameters are in the provided kwargs
            missing = []
            for i in range(len(self.provided_args, len(required_params))):
                param_name = required_params[i]
                if param_name not in self.provided_kwargs:
                    missing.append(param_name)

            if missing:
                print(f"Missing required positional arguments: {', '.join(missing)}\n")
                return False
            
        # check that all required keyword only parameters have provided values
        keyword_only_params = [
            name for name, info in self.param_info.items()
            if info['kind'] == inspect.Parameter.KEYWORD_ONLY
        ]
        required_keyword_only_params = [
            name for name in keyword_only_params
            if not self.param_info[name]['has_default']
        ]
        for name in required_keyword_only_params:
            if name not in self.provided_kwargs:
                print(f"Missing required keyword-only argument: {name}\n")
                return False
            
        return True
    
    def build(self) -> FunctionInstance:
        """
        Build the function instance (FunctionInstance).

        Returns:
            FunctionInstance: a callable function with predefined arguments
        
        """
        self.validate()

        # create the function instance
        return FunctionInstance(
            func=self.func,
            args=tuple(self.provided_args),
            kwargs=self.provided_kwargs,
            module_name=self.module_name,
            module_path=self.module_path,
            func_name=self.func_name
        )
                    


