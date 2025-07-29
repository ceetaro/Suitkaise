# FDL (Format/Debug Library) Concept

## Overview

fdprint (format/debug print) is a super formatter that can format any standard data type, date and time, and more. It's a tool that allows users to automatically print data in better formats, formatted for better display or better debugging.

## Core Philosophy

FDL provides intelligent formatting that adapts to the context - whether you need clean display output or detailed debugging information with type annotations and structure visualization.

## Key Features

### Automatic Data Type Formatting
- **Lists, dictionaries, sets, tuples**: Intelligent structure formatting
- **Primitive types**: Enhanced display for numbers, booleans, None
- **Complex types**: Bytes, complex numbers, ranges
- **Nested structures**: Recursive formatting for complex data

### Display vs Debug Modes

**Display Mode (`fprint`)**:
- Clean, readable output for end users
- Comma-separated lists
- Key-value pairs for dictionaries
- Minimal visual noise

**Debug Mode (`dprint`)**:
- Type annotations for every element
- Structural indicators (brackets, indentation)
- Detailed formatting for debugging
- Color coding for easier identification

### Time and Date Formatting
- **Default formats**: Automatic time/date formatting
- **Custom formats**: `{hms6:now}`, `{datePST:now}` style formatting
- **Threshold-based**: Automatic format selection based on time ranges
- **Timezone support**: Multiple timezone formatting options

### Priority-Based Debug Levels
- **Level system**: 1-5 priority levels for debug messages
- **Configurable filtering**: `fd.set_dprint_level(2)` to show only level 2+
- **Context-aware**: Different detail levels for different situations

## Format Examples

### Raw Python Output
```python
['hello', 'world', 'this', 'is', 'a', 'test']
{'key1': 'value1', 'key2': 'value2'}
```

### Display Format
```
hello, world, this, is, a, test

key1: value1
key2: value2
```

### Debug Format
```
(list) [
    'hello', 'world', 'this', 'is', 'a', 'test'
] (list)

(dict) {
   'key1': 'value1',
   'key2': 'value2'
} (dict)
```

## Integration Benefits
- **Cross-module compatibility**: Works with all SK data types
- **Automatic detection**: Intelligently chooses best format
- **Extensible**: Easy to add new data types and formats
- **Performance-aware**: Efficient formatting for large data structures

## Examples

### Basic Data Formatting

```python
from suitkaise import fdprint as fd
import time

# its as easy as...
value1 = {
    "dict": {"a": "dict"},
    "list": []
}

fd.fprint("This is value1: {value1}", value1)
```

### Time and Date Formatting

```python
# printing dates or times
now = time.time()

# print using our default time format (see report section for more details)
fd.fprint("Printing {value1} at {time:now}", (value1, now))
# or...
# print using our default date format
fd.fprint("Printing {value1} at {date:now}", (value1, now))

# using custom time and date formats

# print using hours, minutes, seconds and microseconds
fd.fprint("Printing {value1} at {hms6:now}", (value1, now))
# print using date and timezone
fd.fprint("Printing {value1} at {datePST:now}", (value1, now))
```

### Debug Formatting

```python
# using debugging formats automatically
fd.dprint("Your message with vars", (tuple_of_vars), priority_level_1_to_5)

# toggling if debug messages should be printed

# will only print messages at level 2 or higher
fd.set_dprint_level(2)
```

### Format Comparison

**Raw Python Output:**
```
['hello', 'world', 'this', 'is', 'a', 'test', 'of', 'the', 'list', 'functionality']
{'key1': 'value1', 'key2': 'value2', 'key3': 'value3', 'key4': 'value4', 'key5': 'value5'}
{'banana', 'apple', 'cherry', 'elderberry', 'date'}
('first', 'second', 'third', 'fourth', 'fifth')
```

**Display Format:**
```
hello, world, this, is, a, test, of, the, list, functionality

key1: value1
key2: value2
key3: value3 
key4: value4
key5: value5

banana, apple, cherry, elderberry, date

(first, second, third, fourth, fifth)
```

**Debug Format:**
```
(list) [
    'hello', 'world', 'this', 'is', 'a', 'test', 'of', 'the', 'list', 'functionality'
] (list)

(dict) {
   'key1': 'value1', 
   'key2': 'value2', 
   'key3': 'value3', 
   'key4': 'value4', 
   'key5': 'value5'
} (dict)

(set) {
    'banana', 'apple', 'cherry', 'elderberry', 'date'
} (set)

(tuple) (
    'first', 'second', 'third', 'fourth', 'fifth'
) (tuple)
```