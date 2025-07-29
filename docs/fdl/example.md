# FDL Examples

## Basic Data Formatting

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

## Time and Date Formatting

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

## Debug Formatting

```python
# using debugging formats automatically
fd.dprint("Your message with vars", (tuple_of_vars), priority_level_1_to_5)

# toggling if debug messages should be printed

# will only print messages at level 2 or higher
fd.set_dprint_level(2)
```

## Complex Data Structure Example

```python
my_list = [
    "hello",
    "world",
    "this",
    "is",
    "a",
    "test",
    "of",
    "the",
    "list",
    "functionality"
]

my_dict = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
    "key4": "value4",
    "key5": "value5"
}

my_set = {
    "apple",
    "banana",
    "cherry",
    "date",
    "elderberry"
}

my_tuple = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth"
)

my_int = 42
my_float = 3.14
my_bool = True
my_none = None
my_bytes = b"byte string"
my_complex = 1 + 2j
my_range = range(10)
my_dict_of_lists = {
    "list1": ["item1", "item2", "item3"],
    "list2": ["item4", "item5", "item6"]
}
my_dict_of_sets = {
    "set1": {"item1", "item2", "item3"},
    "set2": {"item4", "item5", "item6"}
}
my_dict_of_tuples = {
    "tuple1": ("item1", "item2", "item3"),
    "tuple2": ("item4", "item5", "item6")
}

def nlprint(*args, **kwargs):
    """
    Print each argument on a new line.
    
    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments (not used).
    """
    for arg in args:
        try:
            print(arg)
        except Exception as e:
            print(f"Error printing argument {arg}: {e}")

nlprint(
    my_list,
    my_dict,
    my_set,
    my_tuple,
    my_int,
    my_float,
    my_bool,
    my_none,
    my_bytes,
    my_complex,
    my_range,
    my_dict_of_lists,
    my_dict_of_sets,
    my_dict_of_tuples
)
```

## Format Comparison

### Raw Python Output:
```
['hello', 'world', 'this', 'is', 'a', 'test', 'of', 'the', 'list', 'functionality']
{'key1': 'value1', 'key2': 'value2', 'key3': 'value3', 'key4': 'value4', 'key5': 'value5'}
{'banana', 'apple', 'cherry', 'elderberry', 'date'}
('first', 'second', 'third', 'fourth', 'fifth')
```

### Display Format:
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

### Debug Format:
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