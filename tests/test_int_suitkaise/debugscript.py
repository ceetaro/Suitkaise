#!/usr/bin/env python3
"""
Comprehensive formatting test for all data types in both Display and Debug modes.
This script systematically tests every type that your formatting system handles.
"""

# Import your formatting functions
from suitkaise.fdprint import fprint, dprint

def test_display_mode():
    """Test all data types using fprint() - Display Mode (clean formatting)"""
    print("=" * 60)
    print("DISPLAY MODE TESTING (fprint - clean formatting)")
    print("=" * 60)
    
    # None type - looks good
    none_obj = None
    fprint("My None: {}", none_obj)
    
    # Strings - looks good
    string_obj = "hello world"
    fprint("My string: {}", string_obj)
    
    # String with special characters - looks good
    special_string = "hello\nworld\ttab"
    fprint("My special string: {}", special_string)
    
    # Empty string - looks good
    empty_string = ""
    fprint("My empty string: {}", empty_string)
    
    # Integers - looks good
    int_obj = 42
    fprint("My integer: {}", int_obj)
    
    # Large integer
    # Current output: 12345678900
    # Desired output if greater than 9.999,999,999: 1.23456789 e+n with space between number and e
    large_int = 12345678900
    fprint("My large integer: {}", large_int)
    
    # Negative integer - looks good
    negative_int = -123
    fprint("My negative integer: {}", negative_int)
    
    # Float - looks good
    float_obj = 3.14159
    fprint("My float: {}", float_obj)
    
    # Very small float
    # Current output: 1e-06
    # Desired output: 1.0 e-6 (keep at least one decimal place, even if it's zero)
    # right n
    small_float = 0.000001
    fprint("My small float: {}", small_float)
    
    # Complex number - looks good
    complex_obj = 3 + 4j
    fprint("My complex: {}", complex_obj)
    
    # Boolean True
    # Current output: same color as integer
    # Desired output: bold text, standard green color like 🟩
    bool_true = True
    fprint("My boolean True: {}", bool_true)
    
    # Boolean False
    # Current output: same color as integer
    # Desired output: bold text, standard lighter red color like a watermelon red
    bool_false = False
    fprint("My boolean False: {}", bool_false)
    
    # Empty list - looks good
    empty_list = []
    fprint("My empty list: {}", empty_list)
    
    # Simple list - looks good, integers are correctly colored
    simple_list = [1, 2, 3]
    fprint("My simple list: {}", simple_list)
    
    # Mixed list - looks good, mixed types are handled with correct colors
    mixed_list = [1, "hello", True, None]
    fprint("My mixed list: {}", mixed_list)
    
    # Nested list - looks good, nested lists are handled with correct colors
    nested_list = [1, [2, 3], [4, [5, 6]]]
    fprint("My nested list: {}", nested_list)
    
    # Empty tuple
    # Current output: ()
    # Desired output: () with soft yellow color
    empty_tuple = ()
    fprint("My empty tuple: {}", empty_tuple)
    
    # Single item tuple
    # Current output: (42,)
    # Desired output: (42, ) with parentheses in soft yellow color
    single_tuple = (42,)
    fprint("My single tuple: {}", single_tuple)
    
    # Simple tuple
    # Current output: (1, 2, 3)
    # Desired output: (1, 2, 3) with parentheses in soft yellow color
    simple_tuple = (1, 2, 3)
    fprint("My simple tuple: {}", simple_tuple)
    
    # Mixed tuple
    # Current output: (1, 'hello', True, None)
    # Desired output: (1, 'hello', True, None) with parentheses in soft yellow color
    mixed_tuple = (1, "hello", True, None)
    fprint("My mixed tuple: {}", mixed_tuple)
    
    # Empty dictionary - looks good
    empty_dict = {}
    fprint("My empty dict: {}", empty_dict)
    
    # Simple dictionary
    # Current output: key1: value1
    # key2: value2
    # Desired output: key1: value1, key2: value2 -- with:
    # - 60 characters max width, and values must be on the same line as the keys
    # - "My simple dict: " counts towards the 60 characters for the first line
    # - if more than one line needed, once whole dict is printed, new line should be added
    # - key value pairs should be separated by commas
    # - keys should be a slightly lighter green than string color so that they differentiate from string values
    simple_dict = {"key1": "value1", "key2": "value2"}
    fprint("My simple dict: {}", simple_dict)
    
    # Mixed dictionary
    # Current output: name: Alice
    # age: 30
    # active: True
    # data: None
    # Desired output: same concept as simple_dict, but with the mixed types
    mixed_dict = {"name": "Alice", "age": 30, "active": True, "data": None}
    fprint("My mixed dict: {}", mixed_dict)
    
    # Nested dictionary
    # Current output: My nested dict: user: name: Bob
    # details: age: 25
    # city: NYC
    # Desired output: user: name: Bob, details: age: 25, city: NYC -- with:
    # - 60 characters max width, and values must be on the same line as the keys
    # - "My nested dict: " counts towards the 60 characters for the first line
    # - if more than one line needed, once whole dict is printed, new line should be added
    # - key value pairs should be separated by commas
    # - keys should be a slightly lighter green than string color so that they differentiate from string values
    # - in this case, "user" and "details" should be bold, as they are the top-level keys
    # - if there are than 2 layers of nesting, make the key color the next color of the rainbow for each layer
    nested_dict = {"user": {"name": "Bob", "details": {"age": 25, "city": "NYC"}}}
    fprint("My nested dict: {}", nested_dict)
    
    # Dictionary with list values
    # My dict with lists: numbers: 1, 2, 3
    # words: hello, world
    # Desired output: numbers: 1, 2, 3, words: hello, world -- with:
    # same concept as simple_dict, but with the list values. if the list is too long,
    # it should be truncated to 5 items and then "..." added at the end with how many more items there are.
    dict_with_lists = {"numbers": [1, 2, 3, 4, 5], "words": ["hello", "world"]}
    fprint("My dict with lists: {}", dict_with_lists)

    # currently, this prints all 500 items in the list, which is too long
    list = [1, 2, 3, 4, 5]
    big_list = []
    for i in range(100):
        big_list.append(list)
    fprint("My big list: {}", big_list)
    
    # Empty set - looks good
    empty_set = set()
    fprint("My empty set: {}", empty_set)
    
    # Simple set - looks good
    simple_set = {1, 2, 3}
    fprint("My simple set: {}", simple_set)
    
    # Mixed set
    # Current output: 1, hello
    # Desired output: 1, hello, True
    mixed_set = {1, "hello", True}  # Note: True and 1 might be deduplicated
    fprint("My mixed set: {}", mixed_set)
    
    # String set - looks good
    string_set = {"apple", "banana", "cherry"}
    fprint("My string set: {}", string_set)
    
    # Frozenset - looks good
    frozen_set = frozenset([1, 2, 3])
    fprint("My frozenset: {}", frozen_set)
    
    # Range object - looks good
    range_obj = range(5)
    fprint("My range: {}", range_obj)
    
    # Range with step
    # Current output: 0, 10
    # Desired output: 0, 10 (+2) -- with "(+2)" in a dim gray similar to None color but a little darker
    range_step = range(0, 10, 2)
    fprint("My range with step: {}", range_step)
    
    # Bytes - looks good
    bytes_obj = b"hello"
    fprint("My bytes: {}", bytes_obj)
    
    # Bytes with non-UTF8
    # Current output: no visible output at all
    # Desired output: 00, 01, 02, 03 (binary) -- with "binary" in a dim gray similar to None color but a little darker
    # This should print the bytes in a readable format, and truncate if too long (more than 5 bytes)
    binary_bytes = b"\x00\x01\x02\x03"
    fprint("My binary bytes: {}", binary_bytes)
    
    # Bytearray - looks good
    bytearray_obj = bytearray(b"hello")
    fprint("My bytearray: {}", bytearray_obj)
    
    # Complex nested structure
    # if we recognize this as a complex structure, we should print it in a readable format like this:
    # My complex structure: 
    #   users: 
    #       name: Alice, scores: 95, 87, 92
    #       name: Bob, scores: 88, 91, 85
    #   metadata:
    #       total_users: 2, active: True, tags: important, test, demo
    # \n
    complex_structure = {
        "users": [
            {"name": "Alice", "scores": [95, 87, 92]},
            {"name": "Bob", "scores": [88, 91, 85]}
        ],
        "metadata": {
            "total_users": 2,
            "active": True,
            "tags": {"important", "test", "demo"}
        }
    }
    fprint("My complex structure: {}", complex_structure)


