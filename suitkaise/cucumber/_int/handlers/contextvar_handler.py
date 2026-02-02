"""
Handler for contextvars - context variables and tokens.

Context variables are used for context-local state (like thread-local but for async).
Tokens represent a specific value set operation.
"""

import contextvars
from typing import Any, Dict
from .base_class import Handler


class ContextVarHandler(Handler):
    """
    Handle contextvars.ContextVar objects.
    
    ContextVar is a context-local variable container. We serialize:
    - The name of the variable
    - The default value (if set)
    - The current value in the current context (if set)
    
    Note: Context-local values are inherently tied to execution context,
    so we can only capture the current value. Other contexts' values are lost.
    """
    
    type_name = "contextvar"
    
    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, contextvars.ContextVar)
    
    def extract_state(self, obj: contextvars.ContextVar) -> Dict[str, Any]:
        """
        Extract ContextVar state.
        
        What we capture:
        - name: The variable name
        - has_default: Whether a default was specified
        - default_value: The default value (if has_default)
        - has_current: Whether a value is set in current context
        - current_value: The current value (if has_current)
        """
        state = {
            "name": obj.name,
        }
        
        # try to get default value

        # ContextVar doesn't expose this directly, so we need to check
        # by trying to get the value in a fresh context
        try:
            # get current value first
            current_value = obj.get()
            state["has_current"] = True
            state["current_value"] = current_value
        except LookupError:
            # no value set in current context
            state["has_current"] = False
        
        # check if there's a default by inspecting the ContextVar
        # this is tricky - we can use a sentinel to detect if default exists
        sentinel = object()
        default_or_sentinel = obj.get(sentinel)
        
        if default_or_sentinel is not sentinel:
            # has a default
            state["has_default"] = True
            state["default_value"] = default_or_sentinel
        else:
            state["has_default"] = False
        
        return state
    
    def reconstruct(self, state: Dict[str, Any]) -> contextvars.ContextVar:
        """
        Reconstruct ContextVar.
        
        Creates a new ContextVar with the same name and default.
        If there was a current value, sets it in the current context.
        """
        # create ContextVar with or without default
        if state["has_default"]:
            var = contextvars.ContextVar(state["name"], default=state["default_value"])
        else:
            var = contextvars.ContextVar(state["name"])
        
        # set current value if there was one
        if state["has_current"]:
            var.set(state["current_value"])
        
        return var


class TokenHandler(Handler):
    """
    Handle contextvars.Token objects.
    
    Tokens are returned when setting a ContextVar value and can be used to reset
    to the previous value. Since tokens are tied to specific ContextVar instances
    and execution contexts, they can't be meaningfully serialized.
    
    We serialize the token's metadata (var name, value) but reconstruction creates
    a "dead" token that can't be used for reset operations.

    If you want to serialize and reconstruct tokens, have to put the ContextVar through
    and get token over there, but this will be a new (but funcionally equivalent) ContextVar.
    """
    
    type_name = "contextvar_token"
    
    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, contextvars.Token)
    
    def extract_state(self, obj: contextvars.Token) -> Dict[str, Any]:
        """
        Extract Token state.
        
        What we capture:
        - var_name: Name of the associated ContextVar
        - Missing: The old value (Token.old_value) - private attribute
        - Missing: The var itself (Token.var) - private attribute
        
        Tokens have private attributes that aren't meant to be accessed,
        so we only capture what we can safely access.

        Once again, this is the best that Python lets us do.
        """
        # Token objects don't expose much publicly
        # we can try to access private attributes but this is fragile
        try:
            var = obj.var
            var_name = var.name if hasattr(var, 'name') else None
        except AttributeError:
            var_name = None
        
        try:
            old_value = obj.old_value
            # check if it's the MISSING sentinel (can't be pickled)
            if old_value is contextvars.Token.MISSING:
                has_old_value = False
                old_value_serializable = None
            else:
                has_old_value = True
                old_value_serializable = old_value
        except AttributeError:
            has_old_value = False
            old_value_serializable = None
        
        return {
            "var_name": var_name,
            "has_old_value": has_old_value,
            "old_value": old_value_serializable,
            "note": "Tokens cannot be meaningfully deserialized - this is metadata only",
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cannot truly reconstruct tokens.
        
        Tokens are inherently tied to specific execution contexts and ContextVar
        instances. They can't be reconstructed in a meaningful way.
        
        We return a dict with metadata about the original token instead.
        """
        # return metadata dict instead of trying to create a fake token
        return {
            "__cucumber_dead_token__": True,
            "var_name": state.get("var_name"),
            "note": state.get("note"),
        }

