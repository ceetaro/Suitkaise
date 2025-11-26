#!/usr/bin/env python3
"""
Complete serialization/deserialization verification test.

This script demonstrates the full cycle:
1. Create WorstPossibleObject
2. Serialize with cerial
3. Deserialize with cerial
4. Verify 100% reconstruction
5. Show detailed report of what passed/failed
"""

from worst_possible_obj import WorstPossibleObject
import sys
from pathlib import Path

# Add parent directories to path to import cerial
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import cerial
    CERIAL_AVAILABLE = True
except ImportError:
    CERIAL_AVAILABLE = False
    print("⚠️  cerial not yet implemented - will simulate for demo")


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_section(title):
    """Print a formatted section."""
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")


def format_verification_results(passed, failures, verbose=True):
    """Format verification results in a clear, colored way."""
    print_section("VERIFICATION RESULTS")
    
    if passed:
        print("\n✅  PERFECT RECONSTRUCTION!")
        print("   All verification checks passed.")
        print(f"   Total checks: {len(failures) if isinstance(failures, list) else 0}")
        return True
    else:
        print(f"\n❌  VERIFICATION FAILED")
        print(f"   {len(failures)} checks failed\n")
        
        # Group failures by category
        categories = {
            'primitives': [],
            'collections': [],
            'locks': [],
            'queues': [],
            'events': [],
            'files': [],
            'loggers': [],
            'functions': [],
            'regex': [],
            'sqlite': [],
            'circular': [],
            'other': []
        }
        
        for failure in failures:
            categorized = False
            for category in categories.keys():
                if category in failure.lower():
                    categories[category].append(failure)
                    categorized = True
                    break
            if not categorized:
                categories['other'].append(failure)
        
        # Print failures by category
        for category, items in categories.items():
            if items:
                print(f"\n  [{category.upper()}] - {len(items)} failures:")
                if verbose or len(items) <= 5:
                    for item in items:
                        print(f"    • {item}")
                else:
                    for item in items[:5]:
                        print(f"    • {item}")
                    print(f"    ... and {len(items) - 5} more")
        
        return False


def test_full_cycle_verbose():
    """Test the full serialization/deserialization cycle with detailed output."""
    print_header("COMPLETE SERIALIZATION/DESERIALIZATION TEST")
    
    # Step 1: Create original object
    print_section("STEP 1: Creating Original Object")
    print("Creating WorstPossibleObject with verbose logging...")
    
    original = WorstPossibleObject(
        verbose=True,
        debug_log_file='original_creation.log'
    )
    
    print(f"\n✓ Original object created")
    print(f"  - Verification checksums: {len(original._verification_checksums)}")
    print(f"  - Debug log: original_creation.log")
    
    # Step 2: Serialize
    print_section("STEP 2: Serializing Object")
    
    if not CERIAL_AVAILABLE:
        print("❌ cerial not available - cannot test serialization")
        print("   Implement cerial.serialize() first!")
        original.cleanup()
        return False
    
    try:
        print("Calling cerial.serialize(original)...")
        serialized_bytes = cerial.serialize(original)
        
        print(f"\n✓ Serialization succeeded!")
        print(f"  - Serialized size: {len(serialized_bytes):,} bytes")
        print(f"  - Size: {len(serialized_bytes) / 1024:.2f} KB")
        
    except Exception as e:
        print(f"\n❌ Serialization FAILED!")
        print(f"   Error: {e}")
        print(f"\n   Debug steps:")
        print(f"   1. Check the error message above")
        print(f"   2. Run: obj.generate_debug_report(test_serialization=True)")
        print(f"   3. Use skip_types to isolate the problem")
        print(f"   4. Fix the handler for the failing type")
        
        import traceback
        traceback.print_exc()
        original.cleanup()
        return False
    
    # Step 3: Deserialize
    print_section("STEP 3: Deserializing Object")
    
    try:
        print("Calling cerial.deserialize(serialized_bytes)...")
        restored = cerial.deserialize(serialized_bytes)
        
        print(f"\n✓ Deserialization succeeded!")
        print(f"  - Object type: {type(restored).__name__}")
        print(f"  - Has verification data: {hasattr(restored, '_verification_checksums')}")
        
    except Exception as e:
        print(f"\n❌ Deserialization FAILED!")
        print(f"   Error: {e}")
        print(f"\n   Debug steps:")
        print(f"   1. Check the error message above")
        print(f"   2. The serialized data may be corrupted")
        print(f"   3. Check that handlers match between serialize/deserialize")
        
        import traceback
        traceback.print_exc()
        original.cleanup()
        return False
    
    # Step 4: Verify
    print_section("STEP 4: Verifying Reconstruction")
    print("Running original.verify(restored)...")
    print("This checks 80+ attributes including:")
    print("  • All primitive values")
    print("  • Complex object states (locks, queues, events)")
    print("  • File positions and contents")
    print("  • Function callability and correctness")
    print("  • Circular reference identity")
    print("  • SQLite data integrity")
    print("  • And more...")
    
    try:
        passed, failures = original.verify(restored)
        
        success = format_verification_results(passed, failures, verbose=True)
        
        if success:
            print("\n" + "🎉 "*10)
            print("\n   CERIAL WORKS PERFECTLY!")
            print("   Can serialize the worst possible object!\n")
            print("🎉 "*10)
        
    except Exception as e:
        print(f"\n❌ Verification FAILED with exception!")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    # Step 5: Cleanup
    print_section("STEP 5: Cleanup")
    original.cleanup()
    restored.cleanup()
    print("✓ Resources cleaned up")
    
    return success