def test_debug_mode():
    """Test all data types using dprint() - Debug Mode (verbose formatting)"""
    print("\n" + "=" * 60)
    print("DEBUG MODE TESTING (dprint - verbose formatting)")
    print("=" * 60)
    
    # None type
    # Current output: My None [(None) None] - timestamp -- timestamp is all same color
    # Desired output: My None [(None) None] - timestamp -- hour and minute should be much dimmer than second and below
    # - outer brackets [] should be in a dim gray similar to None color but a little darker
    none_obj = None
    dprint("My None", (none_obj,))
    
    # Strings
    # good except for outer brackets and timestamp coloring
    string_obj = "hello world"
    dprint("My string", (string_obj,))
    
    # String with special characters
    # Current output: My special string [(string) 'hello\nworld\ttab'] - timestamp
    # Desired output: My special string [(string) 'hello\nworld\ttab'] - timestamp -- with:
    # - outer brackets [] should be in a dim gray similar to None color but a little darker
    # - timestamp should have hour and minute in a dimmer color than second and below
    # - special characters should be light orange
    special_string = "hello\nworld\ttab"
    dprint("My special string", (special_string,))
    
    # Empty string - good except for outer brackets and timestamp coloring
    empty_string = ""
    dprint("My empty string", (empty_string,))
    
    # Integers
    # Current output: My integer [(integer) 42] - timestamp
    # Desired output: My integer [(int) 42] - timestamp -- with the changed outer brackets and coloring
    int_obj = 42
    dprint("My integer", (int_obj,))
    
    # Large integer - same changes as int
    # if larger than 9,999,999, should be formatted as 1.23456789 e+10
    # if e+n is used, change (int) color to a green blue
    large_int = 1234567890
    dprint("My large integer", (large_int,))
    
    # Negative integer
    # Current output: My negative integer [(integer) -123] - timestamp
    # Desired output: My negative integer [(-int) -123] - timestamp
    # - with the changed outer brackets and coloring
    # - "-int" should be in a red color, while () remain same color
    negative_int = -123
    dprint("My negative integer", (negative_int,))
    
    # Float - good except for outer brackets and timestamp coloring
    float_obj = 3.14159
    dprint("My float", (float_obj,))
    
    # Very small float - good except for outer brackets and timestamp coloring
    # if smaller than 0.00001, should be formatted as 1.0 e-6 (keep at least one decimal place)
    # if e-n is used, change (float) color to a green blue
    small_float = 0.000001
    dprint("My small float", (small_float,))
    
    # Complex number - good except for outer brackets and timestamp coloring
    complex_obj = 3 + 4j
    dprint("My complex", (complex_obj,))
    
    # Boolean True
    # Current output: My boolean True [(boolean) True] - timestamp
    # Desired output: My boolean True [(bool) True] - timestamp
    # - True should be in a bold text, standard green color like 🟩
    bool_true = True
    dprint("My boolean True", (bool_true,))
    
    # Boolean False
    # Current output: My boolean False [(boolean) False] - timestamp
    # Desired output: My boolean False [(bool) False] - timestamp
    # - False should be in a bold text, standard lighter red color like a watermelon red
    bool_false = False
    dprint("My boolean False", (bool_false,))
    
    # all lists have their first bracket the correct yellow, but the second one is white

    # Empty list
    # Current output: My empty list [(list) []] - timestamp
    # change: list brackets should be yellow
    empty_list = []
    dprint("My empty list", (empty_list,))
    
    # Simple list - list brackets should be yellow, outer brackets and coloring should be changed
    # entries now follow the same 60 width rules as fprint instead of being on one line each
    simple_list = [1, 2, 3]
    dprint("My simple list", (simple_list,))
    
    # Mixed list - same as simple list
    mixed_list = [1, "hello", True, None]
    dprint("My mixed list", (mixed_list,))
    
    # Nested list - same as simple list, but for every nested layer, change the color of the brackets
    #   to the next color of the rainbow
    nested_list = [1, [2, 3], [4, [5, 6]]]
    dprint("My nested list", (nested_list,))
    
    # Empty tuple
    # tuple parentheses should be soft yellow like the rest of the brackets
    empty_tuple = ()
    dprint("My empty tuple", (empty_tuple,))
    
    # Single item tuple has error displaying color correctly
    single_tuple = (42,)
    dprint("My single tuple", (single_tuple,))
    
    # Simple tuple
    simple_tuple = (1, 2, 3)
    dprint("My simple tuple", (simple_tuple,))
    
    # Mixed tuple
    mixed_tuple = (1, "hello", True, None)
    dprint("My mixed tuple", (mixed_tuple,))
    
    # Empty dictionary
    empty_dict = {}
    dprint("My empty dict", (empty_dict,))
    
    # Simple dictionary
    simple_dict = {"key1": "value1", "key2": "value2"}
    dprint("My simple dict", (simple_dict,))
    
    # Mixed dictionary
    mixed_dict = {"name": "Alice", "age": 30, "active": True, "data": None}
    dprint("My mixed dict", (mixed_dict,))
    
    # Nested dictionary
    nested_dict = {"user": {"name": "Bob", "details": {"age": 25, "city": "NYC"}}}
    dprint("My nested dict", (nested_dict,))
    
    # Dictionary with list values
    dict_with_lists = {"numbers": [1, 2, 3], "words": ["hello", "world"]}
    dprint("My dict with lists", (dict_with_lists,))
    
    # Empty set
    empty_set = set()
    dprint("My empty set", (empty_set,))
    
    # Simple set
    simple_set = {1, 2, 3}
    dprint("My simple set", (simple_set,))
    
    # Mixed set
    mixed_set = {1, "hello", True}  # Note: True and 1 might be deduplicated
    dprint("My mixed set", (mixed_set,))
    
    # String set
    string_set = {"apple", "banana", "cherry"}
    dprint("My string set", (string_set,))
    
    # Frozenset
    frozen_set = frozenset([1, 2, 3])
    dprint("My frozenset", (frozen_set,))
    
    # Range object
    range_obj = range(5)
    dprint("My range", (range_obj,))
    
    # Range with step
    range_step = range(0, 10, 2)
    dprint("My range with step", (range_step,))
    
    # Bytes
    bytes_obj = b"hello"
    dprint("My bytes", (bytes_obj,))
    
    # Bytes with non-UTF8
    binary_bytes = b"\x00\x01\x02\x03"
    dprint("My binary bytes", (binary_bytes,))
    
    # Bytearray
    bytearray_obj = bytearray(b"hello")
    dprint("My bytearray", (bytearray_obj,))
    
    # Complex nested structure
    complex_structure = {
        "users": [
            {"name": "Alice", "scores": [95, 87, 92]},
            {"name": "Bob", "scores": [88, 91, 85]}
        ],
        "metadata": {
            "total_users": 2,
            "active": True,
            "tags": {"important", "test", "demo"}
        }
    }
    dprint("My complex structure", (complex_structure,))


