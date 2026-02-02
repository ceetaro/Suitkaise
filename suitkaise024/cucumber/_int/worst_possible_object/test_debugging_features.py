#!/usr/bin/env python3
"""
Test script demonstrating the debugging features of WorstPossibleObject.

Shows how to:
1. Create objects with verbose logging
2. Skip certain type categories for isolated testing
3. Generate initialization reports
4. Inspect specific attributes
5. Test pickle compatibility by type
6. Generate comprehensive debug reports
"""

from worst_possible_obj import WorstPossibleObject
import sys


def demo_verbose_mode():
    """Demonstrate verbose initialization logging."""
    print("=" * 70)
    print("DEMO 1: Verbose Mode")
    print("=" * 70)
    print("\nCreating object with verbose=True...")
    print("(This shows detailed initialization progress)\n")
    
    obj = WorstPossibleObject(verbose=True)
    
    print("\n✓ Object created with full logging")
    obj.cleanup()
    print()


def demo_skip_types():
    """Demonstrate selective type skipping for isolated testing."""
    print("=" * 70)
    print("DEMO 2: Skipping Type Categories")
    print("=" * 70)
    print("\nCreating object that SKIPS: functions, locks, queues")
    print("(Useful for testing one type category at a time)\n")
    
    obj = WorstPossibleObject(
        verbose=True,
        skip_types={'functions', 'locks', 'queues', 'circular'}
    )
    
    print("\n✓ Object created with selected types skipped")
    obj.cleanup()
    print()


def demo_debug_log_file():
    """Demonstrate logging to a file."""
    print("=" * 70)
    print("DEMO 3: Debug Log File")
    print("=" * 70)
    print("\nCreating object with debug_log_file='worst_obj_debug.log'...")
    
    obj = WorstPossibleObject(
        verbose=False,  # Don't print, just log to file
        debug_log_file='worst_obj_debug.log'
    )
    
    print("✓ Object created")
    print("✓ Debug log written to: worst_obj_debug.log")
    print("\nFirst 20 lines of log:")
    print("-" * 70)
    
    with open('worst_obj_debug.log', 'r') as f:
        for i, line in enumerate(f):
            if i >= 20:
                break
            print(line.rstrip())
    
    obj.cleanup()
    print()


def demo_initialization_report():
    """Demonstrate initialization report generation."""
    print("=" * 70)
    print("DEMO 4: Initialization Report")
    print("=" * 70)
    print("\nGenerating initialization report...")
    
    obj = WorstPossibleObject()
    
    report = obj.get_initialization_report()
    print(report)
    
    obj.cleanup()
    print()


def demo_list_attributes():
    """Demonstrate listing attributes by type."""
    print("=" * 70)
    print("DEMO 5: List Attributes by Type")
    print("=" * 70)
    print("\nGrouping all attributes by their type...")
    
    obj = WorstPossibleObject()
    
    attrs = obj.list_all_attributes()
    
    for category, items in attrs.items():
        if items:
            print(f"\n[{category.upper()}] - {len(items)} items:")
            for item in items[:5]:  # Show first 5
                print(f"  - {item}")
            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more")
    
    obj.cleanup()
    print()


def demo_inspect_attribute():
    """Demonstrate detailed attribute inspection."""
    print("=" * 70)
    print("DEMO 6: Inspect Specific Attributes")
    print("=" * 70)
    
    obj = WorstPossibleObject()
    
    # Inspect a few different types of objects
    attrs_to_inspect = ['lock_acquired', 'queue', 'function', 'regex_pattern']
    
    for attr in attrs_to_inspect:
        info = obj.inspect_object(attr)
        print(info)
    
    obj.cleanup()
    print()


def demo_test_pickle_by_type():
    """Demonstrate testing pickle compatibility by type category."""
    print("=" * 70)
    print("DEMO 7: Test Pickle Compatibility by Type")
    print("=" * 70)
    print("\nTesting which objects in each category can be pickled...")
    
    obj = WorstPossibleObject()
    
    categories = ['primitives', 'collections', 'functions', 'locks', 'queues', 'files']
    
    for category in categories:
        print(f"\n[{category.upper()}]")
        results = obj.test_serialization_by_type(category)
        
        successes = sum(1 for success, _ in results.values() if success)
        failures = len(results) - successes
        
        print(f"  Total: {len(results)} | Passed: {successes} | Failed: {failures}")
        
        if failures > 0:
            print(f"  Failed items:")
            for name, (success, msg) in results.items():
                if not success:
                    print(f"    - {name}: {msg[:60]}...")
    
    obj.cleanup()
    print()


def demo_comprehensive_debug_report():
    """Demonstrate comprehensive debug report."""
    print("=" * 70)
    print("DEMO 8: Comprehensive Debug Report")
    print("=" * 70)
    print("\nGenerating full debug report with pickle tests...")
    
    obj = WorstPossibleObject()
    
    report = obj.generate_debug_report(test_serialization=True)
    print(report)
    
    obj.cleanup()
    print()


def demo_minimal_object():
    """Demonstrate creating minimal object for isolated testing."""
    print("=" * 70)
    print("DEMO 9: Minimal Object for Isolated Testing")
    print("=" * 70)
    print("\nCreating object with ONLY functions (everything else skipped)...")
    
    obj = WorstPossibleObject(
        verbose=True,
        skip_types={
            'primitives', 'locks', 'queues', 'events', 'files',
            'regex', 'sqlite', 'generators', 'weakrefs', 'mmap',
            'contextvars', 'iterators', 'edge_cases', 'circular'
        }
    )
    
    print("\n✓ Minimal object created")
    print("\nThis is useful for:")
    print("  - Testing one category at a time")
    print("  - Isolating serialization failures")
    print("  - Debugging specific handler implementations")
    
    obj.cleanup()
    print()


def main():
    """Run all demonstrations."""
    demos = [
        ("Verbose Mode", demo_verbose_mode),
        ("Skip Types", demo_skip_types),
        ("Debug Log File", demo_debug_log_file),
        ("Initialization Report", demo_initialization_report),
        ("List Attributes", demo_list_attributes),
        ("Inspect Attributes", demo_inspect_attribute),
        ("Test Pickle by Type", demo_test_pickle_by_type),
        ("Debug Report", demo_comprehensive_debug_report),
        ("Minimal Object", demo_minimal_object),
    ]
    
    print("\n" + "=" * 70)
    print("WORST POSSIBLE OBJECT - DEBUGGING FEATURES DEMONSTRATION")
    print("=" * 70)
    print(f"\nRunning {len(demos)} demonstrations...\n")
    
    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n{'#'*70}")
        print(f"# {i}/{len(demos)}: {name}")
        print(f"{'#'*70}\n")
        
        try:
            demo_func()
        except Exception as e:
            print(f"\n✗ Error in demo: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("ALL DEMONSTRATIONS COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  1. Use verbose=True to see initialization progress")
    print("  2. Use skip_types={...} to test categories individually")
    print("  3. Use debug_log_file='file.log' to save detailed logs")
    print("  4. Use inspect_object(attr) to examine specific objects")
    print("  5. Use test_serialization_by_type(category) to find pickle failures")
    print("  6. Use generate_debug_report() for comprehensive analysis")
    print("\nWhen testing cucumber:")
    print("  - Start with verbose mode to see what's being serialized")
    print("  - If serialization fails, use skip_types to isolate the problem")
    print("  - Use inspect_object() to understand the failing object")
    print("  - Use test_serialization_by_type() to see if base pickle works")
    print()


if __name__ == "__main__":
    main()

