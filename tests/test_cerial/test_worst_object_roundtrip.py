"""
Test full round-trip serialization/deserialization of WorstPossibleObject.

This is the ultimate test - if WorstPossibleObject round-trips successfully,
then cerial can handle pretty much anything.
"""

import pytest
from suitkaise.cerial._int.serializer import Cerializer
from suitkaise.cerial._int.deserializer import Decerializer
from suitkaise.cerial._int.worst_possible_object.worst_possible_obj import WorstPossibleObject


class TestWorstObjectRoundTrip:
    """Test complete round-trip of WorstPossibleObject."""
    
    def setup_method(self):
        """Create serializer and deserializer for each test."""
        self.serializer = Cerializer(debug=False, verbose=False)
        self.deserializer = Decerializer(debug=False, verbose=False)
    
    def test_worst_object_serialization(self):
        """First, verify we can serialize WorstPossibleObject."""
        print("\n" + "="*70)
        print("STEP 1: Creating WorstPossibleObject...")
        print("="*70)
        
        obj = WorstPossibleObject()
        
        print("\n" + "="*70)
        print("STEP 2: Serializing WorstPossibleObject...")
        print("="*70)
        
        serialized = self.serializer.serialize(obj)
        
        print(f"\n✓ Serialization successful!")
        print(f"  Size: {len(serialized):,} bytes")
        print(f"  Type: {type(serialized)}")
    
    def test_worst_object_deserialization(self):
        """Test we can deserialize WorstPossibleObject."""
        print("\n" + "="*70)
        print("STEP 1: Creating and serializing WorstPossibleObject...")
        print("="*70)
        
        obj = WorstPossibleObject()
        serialized = self.serializer.serialize(obj)
        
        print(f"✓ Serialized: {len(serialized):,} bytes")
        
        print("\n" + "="*70)
        print("STEP 2: Deserializing WorstPossibleObject...")
        print("="*70)
        
        reconstructed = self.deserializer.deserialize(serialized)
        
        print(f"\n✓ Deserialization successful!")
        print(f"  Type: {type(reconstructed).__name__}")
        print(f"  Is WorstPossibleObject: {isinstance(reconstructed, WorstPossibleObject)}")
    
    def test_worst_object_full_round_trip(self):
        """Test full round-trip with verification."""
        print("\n" + "="*70)
        print("FULL ROUND-TRIP TEST: WorstPossibleObject")
        print("="*70)
        
        # STEP 1: Create original object
        print("\n[1/4] Creating original WorstPossibleObject...")
        original = WorstPossibleObject()
        original_verification = original.compute_verification_data()
        
        print(f"✓ Original object created")
        print(f"  Verification keys: {len(original_verification)}")
        
        # STEP 2: Serialize
        print("\n[2/4] Serializing...")
        serialized = self.serializer.serialize(original)
        
        print(f"✓ Serialized to {len(serialized):,} bytes")
        
        # STEP 3: Deserialize
        print("\n[3/4] Deserializing...")
        reconstructed = self.deserializer.deserialize(serialized)
        
        print(f"✓ Deserialized successfully")
        print(f"  Type: {type(reconstructed).__name__}")
        assert isinstance(reconstructed, WorstPossibleObject), "Reconstructed object is not WorstPossibleObject!"
        
        # STEP 4: Verify state
        print("\n[4/4] Verifying reconstructed state...")
        reconstructed_verification = reconstructed.compute_verification_data()
        
        # Compare verification data
        # Note: Temp file names are expected to be different (they get new OS-assigned names)
        # but their content and position are preserved
        keys_to_skip = {
            'temp_file_name',           # Temp files get new names
            'temp_file_binary_name',    # Temp files get new names
        }
        
        mismatches = []
        for key in original_verification:
            # Skip keys that are expected to be different
            if key in keys_to_skip:
                continue
                
            if key not in reconstructed_verification:
                mismatches.append(f"  ✗ Missing key: {key}")
            elif original_verification[key] != reconstructed_verification[key]:
                orig_val = original_verification[key]
                recon_val = reconstructed_verification[key]
                mismatches.append(f"  ✗ {key}: {orig_val} != {recon_val}")
        
        # Check for extra keys
        for key in reconstructed_verification:
            if key not in original_verification:
                mismatches.append(f"  ✗ Extra key: {key}")
        
        if mismatches:
            print("\n❌ VERIFICATION FAILED:")
            for mismatch in mismatches[:10]:  # Show first 10
                print(mismatch)
            if len(mismatches) > 10:
                print(f"  ... and {len(mismatches) - 10} more mismatches")
            assert False, f"Verification failed with {len(mismatches)} mismatches"
        else:
            print(f"✓ All {len(original_verification)} verification checks passed!")
        
        print("\n" + "="*70)
        print("🎉 FULL ROUND-TRIP SUCCESSFUL!")
        print("="*70)
    
    def test_multiple_round_trips(self):
        """Test multiple serialization/deserialization cycles."""
        print("\n" + "="*70)
        print("MULTIPLE ROUND-TRIP TEST")
        print("="*70)
        
        # Create original
        obj1 = WorstPossibleObject()
        verification1 = obj1.compute_verification_data()
        
        num_cycles = 3
        current_obj = obj1
        
        for i in range(num_cycles):
            print(f"\n[Cycle {i+1}/{num_cycles}]")
            
            # Serialize
            serialized = self.serializer.serialize(current_obj)
            print(f"  Serialized: {len(serialized):,} bytes")
            
            # Deserialize
            current_obj = self.deserializer.deserialize(serialized)
            print(f"  Deserialized: {type(current_obj).__name__}")
            
            # Verify
            current_verification = current_obj.compute_verification_data()
            
            # Compare with original
            # Note: Skip temp file names (they're expected to be different)
            keys_to_skip = {
                'temp_file_name',
                'temp_file_binary_name',
            }
            
            mismatches = []
            for key in verification1:
                if key in keys_to_skip:
                    continue
                    
                if key not in current_verification:
                    mismatches.append(key)
                elif verification1[key] != current_verification[key]:
                    mismatches.append(key)
            
            if mismatches:
                print(f"  ✗ Failed: {len(mismatches)} mismatches")
                assert False, f"Cycle {i+1} failed with {len(mismatches)} mismatches"
            else:
                print(f"  ✓ Verified: matches original")
        
        print("\n" + "="*70)
        print(f"🎉 ALL {num_cycles} CYCLES SUCCESSFUL!")
        print("="*70)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])