def test_time_formatting():
    """Test time formatting in both modes"""
    print("\n" + "=" * 60)
    print("TIME FORMATTING TESTING")
    print("=" * 60)
    
    # Test various time formats
    fprint("Current time (time): {time:now}")
    fprint("Current time (hms): {hms:now}")
    fprint("Current time (hm): {hm:now}")
    fprint("Current time (time12): {time12:now}")
    fprint("Current time (hms12): {hms12:now}")
    fprint("Current time (hm12): {hm12:now}")
    fprint("Current date: {date:now}")
    fprint("Current datetime: {datetime:now}")
    fprint("Precise time: {hms6:now}")
    fprint("Millisecond time: {hms3:now}")


def test_edge_cases():
    """Test edge cases and unusual data"""
    print("\n" + "=" * 60)
    print("EDGE CASES TESTING")
    print("=" * 60)
    
    # Very long string
    long_string = "x" * 100
    fprint("My long string: {}", long_string)
    
    # Very deep nesting
    deep_nested = {"a": {"b": {"c": {"d": {"e": "deep"}}}}}
    fprint("My deep nested: {}", deep_nested)
    
    # Large list
    large_list = list(range(20))
    fprint("My large list: {}", large_list)
    
    # Dictionary with numeric keys
    numeric_keys = {1: "one", 2: "two", 3: "three"}
    fprint("My numeric keys dict: {}", numeric_keys)
    
    # Mixed key types (if allowed)
    try:
        mixed_keys = {"string_key": 1, 42: "number_key", True: "bool_key"}
        fprint("My mixed keys dict: {}", mixed_keys)
    except Exception as e:
        print(f"Mixed keys error: {e}")


if __name__ == "__main__":
    """Run all formatting tests"""
    print("Starting comprehensive formatting tests...")
    print("This will test every data type in both Display and Debug modes.\n")
    
    # Test display mode (fprint)
    test_display_mode()
    
    # Test debug mode (dprint)
    test_debug_mode()
    
    # Test time formatting
    test_time_formatting()
    
    # Test edge cases
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
    print("Review the output above to see how each data type is formatted.")
    print("Look for any inconsistencies or formatting issues that need adjustment.")