def test_full_cycle_quiet():
    """Test the full cycle with minimal output (just results)."""
    print_header("QUICK TEST (Minimal Output)")
    
    print("Creating object...")
    original = WorstPossibleObject()
    
    if not CERIAL_AVAILABLE:
        print("❌ cerial not available")
        original.cleanup()
        return False
    
    try:
        print("Serializing...")
        serialized = cerial.serialize(original)
        print(f"  ✓ {len(serialized):,} bytes")
        
        print("Deserializing...")
        restored = cerial.deserialize(serialized)
        print("  ✓ Done")
        
        print("Verifying...")
        passed, failures = original.verify(restored)
        
        if passed:
            print("\n✅ PERFECT! All checks passed.\n")
            success = True
        else:
            print(f"\n❌ FAILED: {len(failures)} checks failed")
            print("\nFirst 5 failures:")
            for failure in failures[:5]:
                print(f"  • {failure}")
            success = False
        
        original.cleanup()
        restored.cleanup()
        return success
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        original.cleanup()
        return False


def test_with_selective_types():
    """Test serialization with only specific type categories."""
    print_header("SELECTIVE TYPE TESTING")
    
    print("Testing serialization of different type categories individually...")
    print("(Useful for debugging which types work vs fail)\n")
    
    # Define test categories
    test_cases = [
        ("Primitives Only", {'functions', 'locks', 'queues', 'events', 'files', 
                             'regex', 'sqlite', 'generators', 'weakrefs', 'mmap',
                             'contextvars', 'iterators', 'edge_cases', 'circular'}),
        ("Functions Only", {'locks', 'queues', 'events', 'files', 'regex', 'sqlite',
                           'generators', 'weakrefs', 'mmap', 'contextvars', 'iterators',
                           'edge_cases', 'circular'}),
        ("Locks Only", {'functions', 'queues', 'events', 'files', 'regex', 'sqlite',
                       'generators', 'weakrefs', 'mmap', 'contextvars', 'iterators',
                       'edge_cases', 'circular'}),
        ("Queues Only", {'functions', 'locks', 'events', 'files', 'regex', 'sqlite',
                        'generators', 'weakrefs', 'mmap', 'contextvars', 'iterators',
                        'edge_cases', 'circular'}),
    ]
    
    if not CERIAL_AVAILABLE:
        print("❌ cerial not available - cannot test")
        return False
    
    results = {}
    
    for name, skip_types in test_cases:
        print(f"\n{'─'*70}")
        print(f"Testing: {name}")
        
        try:
            obj = WorstPossibleObject(skip_types=skip_types)
            serialized = cerial.serialize(obj)
            restored = cerial.deserialize(serialized)
            passed, failures = obj.verify(restored)
            
            if passed:
                print(f"  ✅ PASSED ({len(serialized):,} bytes)")
                results[name] = "PASSED"
            else:
                print(f"  ❌ FAILED ({len(failures)} verification errors)")
                results[name] = f"FAILED ({len(failures)} errors)"
            
            obj.cleanup()
            restored.cleanup()
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)[:60]}...")
            results[name] = "ERROR"
    
    # Summary
    print_section("SUMMARY")
    for name, result in results.items():
        status = "✅" if result == "PASSED" else "❌"
        print(f"  {status} {name}: {result}")
    
    all_passed = all(r == "PASSED" for r in results.values())
    return all_passed


def main():
    """Run the tests based on command line arguments."""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "verbose"
    
    if mode == "quiet":
        success = test_full_cycle_quiet()
    elif mode == "selective":
        success = test_with_selective_types()
    else:  # verbose
        success = test_full_cycle_verbose()
    
    print("\n" + "="*70)
    if success:
        print("  ✅ TEST SUITE PASSED")
    else:
        print("  ❌ TEST SUITE FAILED")
    print("="*70 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Show usage if --help
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
Usage: python test_full_cycle.py [mode]

Modes:
  verbose   - Full detailed output (default)
  quiet     - Minimal output, just results
  selective - Test individual type categories

Examples:
  python test_full_cycle.py           # Verbose mode
  python test_full_cycle.py quiet     # Quick test
  python test_full_cycle.py selective # Test by category
        """)
        sys.exit(0)
    
    main()

