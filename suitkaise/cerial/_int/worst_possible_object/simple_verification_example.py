#!/usr/bin/env python3
"""
Simplest possible verification example.

Shows the absolute minimal code to:
1. Create object
2. Serialize
3. Deserialize  
4. Verify
5. See results
"""

from worst_possible_obj import WorstPossibleObject

def simple_example():
    """The absolute simplest verification example."""
    
    print("="*70)
    print("SIMPLE VERIFICATION EXAMPLE")
    print("="*70)
    
    # Step 1: Create original
    print("\n1. Creating original object...")
    original = WorstPossibleObject()
    print(f"   ✓ Created with {len(original._verification_checksums)} checksums")
    
    # Step 2: Serialize (when cerial is ready)
    print("\n2. Serializing...")
    try:
        import cerial
        serialized = cerial.serialize(original)
        print(f"   ✓ Serialized to {len(serialized):,} bytes")
    except ImportError:
        print("   ⚠ cerial not yet implemented")
        print("   → For now, we'll test verification on the same object")
        serialized = None
    except Exception as e:
        print(f"   ✗ Serialization failed: {e}")
        original.cleanup()
        return
    
    # Step 3: Deserialize (when cerial is ready)
    print("\n3. Deserializing...")
    if serialized:
        try:
            restored = cerial.deserialize(serialized)
            print(f"   ✓ Deserialized successfully")
        except Exception as e:
            print(f"   ✗ Deserialization failed: {e}")
            original.cleanup()
            return
    else:
        # For demo purposes, verify against itself
        restored = original
        print("   → Using original object for demo")
    
    # Step 4: VERIFY!
    print("\n4. Verifying reconstruction...")
    print("   Running original.verify(restored)...")
    
    passed, failures = original.verify(restored)
    
    # Step 5: Show results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    if passed:
        print("\n✅✅✅  PERFECT!  ✅✅✅")
        print("\n   Every single attribute matches!")
        print(f"   All {len(original._verification_checksums)} checks passed.")
        print("\n   This means:")
        print("     • All primitive values match")
        print("     • All complex object states preserved")
        print("     • All functions work correctly")
        print("     • All circular references intact")
        print("     • All file positions correct")
        print("     • All SQLite data matches")
        print("     • Everything is PERFECT!")
        
    else:
        print(f"\n❌  FAILED: {len(failures)} checks failed\n")
        
        # Show first 10 failures
        print("First 10 failures:")
        for i, failure in enumerate(failures[:10], 1):
            print(f"  {i}. {failure}")
        
        if len(failures) > 10:
            print(f"\n  ... and {len(failures) - 10} more failures")
        
        print("\nWhat to do:")
        print("  1. Look at the failure messages above")
        print("  2. See which category has most failures")
        print("  3. Use skip_types to isolate that category")
        print("  4. Use inspect_object() to examine failing objects")
        print("  5. Fix the handler for that object type")
        print("  6. Test again!")
    
    print("\n" + "="*70 + "\n")
    
    # Cleanup
    original.cleanup()
    if restored is not original:
        restored.cleanup()
    
    return passed


if __name__ == "__main__":
    simple_example()
    
    print("\nNext steps:")
    print("  • Implement cerial.serialize() and cerial.deserialize()")
    print("  • Run this script again")
    print("  • If verification fails, use the debugging tools:")
    print("      - test_debugging_features.py")
    print("      - test_full_cycle.py")
    print("      - See DEBUGGING_GUIDE.md")
    print()

