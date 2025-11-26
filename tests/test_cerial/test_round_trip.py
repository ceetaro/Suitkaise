"""
Round-trip tests for cerial serializer and deserializer.

These tests verify that objects can be serialized and then deserialized
back to their original state.
"""

import pytest
from suitkaise.cerial._int.serializer import CerialSerializer
from suitkaise.cerial._int.deserializer import CerialDeserializer


class TestBasicRoundTrip:
    """Test basic round-trip serialization/deserialization."""
    
    def setup_method(self):
        """Create serializer and deserializer for each test."""
        self.serializer = CerialSerializer(debug=False, verbose=False)
        self.deserializer = CerialDeserializer(debug=False, verbose=False)
    
    def test_primitives(self):
        """Test round-trip of primitive types."""
        data = {
            'int': 42,
            'float': 3.14,
            'str': 'hello',
            'bool': True,
            'none': None,
            'bytes': b'data',
        }
        
        serialized = self.serializer.serialize(data)
        deserialized = self.deserializer.deserialize(serialized)
        
        assert deserialized == data
        print(f"\n✓ Primitives: {deserialized}")
    
    def test_collections(self):
        """Test round-trip of basic collections."""
        data = {
            'list': [1, 2, 3],
            'tuple': (4, 5, 6),
            'set': {7, 8, 9},
            'dict': {'a': 1, 'b': 2},
        }
        
        serialized = self.serializer.serialize(data)
        deserialized = self.deserializer.deserialize(serialized)
        
        assert deserialized['list'] == data['list']
        assert deserialized['tuple'] == data['tuple']
        assert deserialized['set'] == data['set']
        assert deserialized['dict'] == data['dict']
        print(f"\n✓ Collections: list={deserialized['list']}, tuple={deserialized['tuple']}")
    
    def test_nested_collections(self):
        """Test round-trip of nested collections."""
        data = {
            'nested_list': [[1, 2], [3, 4]],
            'nested_dict': {'outer': {'inner': 'value'}},
            'mixed': {'list': [1, {'key': 'value'}]},
        }
        
        serialized = self.serializer.serialize(data)
        deserialized = self.deserializer.deserialize(serialized)
        
        assert deserialized == data
        print(f"\n✓ Nested collections: {deserialized['nested_dict']}")
    
    def test_circular_reference_dict(self):
        """Test round-trip of circular reference in dict."""
        data = {'a': 1, 'b': 2}
        data['self'] = data
        
        serialized = self.serializer.serialize(data)
        deserialized = self.deserializer.deserialize(serialized)
        
        # Check that circular reference is preserved
        assert deserialized['self'] is deserialized
        assert deserialized['a'] == 1
        assert deserialized['b'] == 2
        print(f"\n✓ Circular dict: self-reference={deserialized['self'] is deserialized}")
    
    def test_circular_reference_list(self):
        """Test round-trip of circular reference in list."""
        data = [1, 2, 3]
        data.append(data)
        
        serialized = self.serializer.serialize(data)
        deserialized = self.deserializer.deserialize(serialized)
        
        # Check that circular reference is preserved
        assert deserialized[3] is deserialized
        assert deserialized[:3] == [1, 2, 3]
        print(f"\n✓ Circular list: self-reference={deserialized[3] is deserialized}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

