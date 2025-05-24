#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import io
from suitkaise.cereal import Cereal
from suitkaise.skglobals import SKGlobal, SKGlobalValueError

print("=== DEBUG: Testing Non-Serializable Object ===")

# Test the same object from the failing test
class NonSerializable:
    def __init__(self):
        self.func = lambda x: x  # Lambda functions are not serializable
        self.file_handle = open(__file__, 'r')  # File handles are not serializable
    
    def __del__(self):
        if hasattr(self, 'file_handle') and not self.file_handle.closed:
            self.file_handle.close()

non_serializable_obj = NonSerializable()

print(f"DEBUG: Testing serialization of {type(non_serializable_obj)}")

# Test our cereal directly
cereal = Cereal()

try:
    is_serializable = cereal.serializable(non_serializable_obj, mode='internal')
    print(f"DEBUG: cereal.serializable() returned: {is_serializable}")
    
    if is_serializable:
        # Try actual serialization
        try:
            serialized = cereal.serialize(non_serializable_obj, mode='internal')
            print(f"DEBUG: Serialization succeeded: {len(serialized)} bytes")
        except Exception as e:
            print(f"DEBUG: Actual serialization failed: {e}")
    else:
        print("DEBUG: cereal.serializable() returned False")
except Exception as e:
    print(f"DEBUG: cereal.serializable() failed with: {e}")

print("\n=== Now testing SKGlobal ===")

# Now test SKGlobal
try:
    global_var = SKGlobal(
        name="test_non_serializable",
        value=non_serializable_obj,
        auto_sync=True,
        auto_create=True
    )
    print("DEBUG: SKGlobal creation succeeded - this is the problem!")
    print(f"DEBUG: Global value: {global_var.get()}")
except SKGlobalValueError as e:
    print(f"DEBUG: SKGlobal correctly raised SKGlobalValueError: {e}")
except Exception as e:
    print(f"DEBUG: SKGlobal raised unexpected error: {type(e).__name__}: {e}")