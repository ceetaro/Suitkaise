#!/usr/bin/env python3
"""
Detailed debug test to see exactly what's happening during deserialization.
"""

import sys
import threading
from pathlib import Path

# Add suitkaise to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_exact_failing_scenario():
    """Test the exact scenario that's failing in the main test."""
    print("🔍 Testing Exact Failing Scenario...")
    
    try:
        from suitkaise._int.serialization.cerial_core import (
            serialize, deserialize, enable_debug_mode, disable_debug_mode
        )
        
        enable_debug_mode()
        
        # Create the EXACT complex data from the failing test
        complex_data = {
            "config": {
                "threads": 4,
                "timeout": 30.0,
                "debug": True
            },
            "locks": {
                "main_lock": threading.Lock(),
                "data_lock": threading.RLock(),
                "semaphore": threading.Semaphore(2)
            },
            "data": [
                {"id": 1, "value": "test1"},
                {"id": 2, "value": "test2"},
                {"id": 3, "value": "test3"}
            ],
            "metadata": {
                "created": "2024-01-01",
                "version": "1.0.0"
            }
        }
        
        print(f"📦 Original complex_data:")
        print(f"  Type: {type(complex_data)}")
        print(f"  Keys: {list(complex_data.keys())}")
        print(f"  config type: {type(complex_data['config'])}")
        print(f"  locks type: {type(complex_data['locks'])}")
        print(f"  data type: {type(complex_data['data'])}")
        
        print(f"\n🚀 Serializing...")
        serialized = serialize(complex_data)
        print(f"  Serialized: {len(serialized)} bytes")
        
        print(f"\n📥 Deserializing...")
        deserialized = deserialize(serialized)
        
        print(f"\n📦 Deserialized result:")
        print(f"  Type: {type(deserialized)}")
        
        if isinstance(deserialized, dict):
            print(f"  Keys: {list(deserialized.keys())}")
            
            # Check each expected section
            expected_keys = ["config", "locks", "data", "metadata"]
            for key in expected_keys:
                if key in deserialized:
                    print(f"  ✅ {key}: {type(deserialized[key])}")
                    if key == "config":
                        print(f"      config contents: {deserialized[key]}")
                else:
                    print(f"  ❌ {key}: MISSING!")
        else:
            print(f"  ❌ Not a dict! Got: {deserialized}")
        
        disable_debug_mode()
        
        # Return whether it matches expected structure
        if isinstance(deserialized, dict):
            has_all_keys = all(key in deserialized for key in ["config", "locks", "data", "metadata"])
            return has_all_keys
        else:
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_case():
    """Test a simple case to verify basic functionality."""
    print("\n🔧 Testing Simple Case...")
    
    try:
        from suitkaise._int.serialization.cerial_core import (
            serialize, deserialize, enable_debug_mode, disable_debug_mode
        )
        
        enable_debug_mode()
        
        # Simple case
        simple_data = {"lock": threading.Lock()}
        
        print(f"📦 Original simple_data:")
        print(f"  Type: {type(simple_data)}")
        print(f"  Keys: {list(simple_data.keys())}")
        
        print(f"\n🚀 Serializing simple case...")
        serialized = serialize(simple_data)
        print(f"  Serialized: {len(serialized)} bytes")
        
        print(f"\n📥 Deserializing simple case...")
        deserialized = deserialize(serialized)
        
        print(f"\n📦 Simple deserialized result:")
        print(f"  Type: {type(deserialized)}")
        
        if isinstance(deserialized, dict):
            print(f"  Keys: {list(deserialized.keys())}")
            if "lock" in deserialized:
                print(f"  ✅ lock: {type(deserialized['lock'])}")
                simple_success = True
            else:
                print(f"  ❌ lock: MISSING!")
                simple_success = False
        else:
            print(f"  ❌ Not a dict! Got: {deserialized}")
            simple_success = False
        
        disable_debug_mode()
        return simple_success
        
    except Exception as e:
        print(f"❌ Simple test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🐛 Detailed Debug Test - Step by Step")
    print("=" * 45)
    
    simple_ok = test_simple_case()
    complex_ok = test_exact_failing_scenario()
    
    print("\n" + "=" * 45)
    print(f"Simple case: {'✅ PASS' if simple_ok else '❌ FAIL'}")
    print(f"Complex case: {'✅ PASS' if complex_ok else '❌ FAIL'}")
    
    if simple_ok and complex_ok:
        print("🎉 Both tests passed! The structure issue should be fixed.")
    else:
        print("❌ Issues remain. Check the debug output above.")
    
    sys.exit(0 if (simple_ok and complex_ok) else 1)