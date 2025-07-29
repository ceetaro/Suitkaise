"""
FDL Example - Format/Debug Library

This example demonstrates:
- Display formatting with fprint
- Debug formatting with dprint
- Time and date formatting
- Debug level control
"""

from suitkaise import fdprint as fd
import time

def main():
    print("=== Basic Data Formatting ===")
    
    # Sample data structures
    sample_dict = {
        "name": "John Doe",
        "age": 30,
        "city": "New York",
        "skills": ["Python", "JavaScript", "SQL"]
    }
    
    sample_list = ["apple", "banana", "cherry", "date", "elderberry"]
    sample_set = {"red", "green", "blue", "yellow"}
    sample_tuple = ("first", "second", "third")
    
    # Display formatting (clean, user-friendly)
    print("--- Display Format (fprint) ---")
    fd.fprint("Dictionary: {data}", sample_dict)
    fd.fprint("List: {data}", sample_list)
    fd.fprint("Set: {data}", sample_set)
    fd.fprint("Tuple: {data}", sample_tuple)
    
    print("\n--- Debug Format (dprint) ---")
    # Debug formatting (detailed, with type information)
    fd.dprint("Dictionary with types", (sample_dict,), 1)
    fd.dprint("List with structure", (sample_list,), 1)
    fd.dprint("Set with type info", (sample_set,), 1)
    fd.dprint("Tuple structure", (sample_tuple,), 1)
    
    print("\n=== Time and Date Formatting ===")
    
    now = time.time()
    
    # Default time formats
    fd.fprint("Current time (default): {time:now}", now)
    fd.fprint("Current date (default): {date:now}", now)
    
    # Custom time formats
    fd.fprint("Time with microseconds: {hms6:now}", now)
    fd.fprint("Date with timezone: {datePST:now}", now)
    
    print("\n=== Debug Level Control ===")
    
    # Set debug level to 2 (only show level 2 and higher)
    fd.set_dprint_level(2)
    
    print("Debug level set to 2 - testing different priority levels:")
    
    fd.dprint("Level 1 message (should not show)", ("hidden",), 1)
    fd.dprint("Level 2 message (should show)", ("visible",), 2)
    fd.dprint("Level 3 message (should show)", ("also visible",), 3)
    
    # Reset debug level
    fd.set_dprint_level(1)
    print("\nDebug level reset to 1:")
    fd.dprint("Level 1 message (now visible)", ("now showing",), 1)
    
    print("\n=== Complex Data Structures ===")
    
    complex_data = {
        "user": {
            "id": 12345,
            "profile": {
                "name": "Alice Smith",
                "preferences": ["dark_mode", "notifications"],
                "settings": {
                    "theme": "dark",
                    "language": "en",
                    "timezone": "UTC-5"
                }
            }
        },
        "data": [
            {"type": "document", "size": 1024},
            {"type": "image", "size": 2048},
            {"type": "video", "size": 10240}
        ],
        "metadata": {
            "created": time.time(),
            "version": "1.0.0",
            "tags": {"important", "user-data", "processed"}
        }
    }
    
    print("--- Complex Structure (Display) ---")
    fd.fprint("Complex data: {data}", complex_data)
    
    print("\n--- Complex Structure (Debug) ---")
    fd.dprint("Complex data with full type info", (complex_data,), 1)
    
    print("\n=== Primitive Types ===")
    
    primitives = {
        "integer": 42,
        "float": 3.14159,
        "boolean": True,
        "none": None,
        "string": "Hello, World!",
        "bytes": b"byte string",
        "complex": 1 + 2j
    }
    
    for name, value in primitives.items():
        fd.fprint(f"{name}: {{value}}", value)
        fd.dprint(f"{name} debug", (value,), 1)

if __name__ == "__main__":
    main()