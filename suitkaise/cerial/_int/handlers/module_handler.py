"""
Handler for module objects.

Handles dynamically created modules (types.ModuleType) that don't exist
in the target process's sys.modules.
"""

import types
import sys
import importlib
from typing import Any, Dict
from .base_class import Handler


class ModuleSerializationError(Exception):
    """Raised when module serialization fails."""
    pass


class ModuleHandler(Handler):
    """
    Serializes types.ModuleType objects.
    
    Strategy:
    - For standard modules: just store the name (can be imported in target)
    - For dynamic modules: serialize the module's __dict__
    
    Dynamic modules are created with types.ModuleType() and don't exist
    in the filesystem. We need to serialize their entire namespace.
    """
    
    type_name = "module"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a module."""
        return isinstance(obj, types.ModuleType)
    
    def extract_state(self, obj: types.ModuleType) -> Dict[str, Any]:
        """
        Extract module state.
        
        What we capture:
        - name: Module name
        - is_dynamic: Whether module can be imported or is dynamic
        - module_dict: Module's __dict__ (for dynamic modules)
        - doc: Module's __doc__ string
        - file: Module's __file__ attribute (if any)
        - package: Module's __package__ attribute
        """
        module_name = obj.__name__
        module_file = getattr(obj, '__file__', None)
        module_doc = getattr(obj, '__doc__', None)
        module_package = getattr(obj, '__package__', None)
        
        # determine if module is dynamic
        # try to import it to see if it exists in the standard path
        is_dynamic = False
        try:
            imported = importlib.import_module(module_name)
            # if it imported and is NOT the same object, it's a custom module
            if imported is not obj:
                is_dynamic = True
        except (ImportError, ModuleNotFoundError):
            # can't import it - it's definitely dynamic
            is_dynamic = True
        
        # for dynamic modules, serialize the entire __dict__
        module_dict = {}
        if is_dynamic:
            # get module's namespace
            for key, value in obj.__dict__.items():
                # skip special attributes
                if key.startswith('__') and key.endswith('__'):
                    # keep some special attributes
                    if key in ('__name__', '__doc__', '__package__', '__file__'):
                        module_dict[key] = value
                    continue
                
                # skip modules (to avoid deep recursion)
                if isinstance(value, types.ModuleType):
                    # store just the module name for reference
                    module_dict[key] = {"__module_ref__": value.__name__}
                    continue
                
                # include everything else (will be recursively serialized)
                module_dict[key] = value
        
        # for non-dynamic modules, only store the name 
        # (everything else can be recovered by importing on the other end)
        if not is_dynamic:
            return {
                "name": module_name,
                "is_dynamic": False,
            }
        
        # for dynamic modules, we need to store everything
        return {
            "name": module_name,
            "is_dynamic": True,
            "module_dict": module_dict,  # Will be recursively serialized
            "doc": module_doc,
            "file": module_file,
            "package": module_package,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> types.ModuleType:
        """
        Reconstruct module.
        
        For standard modules, just import them.
        For dynamic modules, recreate with types.ModuleType and populate __dict__.
        """
        module_name = state["name"]
        is_dynamic = state["is_dynamic"]
        
        if not is_dynamic:
            # try to import standard module
            try:
                return importlib.import_module(module_name)
            except (ImportError, ModuleNotFoundError) as e:
                raise ModuleSerializationError(
                    f"Cannot import module '{module_name}' in target process. "
                    f"Ensure the module is installed: {e}"
                ) from e
        
        # create dynamic module
        module = types.ModuleType(module_name, state["doc"])
        
        # set special attributes
        if state["file"]:
            module.__file__ = state["file"]
        if state["package"]:
            module.__package__ = state["package"]
        
        # populate module's __dict__
        for key, value in state["module_dict"].items():
            # handle module references
            if isinstance(value, dict) and "__module_ref__" in value:
                # try to import the referenced module
                try:
                    value = importlib.import_module(value["__module_ref__"])
                except (ImportError, ModuleNotFoundError):
                    # referenced module not available - skip this attribute
                    import warnings
                    warnings.warn(f"Cannot import referenced module {value['__module_ref__']} for dynamic module")
                    continue
                except Exception as e:
                    # unexpected import error
                    import warnings
                    warnings.warn(f"Unexpected error importing module {value['__module_ref__']}: {e}")
                    continue
            
            setattr(module, key, value)
        
        # add to sys.modules so it can be imported
        # this allows circular references within the module to work
        sys.modules[module_name] = module
        
        return module

