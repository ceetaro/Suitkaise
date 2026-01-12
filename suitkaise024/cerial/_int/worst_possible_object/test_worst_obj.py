"""
Test script for WorstPossibleObject

This demonstrates creating the object, verifying it works,
and shows what cerial will need to serialize/deserialize.
"""

from worst_possible_obj import WorstPossibleObject


def test_worst_possible_object_creation():
    """Test that we can create the object and it initializes correctly."""
    print("Creating WorstPossibleObject...")
    obj = WorstPossibleObject(depth=0, max_depth=3)
    
    print(f"✓ Created outer class (depth={obj.depth})")
    print(f"✓ Has {len(obj._verification_data)} verification fields")
    
    # Check nested classes exist
    assert hasattr(obj, 'nested_class_instance')
    print(f"✓ Nested1 exists (depth={obj.nested_class_instance.depth})")
    
    assert hasattr(obj.nested_class_instance, 'nested_class_instance')
    print(f"✓ Nested2 exists (depth={obj.nested_class_instance.nested_class_instance.depth})")
    
    assert hasattr(obj.nested_class_instance.nested_class_instance, 'nested_class_instance')
    print(f"✓ Nested3 exists (depth={obj.nested_class_instance.nested_class_instance.nested_class_instance.depth})")
    
    # Check some complex objects
    print("\nComplex objects present:")
    print(f"  - Lock (locked={obj.lock.locked()})")
    print(f"  - Event (set={obj.event.is_set()})")
    print(f"  - Logger (name={obj.logger.name}, level={obj.logger.level})")
    print(f"  - Queue (size={obj.queue.qsize()})")
    print(f"  - Regex pattern={obj.regex_pattern.pattern}")
    print(f"  - Temp file={obj.temp_file.name}")
    print(f"  - SQLite connection active")
    
    # Check circular reference
    assert obj.circular_dict["self"] is obj.circular_dict
    print(f"✓ Circular reference works correctly")
    
    # Check random collections
    print(f"\nRandom collections:")
    print(f"  - Nested list depth: {_get_depth(obj.random_nested_list)}")
    print(f"  - Nested dict keys: {list(obj.random_nested_dict.keys())}")
    
    print("\n✓ All basic checks passed!")
    
    # Cleanup
    obj.cleanup()
    print("✓ Cleanup completed")
    
    return obj


def _get_depth(obj, current=0):
    """Helper to calculate nesting depth of collections."""
    if isinstance(obj, (list, tuple)):
        if not obj:
            return current
        depths = [_get_depth(item, current + 1) for item in obj]
        return max(depths) if depths else current
    elif isinstance(obj, dict):
        if not obj:
            return current
        depths = [_get_depth(v, current + 1) for v in obj.values()]
        return max(depths) if depths else current
    else:
        return current


def test_verification():
    """Test that verification works on identical objects."""
    print("\n" + "="*60)
    print("Testing verification between two identical objects...")
    print("="*60 + "\n")
    
    obj1 = WorstPossibleObject(depth=0, max_depth=2)  # Smaller for faster test
    obj2 = WorstPossibleObject(depth=0, max_depth=2)  # Same seed = same random data
    
    passed, failures = obj1.verify(obj2)
    
    if passed:
        print("✓ Verification PASSED! Both objects match.")
    else:
        print(f"✗ Verification FAILED with {len(failures)} mismatches:")
        for failure in failures[:10]:  # Show first 10
            print(f"  - {failure}")
    
    obj1.cleanup()
    obj2.cleanup()
    
    return passed


def test_different_depths():
    """Test objects at different depths have different data."""
    print("\n" + "="*60)
    print("Testing that objects at different depths differ...")
    print("="*60 + "\n")
    
    obj_depth0 = WorstPossibleObject(depth=0, max_depth=1)
    obj_depth1 = WorstPossibleObject(depth=1, max_depth=2)
    
    # They should have different logger names (based on depth)
    print(f"Depth 0 logger: {obj_depth0.logger.name}")
    print(f"Depth 1 logger: {obj_depth1.logger.name}")
    
    assert obj_depth0.logger.name != obj_depth1.logger.name
    print("✓ Objects at different depths have different data")
    
    obj_depth0.cleanup()
    obj_depth1.cleanup()


if __name__ == "__main__":
    print("="*60)
    print("WORST POSSIBLE OBJECT TEST SUITE")
    print("="*60 + "\n")
    
    test_worst_possible_object_creation()
    test_verification()
    test_different_depths()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED!")
    print("="*60)
    print("\nNext step: Use cerial to serialize/deserialize this object")
    print("and verify it still passes all checks.")

