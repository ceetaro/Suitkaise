"""
Dynamically Imported Modules Serialization Handler

This module provides serialization support for dynamically imported module
objects that cannot be pickled due to their complex internal state, code
objects, and environment dependencies.

SUPPORTED OBJECTS:
==================

1. DYNAMICALLY IMPORTED MODULES:
   - Modules imported with importlib.import_module()
   - Modules imported with __import__()
   - Modules loaded from custom paths

2. MODULE TYPES:
   - Standard library modules
   - Third-party packages
   - User-defined modules
   - Package modules with submodules
   - Extension modules (C/C++, Cython)

3. SPECIAL MODULE CASES:
   - Modules with custom __path__ attributes
   - Namespace packages
   - Modules imported from zip files
   - Modules with reload() called on them
   - Modules imported conditionally

4. MODULE METADATA:
   - Module name and package hierarchy
   - File path and location information
   - Import timestamp and loader information
   - Module attributes and exported names

SERIALIZATION STRATEGY:
======================

Module serialization is challenging because modules contain:
- Compiled code objects (not serializable)
- Global namespace with complex objects
- Import system state and dependencies
- File system references and paths
- Cached compilation results

Our approach:
1. **Store import information** (name, package, path)
2. **Preserve module metadata** (version, attributes, exports)
3. **Store import context** (how it was imported)
4. **Handle missing modules** gracefully during deserialization
5. **Recreate import** using standard import mechanisms
6. **Provide placeholder modules** when imports fail

LIMITATIONS:
============
- Module global state is not preserved
- Dynamically modified modules lose modifications
- C extension modules may not be available in target environment
- Custom import hooks and loaders are not preserved
- Module-level side effects are not replayed
- Circular import dependencies may cause issues
- sys.modules cache state is not preserved

"""

