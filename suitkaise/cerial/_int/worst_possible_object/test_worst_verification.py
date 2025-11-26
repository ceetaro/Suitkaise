#!/usr/bin/env python3
"""
Test script to demonstrate WorstPossibleObject verification system.

This shows how to:
1. Create the object
2. Verify it against itself (should pass)
3. Verify it against a different instance with same seed (should pass)
4. Show what verification failures look like
"""

from worst_possible_obj import WorstPossibleObject
import random


def test_self_verification():
    """Test that an object verifies against itself."""
    print("="*70)
    print("TEST 1: Self-Verification")
    print("="*70)
    print("\nCreating WorstPossibleObject...")
    
    obj = WorstPossibleObject()
    
    print(f"✓ Object created")
    print(f"  - Verification checksums: {len(obj._verification_checksums)} fields")
    print(f"  - Lock acquired: {obj.lock_acquired.locked()}")
    print(f"  - Queue size: {obj.queue.qsize()}")
    print(f"  - Circular ref works: {obj.circular_dict['self'] is obj.circular_dict}")
    
    print("\nVerifying object against itself...")
    passed, failures = obj.verify(obj)
    
    if passed:
        print("✓ PASSED: Object verifies against itself!")
    else:
        print(f"✗ FAILED: {len(failures)} failures (this shouldn't happen!)")
        for failure in failures[:5]:
            print(f"  - {failure}")
    
    obj.cleanup()
    print()
    return passed


def test_same_seed_verification():
    """Test that two objects with same random seed verify against each other."""
    print("="*70)
    print("TEST 2: Same Seed Verification")
    print("="*70)
    print("\nCreating two objects with same random seed...")
    
    # Set seed before creating each object
    random.seed(42)
    obj1 = WorstPossibleObject()
    
    random.seed(42)
    obj2 = WorstPossibleObject()
    
    print("✓ Both objects created")
    print(f"  - obj1 queue size: {obj1.queue.qsize()}")
    print(f"  - obj2 queue size: {obj2.queue.qsize()}")
    
    print("\nVerifying obj1 against obj2...")
    passed, failures = obj1.verify(obj2)
    
    if passed:
        print("✓ PASSED: Objects with same seed verify!")
    else:
        print(f"⚠ Some differences (expected due to IDs, file paths, etc.):")
        print(f"  {len(failures)} differences found")
        for failure in failures[:10]:
            print(f"  - {failure}")
    
    obj1.cleanup()
    obj2.cleanup()
    print()
    return passed


def test_modification_detection():
    """Test that verification detects modifications."""
    print("="*70)
    print("TEST 3: Modification Detection")
    print("="*70)
    print("\nCreating object and modifying it...")
    
    obj1 = WorstPossibleObject()
    obj2 = WorstPossibleObject()
    
    # Make some modifications to obj2
    obj2.int_value = 999  # Changed from 42
    obj2.str_value = "MODIFIED"  # Changed
    obj2.queue.put("extra_item")  # Queue size now different
    
    print("✓ Objects created and obj2 modified")
    print(f"  - obj1.int_value: {obj1.int_value}")
    print(f"  - obj2.int_value: {obj2.int_value}")
    print(f"  - obj1.str_value: {obj1.str_value}")
    print(f"  - obj2.str_value: {obj2.str_value}")
    print(f"  - obj1.queue.qsize(): {obj1.queue.qsize()}")
    print(f"  - obj2.queue.qsize(): {obj2.queue.qsize()}")
    
    print("\nVerifying obj1 against modified obj2...")
    passed, failures = obj1.verify(obj2)
    
    if not passed:
        print(f"✓ CORRECTLY DETECTED: {len(failures)} differences found")
        print("\nFirst 10 differences:")
        for failure in failures[:10]:
            print(f"  - {failure}")
    else:
        print("✗ FAILED: Should have detected modifications!")
    
    obj1.cleanup()
    obj2.cleanup()
    print()
    return not passed  # Test passes if verification correctly failed


