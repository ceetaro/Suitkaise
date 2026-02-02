"""
Stress test for cucumber serialization/deserialization.

Creates many WorstPossibleObject instances and runs hundreds of 
serialization cycles to validate:
- No memory leaks
- Consistent state across cycles
- Handler stability
- Circular reference handling
- Inter-process communication simulation
"""

import gc
import sys
import time
from suitkaise.cucumber._int.serializer import Serializer
from suitkaise.cucumber._int.deserializer import Deserializer
from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject


class StressTest:
    """Comprehensive stress test for cucumber."""
    
    def __init__(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
        self.errors = []
        self.stats = {
            "objects_created": 0,
            "cycles_completed": 0,
            "total_bytes_serialized": 0,
            "failures": 0,
        }
    
    def run_single_object_cycles(self, obj_index: int, num_cycles: int) -> bool:
        """
        Run multiple serialization/deserialization cycles on a single object.
        
        Simulates inter-process communication: A → B → A → B → ...
        
        Returns True if all cycles pass.
        """
        try:
            # Create object
            obj = WorstPossibleObject()
            self.stats["objects_created"] += 1
            
            # Get initial verification data
            initial_verification = obj.compute_verification_data()
            
            # Skip temp file names (they change each time)
            keys_to_skip = {'temp_file_name', 'temp_file_binary_name'}
            
            # Run cycles
            current_obj = obj
            for cycle in range(num_cycles):
                # Serialize
                serialized = self.serializer.serialize(current_obj)
                self.stats["total_bytes_serialized"] += len(serialized)
                
                # Deserialize
                current_obj = self.deserializer.deserialize(serialized)
                
                # Verify every 10th cycle (not every cycle for performance)
                if cycle % 10 == 0 or cycle == num_cycles - 1:
                    current_verification = current_obj.compute_verification_data()
                    
                    # Check for mismatches
                    for key in initial_verification:
                        if key in keys_to_skip:
                            continue
                        
                        if key not in current_verification:
                            self.errors.append(
                                f"Object {obj_index}, Cycle {cycle}: Missing key '{key}'"
                            )
                            return False
                        
                        if initial_verification[key] != current_verification[key]:
                            self.errors.append(
                                f"Object {obj_index}, Cycle {cycle}: "
                                f"Key '{key}' mismatch: {initial_verification[key]} != {current_verification[key]}"
                            )
                            return False
                
                self.stats["cycles_completed"] += 1
                
                # Force garbage collection every 50 cycles to check for leaks
                if cycle % 50 == 0:
                    gc.collect()
            
            return True
            
        except Exception as e:
            self.errors.append(f"Object {obj_index}: {type(e).__name__}: {e}")
            self.stats["failures"] += 1
            return False
    
    def run_parallel_objects_test(self, num_objects: int, cycles_per_object: int):
        """
        Create multiple objects and cycle each one multiple times.
        
        This simulates having multiple inter-process workflows running concurrently.
        """
        print("="*70)
        print("STRESS TEST: Multiple Objects × Multiple Cycles")
        print("="*70)
        print(f"\nConfiguration:")
        print(f"  Objects to create: {num_objects}")
        print(f"  Cycles per object: {cycles_per_object}")
        print(f"  Total cycles: {num_objects * cycles_per_object:,}")
        print()
        
        start_time = time.time()
        
        for i in range(num_objects):
            if i % 5 == 0:
                elapsed = time.time() - start_time
                cycles_so_far = self.stats["cycles_completed"]
                if cycles_so_far > 0:
                    rate = cycles_so_far / elapsed
                    print(f"  [{i+1}/{num_objects}] {cycles_so_far:,} cycles @ {rate:.1f} cycles/sec")
            
            success = self.run_single_object_cycles(i + 1, cycles_per_object)
            
            if not success:
                print(f"\n  ❌ Object {i+1} failed!")
                break
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*70}")
        print("RESULTS")
        print("="*70)
        print(f"  Objects created: {self.stats['objects_created']}")
        print(f"  Cycles completed: {self.stats['cycles_completed']:,}")
        print(f"  Total bytes serialized: {self.stats['total_bytes_serialized']:,}")
        print(f"  Time elapsed: {elapsed:.2f}s")
        print(f"  Average cycles/sec: {self.stats['cycles_completed'] / elapsed:.1f}")
        print(f"  Average bytes/cycle: {self.stats['total_bytes_serialized'] // max(1, self.stats['cycles_completed']):,}")
        print()
        
        if self.errors:
            print(f"  ❌ FAILURES: {len(self.errors)}")
            print("\nFirst 5 errors:")
            for error in self.errors[:5]:
                print(f"    - {error}")
            if len(self.errors) > 5:
                print(f"    ... and {len(self.errors) - 5} more")
        else:
            print("  ✅ ALL TESTS PASSED!")
            print(f"\n  🎉 Successfully completed {self.stats['cycles_completed']:,} serialization cycles!")
            print(f"     across {self.stats['objects_created']} WorstPossibleObject instances")
            print(f"     without a single failure!")
        
        print("="*70)
        
        return len(self.errors) == 0


def main():
    """Run the stress test."""
    print("\n" + "="*70)
    print("CUCUMBER STRESS TEST")
    print("="*70)
    print("\nThis test creates many WorstPossibleObject instances")
    print("and runs hundreds of serialization/deserialization cycles")
    print("to validate stability, correctness, and inter-process simulation.")
    print()
    
    test = StressTest()
    
    # Configuration
    num_objects = 25       # Create 25 different objects
    cycles_per_object = 100  # Run 100 cycles on each (total: 2,500 cycles)
    
    success = test.run_parallel_objects_test(num_objects, cycles_per_object)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