import sys
import types
import importlib
import importlib.util
import os
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Set

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class DynamicModulesHandler(_NSO_Handler):
    """Handler for dynamically imported module objects."""
    
    def __init__(self):
        """Initialize the dynamic modules handler."""
        super().__init__()
        self._handler_name = "DynamicModulesHandler"
        self._priority = 5  # Lower priority since modules are less common to serialize
        
        # Built-in modules that should always be available
        self._builtin_modules = set(sys.builtin_module_names)
        
        # Standard library modules (Python 3.6+ pattern)
        self._stdlib_prefixes = {
            'collections', 'itertools', 'functools', 'operator', 'pathlib',
            'os', 'sys', 'io', 'json', 'pickle', 'datetime', 'time',
            'random', 'math', 'statistics', 'string', 'typing'
        }
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given module object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for types.ModuleType objects
        - Check for objects with module characteristics
        - Exclude certain system modules that shouldn't be serialized
        """
        try:
            # Direct module type check
            if isinstance(obj, types.ModuleType):
                # Don't handle certain system modules
                module_name = getattr(obj, '__name__', '')
                
                # Exclude main module and special modules
                excluded_modules = {
                    '__main__', '__builtin__', '__builtins__',
                    'sys', 'builtins'  # These are too fundamental
                }
                
                if module_name in excluded_modules:
                    return False
                
                return True
            
            # Check for module-like objects
            obj_type_name = type(obj).__name__
            if obj_type_name == 'module':
                return True
            
            # Check for objects that look like modules
            has_name = hasattr(obj, '__name__')
            has_file = hasattr(obj, '__file__')
            has_package = hasattr(obj, '__package__')
            
            # Must have at least name and one of file/package
            if has_name and (has_file or has_package):
                return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: types.ModuleType) -> Dict[str, Any]:
        """
        Serialize a module object to a dictionary representation.
        
        Args:
            obj: Module object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the module
            
        SERIALIZATION PROCESS:
        1. Extract module identification information
        2. Store import path and loader information
        3. Capture module metadata and attributes
        4. Determine recreation strategy based on module type
        5. Handle special cases (packages, extensions, etc.)
        """
        # Base serialization data
        data = {
            "module_name": getattr(obj, '__name__', '<unknown>'),
            "module_file": getattr(obj, '__file__', None),
            "module_package": getattr(obj, '__package__', None),
            "module_path": getattr(obj, '__path__', None),
            "module_spec": None,
            "module_loader": None,
            "module_type": self._get_module_type(obj),
            "module_attributes": {},
            "import_context": {},
            "serialization_strategy": None,
            "recreation_possible": False,
            "note": None
        }
        
        try:
            # Extract module spec information
            if hasattr(obj, '__spec__') and obj.__spec__:
                spec = obj.__spec__
                data["module_spec"] = {
                    "name": getattr(spec, 'name', None),
                    "origin": getattr(spec, 'origin', None),
                    "submodule_search_locations": getattr(spec, 'submodule_search_locations', None),
                    "loader_class": type(spec.loader).__name__ if spec.loader else None,
                    "has_location": getattr(spec, 'has_location', False)
                }
            
            # Extract loader information
            if hasattr(obj, '__loader__') and obj.__loader__:
                loader = obj.__loader__
                data["module_loader"] = {
                    "loader_class": type(loader).__name__,
                    "loader_module": getattr(type(loader), '__module__', None)
                }
            
            # Extract import context
            data["import_context"] = self._extract_import_context(obj)
            
            # Extract safe module attributes
            data["module_attributes"] = self._extract_module_attributes(obj)
            
            # Determine serialization strategy
            module_type = data["module_type"]
            if module_type == "builtin":
                data["serialization_strategy"] = "builtin_import"
                data["recreation_possible"] = True
            
            elif module_type == "stdlib":
                data["serialization_strategy"] = "stdlib_import"
                data["recreation_possible"] = True
            
            elif module_type == "third_party":
                data["serialization_strategy"] = "package_import"
                data["recreation_possible"] = True
            
            elif module_type == "user_module":
                data["serialization_strategy"] = "file_import"
                data["recreation_possible"] = bool(data["module_file"])
            
            elif module_type == "extension":
                data["serialization_strategy"] = "extension_import"
                data["recreation_possible"] = True
            
            else:
                data["serialization_strategy"] = "dynamic_import"
                data["recreation_possible"] = bool(data["module_name"])
            
        except Exception as e:
            data["note"] = f"Error extracting module information: {e}"
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> types.ModuleType:
        """
        Deserialize a module object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized module data
            
        Returns:
            Recreated module object (or placeholder if import fails)
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Attempt to import module using appropriate method
        3. Validate that the imported module matches expected characteristics
        4. Handle import failures gracefully with placeholders
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        module_name = data.get("module_name", "unknown")
        
        try:
            if strategy == "builtin_import":
                return self._import_builtin_module(data)
            
            elif strategy == "stdlib_import":
                return self._import_stdlib_module(data)
            
            elif strategy == "package_import":
                return self._import_package_module(data)
            
            elif strategy == "file_import":
                return self._import_file_module(data)
            
            elif strategy == "extension_import":
                return self._import_extension_module(data)
            
            elif strategy == "dynamic_import":
                return self._import_dynamic_module(data)
            
            elif strategy == "fallback_placeholder":
                return self._create_module_placeholder(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a placeholder module
            return self._create_module_placeholder(data, str(e))
    
    # ========================================================================
    # MODULE TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_module_type(self, obj: types.ModuleType) -> str:
        """
        Determine the specific type of module.
        
        Args:
            obj: Module object to analyze
            
        Returns:
            String identifying the module type
        """
        module_name = getattr(obj, '__name__', '')
        module_file = getattr(obj, '__file__', None)
        
        # Built-in modules
        if module_name in self._builtin_modules:
            return "builtin"
        
        # Check if it's a standard library module
        if self._is_stdlib_module(obj):
            return "stdlib"
        
        # Extension modules (C/C++/Cython)
        if module_file and (module_file.endswith('.so') or 
                           module_file.endswith('.pyd') or 
                           module_file.endswith('.dll')):
            return "extension"
        
        # Check if it's a third-party package
        if module_file and ('site-packages' in module_file or 
                           'dist-packages' in module_file):
            return "third_party"
        
        # User modules (local files)
        if module_file and module_file.endswith('.py'):
            return "user_module"
        
        # Namespace packages or other special cases
        if hasattr(obj, '__path__'):
            return "package"
        
        # Default to unknown
        return "unknown"
    
    def _is_stdlib_module(self, obj: types.ModuleType) -> bool:
        """
        Check if a module is part of the standard library.
        
        Args:
            obj: Module object to check
            
        Returns:
            True if module is from standard library
        """
        module_name = getattr(obj, '__name__', '')
        module_file = getattr(obj, '__file__', None)
        
        # Check name prefixes
        for prefix in self._stdlib_prefixes:
            if module_name.startswith(prefix):
                return True
        
        # Check file path (heuristic)
        if module_file:
            # Standard library modules are typically in Python installation
            stdlib_indicators = [
                'lib/python',
                'Lib/',  # Windows
                '/usr/lib/python',
                '/usr/local/lib/python'
            ]
            
            for indicator in stdlib_indicators:
                if indicator in module_file:
                    return True
        
        return False
    
    def _extract_import_context(self, obj: types.ModuleType) -> Dict[str, Any]:
        """
        Extract context information about how the module was imported.
        
        Args:
            obj: Module object
            
        Returns:
            Dictionary with import context information
        """
        context = {
            "in_sys_modules": obj.__name__ in sys.modules,
            "module_cached": False,
            "import_time": None
        }
        
        try:
            # Check if module is cached
            if obj.__name__ in sys.modules:
                context["module_cached"] = sys.modules[obj.__name__] is obj
            
            # Try to get module creation time (heuristic)
            if hasattr(obj, '__file__') and obj.__file__:
                try:
                    stat_info = os.stat(obj.__file__)
                    context["file_mtime"] = stat_info.st_mtime
                except (OSError, AttributeError):
                    pass
        
        except Exception:
            pass  # Context extraction is optional
        
        return context
    
    def _extract_module_attributes(self, obj: types.ModuleType) -> Dict[str, Any]:
        """
        Extract safe module attributes for debugging and validation.
        
        Args:
            obj: Module object
            
        Returns:
            Dictionary with module attributes
        """
        attributes = {}
        
        try:
            # Standard module attributes
            standard_attrs = [
                '__name__', '__doc__', '__file__', '__package__',
                '__version__', '__author__', '__email__'
            ]
            
            for attr_name in standard_attrs:
                if hasattr(obj, attr_name):
                    attr_value = getattr(obj, attr_name)
                    if isinstance(attr_value, (str, int, float, bool, type(None))):
                        attributes[attr_name] = attr_value
            
            # Try to get exported names
            if hasattr(obj, '__all__'):
                all_items = getattr(obj, '__all__')
                if isinstance(all_items, (list, tuple)):
                    attributes["__all__"] = list(all_items)
            
            # Count of module contents (for validation)
            try:
                all_names = [name for name in dir(obj) if not name.startswith('_')]
                attributes["public_names_count"] = len(all_names)
                attributes["public_names_sample"] = all_names[:10]  # First 10 names
            except Exception:
                pass
        
        except Exception:
            pass  # Attribute extraction is optional
        
        return attributes
    
    # ========================================================================
    # MODULE IMPORT METHODS
    # ========================================================================
    
    def _import_builtin_module(self, data: Dict[str, Any]) -> types.ModuleType:
        """
        Import built-in modules.
        """
        module_name = data["module_name"]
        
        if module_name not in self._builtin_modules:
            raise ImportError(f"Module {module_name} is not a built-in module")
        
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Failed to import built-in module {module_name}: {e}")
    
    def _import_stdlib_module(self, data: Dict[str, Any]) -> types.ModuleType:
        """
        Import standard library modules.
        """
        module_name = data["module_name"]
        
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Failed to import stdlib module {module_name}: {e}")
    
    def _import_package_module(self, data: Dict[str, Any]) -> types.ModuleType:
        """
        Import third-party package modules.
        """
        module_name = data["module_name"]
        
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Failed to import package module {module_name}: {e}")
    
    def _import_file_module(self, data: Dict[str, Any]) -> types.ModuleType:
        """
        Import modules from file paths.
        """
        module_name = data["module_name"]
        module_file = data["module_file"]
        
        if not module_file or not os.path.exists(module_file):
            # Try standard import as fallback
            try:
                return importlib.import_module(module_name)
            except ImportError:
                raise ImportError(f"Module file {module_file} not found and module {module_name} not importable")
        
        try:
            # Import from file using importlib
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            if spec is None:
                raise ImportError(f"Could not create spec for {module_name} from {module_file}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules before execution
            sys.modules[module_name] = module
            
            # Execute the module
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            # Clean up sys.modules if we added it
            if module_name in sys.modules:
                del sys.modules[module_name]
            raise ImportError(f"Failed to import module from file {module_file}: {e}")
    
    def _import_extension_module(self, data: Dict[str, Any]) -> types.ModuleType:
        """
        Import extension modules (C/C++/Cython).
        """
        module_name = data["module_name"]
        
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Failed to import extension module {module_name}: {e}")
    
    def _import_dynamic_module(self, data: Dict[str, Any]) -> types.ModuleType:
        """
        Import modules using dynamic import strategies.
        """
        module_name = data["module_name"]
        module_file = data.get("module_file")
        
        # Try various import strategies
        
        # Strategy 1: Standard import
        try:
            return importlib.import_module(module_name)
        except ImportError:
            pass
        
        # Strategy 2: File-based import if file is available
        if module_file and os.path.exists(module_file):
            try:
                return self._import_file_module(data)
            except ImportError:
                pass
        
        # Strategy 3: Try importing parent package and getting submodule
        if '.' in module_name:
            try:
                parts = module_name.split('.')
                parent_name = '.'.join(parts[:-1])
                child_name = parts[-1]
                
                parent_module = importlib.import_module(parent_name)
                if hasattr(parent_module, child_name):
                    child = getattr(parent_module, child_name)
                    if isinstance(child, types.ModuleType):
                        return child
            except ImportError:
                pass
        
        # All strategies failed
        raise ImportError(f"Could not import module {module_name} using any strategy")
    
    # ========================================================================
    # MODULE PLACEHOLDER CREATION
    # ========================================================================
    
    def _create_module_placeholder(self, data: Dict[str, Any], error_message: str = None) -> types.ModuleType:
        """
        Create a placeholder module for modules that failed to import.
        
        Args:
            data: Serialized module data
            error_message: Optional error message
            
        Returns:
            Placeholder module object
        """
        module_name = data.get("module_name", "unknown_module")
        module_attributes = data.get("module_attributes", {})
        
        # Create a new module object
        placeholder_module = types.ModuleType(module_name)
        
        # Set basic attributes
        placeholder_module.__name__ = module_name
        placeholder_module.__doc__ = f"Placeholder for module {module_name}"
        placeholder_module.__file__ = data.get("module_file", "<unavailable>")
        placeholder_module.__package__ = data.get("module_package")
        
        # Add original attributes if they were simple types
        for attr_name, attr_value in module_attributes.items():
            if isinstance(attr_value, (str, int, float, bool, type(None), list)):
                try:
                    setattr(placeholder_module, attr_name, attr_value)
                except Exception:
                    pass
        
        # Add error information
        placeholder_module.__cerial_placeholder__ = True
        placeholder_module.__cerial_error__ = error_message or "Module could not be imported"
        placeholder_module.__cerial_original_data__ = data
        
        # Add a warning function that gets called when the module is used
        def _placeholder_warning():
            print(f"Warning: Using placeholder for module {module_name}. "
                  f"Original module could not be imported: {placeholder_module.__cerial_error__}")
        
        placeholder_module._cerial_warning = _placeholder_warning
        
        # Override __getattr__ to provide helpful error messages
        def __getattr__(name):
            _placeholder_warning()
            raise AttributeError(f"Placeholder module {module_name} has no attribute '{name}'. "
                               f"Original module import failed: {placeholder_module.__cerial_error__}")
        
        placeholder_module.__getattr__ = __getattr__
        
        return placeholder_module
    
    # ========================================================================
    # MODULE VALIDATION METHODS
    # ========================================================================
    
    def validate_module_import(self, obj: types.ModuleType, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that an imported module matches the original serialized module.
        
        Args:
            obj: Imported module object
            data: Original serialized module data
            
        Returns:
            Dictionary with validation results
        """
        results = {
            "name_matches": False,
            "file_matches": False,
            "attributes_match": False,
            "type_matches": False,
            "validation_successful": False,
            "warnings": []
        }
        
        try:
            original_name = data.get("module_name")
            original_file = data.get("module_file")
            original_attributes = data.get("module_attributes", {})
            original_type = data.get("module_type")
            
            # Check name
            current_name = getattr(obj, '__name__', None)
            results["name_matches"] = (current_name == original_name)
            if not results["name_matches"]:
                results["warnings"].append(f"Module name mismatch: {current_name} vs {original_name}")
            
            # Check file path
            current_file = getattr(obj, '__file__', None)
            results["file_matches"] = (current_file == original_file)
            if not results["file_matches"] and original_file:
                results["warnings"].append(f"Module file mismatch: {current_file} vs {original_file}")
            
            # Check key attributes
            attr_matches = 0
            attr_total = 0
            
            for attr_name, original_value in original_attributes.items():
                if attr_name in ['public_names_count', 'public_names_sample']:
                    continue  # Skip validation-only attributes
                
                attr_total += 1
                current_value = getattr(obj, attr_name, None)
                
                if current_value == original_value:
                    attr_matches += 1
                else:
                    results["warnings"].append(f"Attribute {attr_name} mismatch: {current_value} vs {original_value}")
            
            if attr_total > 0:
                results["attributes_match"] = (attr_matches / attr_total) >= 0.8  # 80% match threshold
            else:
                results["attributes_match"] = True  # No attributes to check
            
            # Check module type
            current_type = self._get_module_type(obj)
            results["type_matches"] = (current_type == original_type)
            if not results["type_matches"]:
                results["warnings"].append(f"Module type mismatch: {current_type} vs {original_type}")
            
            # Overall validation
            results["validation_successful"] = all([
                results["name_matches"],
                results["attributes_match"],
                results["type_matches"]
            ])
            
        except Exception as e:
            results["warnings"].append(f"Validation failed with error: {e}")
        
        return results


# Create a singleton instance for auto-registration
dynamic_modules_handler = DynamicModulesHandler()