def test_circular_reference_verification():
    """Test that circular reference identity is verified."""
    print("="*70)
    print("TEST 4: Circular Reference Verification")
    print("="*70)
    print("\nTesting circular reference identity preservation...")
    
    obj = WorstPossibleObject()
    
    # Check various circular references
    checks = [
        ("circular_dict['self']", 
         obj.circular_dict['self'] is obj.circular_dict),
        ("circular_dict['also_self']", 
         obj.circular_dict['also_self'] is obj.circular_dict),
        ("circular_list[3]", 
         obj.circular_list[3] is obj.circular_list),
        ("ref_a points to ref_b", 
         obj.ref_a['points_to_b'] is obj.ref_b),
        ("ref_b points to ref_a", 
         obj.ref_b['points_to_a'] is obj.ref_a),
        ("circular_nested[1][2]", 
         obj.circular_nested[1][2] is obj.circular_nested),
        ("circular_nested cross-ref", 
         obj.circular_nested[2]['b'] is obj.circular_nested[0]),
    ]
    
    all_passed = True
    for name, check in checks:
        status = "✓" if check else "✗"
        print(f"  {status} {name}: {check}")
        if not check:
            all_passed = False
    
    if all_passed:
        print("\n✓ PASSED: All circular references maintain identity!")
    else:
        print("\n✗ FAILED: Some circular references broken!")
    
    obj.cleanup()
    print()
    return all_passed


def test_functional_verification():
    """Test that functions actually work after creation."""
    print("="*70)
    print("TEST 5: Functional Verification")
    print("="*70)
    print("\nTesting that complex objects actually function...")
    
    obj = WorstPossibleObject()
    
    tests = []
    
    # Test function
    try:
        result = obj.function(5, 10)
        tests.append(("function(5, 10)", result == 15, f"expected 15, got {result}"))
    except Exception as e:
        tests.append(("function(5, 10)", False, str(e)))
    
    # Test lambda
    try:
        result = obj.lambda_function(10)
        tests.append(("lambda_function(10)", result == 20, f"expected 20, got {result}"))
    except Exception as e:
        tests.append(("lambda_function(10)", False, str(e)))
    
    # Test partial
    try:
        result = obj.partial_function(y=5)
        tests.append(("partial_function(y=5)", result == 15, f"expected 15, got {result}"))
    except Exception as e:
        tests.append(("partial_function(y=5)", False, str(e)))
    
    # Test regex
    try:
        match = obj.regex_pattern.search("version 3.14 found")
        tests.append(("regex.search()", match is not None, "should match"))
    except Exception as e:
        tests.append(("regex.search()", False, str(e)))
    
    # Test queue
    try:
        size = obj.queue.qsize()
        tests.append(("queue.qsize()", size == 3, f"expected 3, got {size}"))
    except Exception as e:
        tests.append(("queue.qsize()", False, str(e)))
    
    # Test logger
    try:
        obj.logger.info("test message")
        tests.append(("logger.info()", True, "callable"))
    except Exception as e:
        tests.append(("logger.info()", False, str(e)))
    
    # Print results
    all_passed = True
    for name, passed, detail in tests:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}: {detail}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✓ PASSED: All functions work correctly!")
    else:
        print("\n✗ FAILED: Some functions don't work!")
    
    obj.cleanup()
    print()
    return all_passed


def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("WORST POSSIBLE OBJECT - VERIFICATION TEST SUITE")
    print("="*70)
    print()
    
    results = {
        "Self Verification": test_self_verification(),
        "Same Seed Verification": test_same_seed_verification(),
        "Modification Detection": test_modification_detection(),
        "Circular Reference Verification": test_circular_reference_verification(),
        "Functional Verification": test_functional_verification(),
    }
    
    print("="*70)
    print("SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print()
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("\nThe WorstPossibleObject is ready to test cerial serialization.")
        print("Next step: Use cerial.serialize() and cerial.deserialize() on this object")
        print("and verify the deserialized object passes all these same checks.")
    else:
        print("✗ SOME TESTS FAILED!")
        print("The verification system may need adjustment.")
    print("="*70)


if __name__ == "__main__":
    main()

