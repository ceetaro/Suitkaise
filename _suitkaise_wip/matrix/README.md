# Thread-Safe Matrix and Array Library

A Python library providing thread-safe, multi-dimensional matrix and array data structures with numpy-powered operations.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Comprehensive Examples](#comprehensive-examples)
  - [Matrix Operations](#matrix-operations)
  - [Array Operations](#array-operations)
  - [Advanced Usage](#advanced-usage)
  - [Thread Safety Examples](#thread-safety-examples)
- [API Reference](#api-reference)
  - [Matrix Class](#matrix-class)
  - [Array Class](#array-class)
- [Thread Safety](#thread-safety)
- [Performance](#performance)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Features

- **Thread-Safe**: All operations use `threading.RLock` for thread safety
- **Multi-Dimensional**: Support for n-dimensional matrices and arrays
- **Type-Enforced Arrays**: Arrays enforce a single data type with automatic conversion
- **Arithmetic Operations**: Full support for +, -, *, / operations on Arrays
- **Numpy Integration**: Vectorized operations using numpy for performance
- **Easy to Use**: Simple, intuitive API

## Installation

```bash
pip install numpy
```

## Quick Start

### Basic Matrix Usage

```python
from matrix import Matrix

# Create matrices of different dimensions
matrix_1d = Matrix((5,))        # 1D matrix (vector)
matrix_2d = Matrix((3, 4))      # 2D matrix (3 rows, 4 columns)
matrix_3d = Matrix((2, 3, 4))   # 3D matrix

# Set and get values (any data type)
matrix_2d[0, 1] = "Hello World"
matrix_2d[1, 2] = 42
matrix_2d[2, 3] = [1, 2, 3]  # Can store lists
matrix_2d[0, 0] = {"key": "value"}  # Can store dictionaries

print(matrix_2d[0, 1])  # "Hello World"
print(matrix_2d[1, 2])  # 42

# Matrix properties
print(f"Dimensions: {matrix_2d.dimensions}")      # (3, 4)
print(f"Number of dimensions: {matrix_2d.num_dimensions}")  # 2
print(f"Total size: {matrix_2d.size}")           # 12
print(f"Dimension 0 size: {matrix_2d.get_dimension(0)}")  # 3
```

### Array with Type Enforcement

```python
from matrix import Array

# Create arrays with specific data types
int_array = Array((3, 3), int)
float_array = Array((2, 4), float)
str_array = Array((2, 2), str)
bool_array = Array((3, 3), bool)

# Arrays automatically convert values to the specified type
int_array[0, 0] = 5      # Store integer
int_array[0, 1] = 3.7    # Converted to int(3)
int_array[0, 2] = "42"   # Converted to int(42)

str_array[0, 0] = "hello"
str_array[0, 1] = 123    # Converted to "123"

print(int_array[0, 1])   # 3 (converted from 3.7)
print(str_array[0, 1])   # "123" (converted from 123)
```

## Comprehensive Examples

### Matrix Operations

#### Creating and Manipulating Matrices

```python
from matrix import Matrix

# Create different dimensional matrices
vector = Matrix((10,))           # 1D vector
matrix_2d = Matrix((5, 4))       # 2D matrix
matrix_3d = Matrix((2, 3, 4))    # 3D matrix
matrix_4d = Matrix((2, 3, 4, 5)) # 4D matrix

# Fill entire matrix with a value
matrix_2d.fill("default")
print(matrix_2d[2, 1])  # "default"

# Set individual elements
matrix_2d[0, 0] = "start"
matrix_2d[4, 3] = "end"
matrix_3d[1, 2, 3] = {"nested": "data"}

# Copy matrices
backup = matrix_2d.copy()
backup[0, 0] = "modified"
print(matrix_2d[0, 0])  # Still "start" - independent copy

# Compare matrices
matrix1 = Matrix((2, 2))
matrix2 = Matrix((2, 2))
matrix1.fill("same")
matrix2.fill("same")
print(matrix1 == matrix2)  # True
print(matrix1.equalmatrix(matrix2))  # True
```

#### Matrix Replace Operation

```python
# Replace truthy values from one matrix to another
large_matrix = Matrix((4, 4))
large_matrix.fill("original")

small_matrix = Matrix((2, 2))
small_matrix[0, 0] = "new_value"
small_matrix[1, 1] = "another_new"
# small_matrix[0, 1] and small_matrix[1, 0] remain None (falsy)

large_matrix.replace(small_matrix)
# Only truthy values from small_matrix are copied
print(large_matrix[0, 0])  # "new_value"
print(large_matrix[1, 1])  # "another_new"
print(large_matrix[0, 1])  # "original" (unchanged)
print(large_matrix[2, 2])  # "original" (outside small_matrix range)
```

### Array Operations

#### Creating and Type Enforcement

```python
from matrix import Array

# Create arrays with different types
int_arr = Array((3, 3), int)
float_arr = Array((2, 4), float)
str_arr = Array((2, 2), str)
bool_arr = Array((3, 3), bool)

# Type enforcement examples
int_arr[0, 0] = 5        # Direct integer
int_arr[0, 1] = 3.9      # Converted to 3
int_arr[0, 2] = "42"     # Converted to 42
int_arr[1, 0] = True     # Converted to 1

float_arr[0, 0] = 3.14   # Direct float
float_arr[0, 1] = 5      # Converted to 5.0
float_arr[0, 2] = "2.5"  # Converted to 2.5

str_arr[0, 0] = "hello"  # Direct string
str_arr[0, 1] = 123      # Converted to "123"
str_arr[1, 0] = 3.14     # Converted to "3.14"

bool_arr[0, 0] = True    # Direct boolean
bool_arr[0, 1] = 1       # Converted to True
bool_arr[0, 2] = 0       # Converted to False
bool_arr[1, 0] = "yes"   # Converted to True (truthy)

print(f"Array type: {int_arr.type}")  # <class 'int'>
```

#### Array Arithmetic Operations

```python
# Create sample arrays
arr1 = Array((3, 3), float)
arr2 = Array((3, 3), float)

# Fill with values
arr1.fill(10.0)
arr2.fill(2.0)

# Array-to-Array operations
result_add = arr1 + arr2    # All elements = 12.0
result_sub = arr1 - arr2    # All elements = 8.0
result_mul = arr1 * arr2    # All elements = 20.0
result_div = arr1 / arr2    # All elements = 5.0

print(f"Addition result: {result_add[0, 0]}")     # 12.0
print(f"Subtraction result: {result_sub[0, 0]}")  # 8.0
print(f"Multiplication result: {result_mul[0, 0]}") # 20.0
print(f"Division result: {result_div[0, 0]}")      # 5.0

# Scalar operations
scalar_add = arr1 + 5       # All elements = 15.0
scalar_sub = arr1 - 3       # All elements = 7.0
scalar_mul = arr1 * 2       # All elements = 20.0
scalar_div = arr1 / 4       # All elements = 2.5

print(f"Scalar addition: {scalar_add[1, 1]}")      # 15.0
print(f"Scalar multiplication: {scalar_mul[2, 2]}") # 20.0
```

#### Working with Different Array Types

```python
# Integer arrays for counting/indexing
counter = Array((5, 5), int)
counter.fill(0)
for i in range(5):
    for j in range(5):
        counter[i, j] = i * 5 + j

# String arrays for text processing
text_grid = Array((3, 3), str)
text_grid.fill("empty")
text_grid[1, 1] = "center"
text_grid[0, 0] = "top-left"
text_grid[2, 2] = "bottom-right"

# Boolean arrays for flags/masks
flags = Array((4, 4), bool)
flags.fill(False)
flags[0, 0] = True
flags[3, 3] = True

# Array comparison
arr_a = Array((2, 2), int)
arr_b = Array((2, 2), int)
arr_a.fill(42)
arr_b.fill(42)
print(arr_a == arr_b)  # True
print(arr_a.equalarray(arr_b))  # True

# Different types are never equal
int_array = Array((2, 2), int)
float_array = Array((2, 2), float)
int_array.fill(5)
float_array.fill(5.0)
print(int_array == float_array)  # False (different types)
```

### Advanced Usage

#### Complex Data Structures

```python
# Matrix storing complex objects
complex_matrix = Matrix((2, 2))
complex_matrix[0, 0] = {"user": "alice", "score": 95}
complex_matrix[0, 1] = ["item1", "item2", "item3"]
complex_matrix[1, 0] = lambda x: x * 2  # Even functions!
complex_matrix[1, 1] = {"nested": {"deep": "value"}}

# Access complex data
user_data = complex_matrix[0, 0]
print(f"User: {user_data['user']}, Score: {user_data['score']}")

items = complex_matrix[0, 1]
print(f"Items: {', '.join(items)}")

func = complex_matrix[1, 0]
print(f"Function result: {func(5)}")  # 10
```

#### Working with Large Dimensions

```python
# Create high-dimensional arrays
high_dim_matrix = Matrix((10, 10, 10, 10))  # 4D with 10,000 elements
print(f"Total elements: {high_dim_matrix.size}")  # 10000

# Efficient operations on large arrays
large_array = Array((100, 100), float)
large_array.fill(1.0)

# Copy for backup
backup_array = large_array.copy()

# Perform operations
result = large_array * 3.14159
print(f"Pi multiplication result: {result[50, 50]}")  # 3.14159
```

### Thread Safety Examples

```python
import threading
import time
from matrix import Matrix, Array

# Thread-safe matrix operations
shared_matrix = Matrix((100, 100))
results = []

def matrix_worker(thread_id):
    """Worker function demonstrating thread-safe matrix access."""
    for i in range(10):
        # Safe concurrent writes
        shared_matrix[thread_id, i] = f"Thread-{thread_id}-Item-{i}"
        
        # Safe concurrent reads
        value = shared_matrix[thread_id, i]
        results.append(f"Thread {thread_id} wrote and read: {value}")
        
        time.sleep(0.001)  # Simulate some work

# Thread-safe array operations
shared_array = Array((50, 50), int)
shared_array.fill(0)

def array_worker(thread_id):
    """Worker function demonstrating thread-safe array arithmetic."""
    for i in range(5):
        # Create a small array for operations
        local_array = Array((50, 50), int)
        local_array.fill(thread_id)
        
        # Safe arithmetic operations
        temp_result = shared_array + local_array
        results.append(f"Thread {thread_id}: Addition completed")
        
        time.sleep(0.001)

# Start multiple threads
threads = []

# Matrix threads
for i in range(5):
    thread = threading.Thread(target=matrix_worker, args=(i,))
    threads.append(thread)
    thread.start()

# Array threads
for i in range(3):
    thread = threading.Thread(target=array_worker, args=(i,))
    threads.append(thread)
    thread.start()

# Wait for all threads to complete
for thread in threads:
    thread.join()

print(f"Completed {len(results)} thread operations successfully!")

# Verify data integrity
for i in range(5):
    for j in range(10):
        expected = f"Thread-{i}-Item-{j}"
        actual = shared_matrix[i, j]
        assert actual == expected, f"Data corruption detected!"

print("Thread safety test passed - no data corruption!")
```

## API Reference

### Matrix Class

A thread-safe, multi-dimensional matrix that can store any type of data.

#### Constructor

```python
Matrix(dimensions: Tuple[int, ...])
```

**Parameters:**
- `dimensions`: Tuple of positive integers specifying the size of each dimension

**Examples:**
```python
Matrix((3, 4))      # 2D matrix: 3 rows, 4 columns
Matrix((2, 3, 4))   # 3D matrix
Matrix((10,))       # 1D matrix (vector)
```

#### Methods

##### `matrix[index] = value` (Indexing)

**Get/Set values at specific indices**

```python
# Getting values
value = matrix[1, 2]        # 2D indexing
value = matrix[0, 1, 2]     # 3D indexing

# Setting values
matrix[1, 2] = "hello"      # Any data type
matrix[0, 1, 2] = [1, 2, 3] # Lists, dicts, objects, etc.
```

##### `copy() -> Matrix`

**Create a deep copy of the matrix**

```python
original = Matrix((2, 3))
original[0, 0] = "data"
copy = original.copy()
copy[0, 0] = "modified"  # Original unchanged
```

##### `fill(value: Any) -> None`

**Fill entire matrix with a single value**

```python
matrix.fill(0)          # Fill with zeros
matrix.fill("empty")    # Fill with string
matrix.fill(None)       # Fill with None
```

##### `replace(other: Matrix) -> None`

**Replace truthy values from another matrix**

```python
matrix1 = Matrix((3, 3))
matrix1.fill("original")
matrix2 = Matrix((2, 2))
matrix2[0, 0] = "new"
matrix1.replace(matrix2)  # Only truthy values copied
```

##### `equalmatrix(other: Matrix) -> bool`

**Check if matrices are equal**

```python
if matrix1.equalmatrix(matrix2):
    print("Matrices are identical")
```

##### `get_dimension(index: int) -> int`

**Get size of a specific dimension**

```python
matrix = Matrix((3, 4, 5))
rows = matrix.get_dimension(0)     # Returns 3
cols = matrix.get_dimension(1)     # Returns 4
depth = matrix.get_dimension(2)    # Returns 5
```

#### Properties

- `dimensions: Tuple[int, ...]` - Tuple of dimensions
- `num_dimensions: int` - Number of dimensions
- `size: int` - Total number of elements

**Examples:**
```python
matrix = Matrix((3, 4, 5))
print(matrix.dimensions)      # (3, 4, 5)
print(matrix.num_dimensions)  # 3
print(matrix.size)           # 60
```

### Array Class

A thread-safe, type-enforced multi-dimensional array with arithmetic operations.

#### Constructor

```python
Array(dimensions: Tuple[int, ...], data_type: type)
```

**Parameters:**
- `dimensions`: Tuple of positive integers specifying the size of each dimension
- `data_type`: Python type that all elements must conform to

**Examples:**
```python
Array((3, 4), int)      # 2D integer array
Array((2, 3, 4), float) # 3D float array
Array((10,), str)       # 1D string array
Array((5, 5), bool)     # 2D boolean array
```

#### Arithmetic Operations

##### Addition (`+`)

```python
# Array + Array
result = arr1 + arr2    # Element-wise addition

# Array + Scalar
result = arr1 + 5       # Add 5 to all elements
result = arr1 + 3.14    # Add 3.14 to all elements
```

##### Subtraction (`-`)

```python
# Array - Array
result = arr1 - arr2    # Element-wise subtraction

# Array - Scalar
result = arr1 - 10      # Subtract 10 from all elements
```

##### Multiplication (`*`)

```python
# Array * Array
result = arr1 * arr2    # Element-wise multiplication

# Array * Scalar
result = arr1 * 2       # Multiply all elements by 2
result = arr1 * 0.5     # Multiply all elements by 0.5
```

##### Division (`/`)

```python
# Array / Array
result = arr1 / arr2    # Element-wise division

# Array / Scalar
result = arr1 / 2       # Divide all elements by 2
result = arr1 / 3.0     # Divide all elements by 3.0
```

#### Type Enforcement Examples

```python
# Integer array automatically converts values
int_arr = Array((2, 2), int)
int_arr[0, 0] = 5        # int
int_arr[0, 1] = 3.7      # Converted to 3
int_arr[1, 0] = "42"     # Converted to 42
int_arr[1, 1] = True     # Converted to 1

# String array converts everything to string
str_arr = Array((2, 2), str)
str_arr[0, 0] = "hello"  # str
str_arr[0, 1] = 123      # Converted to "123"
str_arr[1, 0] = 3.14     # Converted to "3.14"
str_arr[1, 1] = True     # Converted to "True"

# Float array for precise calculations
float_arr = Array((2, 2), float)
float_arr[0, 0] = 3.14   # float
float_arr[0, 1] = 5      # Converted to 5.0
float_arr[1, 0] = "2.5"  # Converted to 2.5
```

#### Additional Methods

##### `copy() -> Array`

**Create a deep copy of the array**

```python
original = Array((2, 3), int)
original.fill(42)
copy = original.copy()
copy[0, 0] = 99  # Original unchanged
```

##### `fill(value: Any) -> None`

**Fill entire array with a single value (with type conversion)**

```python
int_arr = Array((3, 3), int)
int_arr.fill(42)     # Fill with integer
int_arr.fill(3.7)    # Converted to 3
int_arr.fill("100")  # Converted to 100
```

##### `equalarray(other: Array) -> bool`

**Check if arrays are equal (same type, dimensions, and values)**

```python
if arr1.equalarray(arr2):
    print("Arrays are identical")
```

#### Properties

- `type: type` - The enforced data type
- All Matrix properties are inherited (`dimensions`, `num_dimensions`, `size`)

**Examples:**
```python
arr = Array((3, 4), int)
print(arr.type)          # <class 'int'>
print(arr.dimensions)    # (3, 4)
print(arr.num_dimensions) # 2
print(arr.size)          # 12
```

## Thread Safety

All operations on both Matrix and Array classes are thread-safe using `threading.RLock`. This means:

- **Concurrent Access**: Multiple threads can safely read/write to the same matrix/array simultaneously
- **Atomic Operations**: Individual element operations are atomic and consistent
- **Bulk Operation Safety**: Arithmetic operations and comparisons are performed under lock protection
- **No Data Corruption**: Thread safety prevents race conditions and data corruption

### Thread Safety Examples

```python
import threading
from matrix import Matrix, Array

# Safe concurrent matrix access
shared_matrix = Matrix((100, 100))

def worker(thread_id):
    for i in range(10):
        # Thread-safe write
        shared_matrix[thread_id, i] = f"Data-{thread_id}-{i}"
        # Thread-safe read
        value = shared_matrix[thread_id, i]

# Multiple threads accessing the same matrix safely
threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()
```

## Performance

The library uses numpy for underlying storage and vectorized operations, providing:

- **Fast Element Access**: O(1) element access and modification
- **Efficient Arithmetic**: Vectorized operations using numpy's optimized C code
- **Memory Efficient**: Optimal memory layout and data type usage
- **Vectorized Operations**: Bulk operations on entire arrays
- **Type Optimization**: Numeric arrays use native numpy dtypes for better performance

### Performance Characteristics

```python
# Large arrays are handled efficiently
large_array = Array((1000, 1000), float)  # 1M elements
large_array.fill(1.0)                      # Fast vectorized fill

# Arithmetic operations are vectorized
result = large_array * 3.14159             # Fast multiplication
sum_result = large_array + large_array     # Fast element-wise addition

# Memory usage is optimized
int_array = Array((1000, 1000), int)       # Uses numpy's int64 dtype
float_array = Array((1000, 1000), float)   # Uses numpy's float64 dtype
```

## Error Handling

The library provides comprehensive error handling with clear, helpful messages:

```python
# Dimension validation
try:
    Matrix((0, 5))  # Invalid dimension
except ValueError as e:
    print(e)  # "Dimensions must be positive integers"

# Index bounds checking
try:
    matrix = Matrix((3, 3))
    matrix[5, 2] = "value"  # Out of bounds
except IndexError as e:
    print(e)  # "Index 5 out of bounds for dimension 0 with size 3"

# Type conversion errors
try:
    arr = Array((2, 2), int)
    arr[0, 0] = "not_a_number"
except TypeError as e:
    print(e)  # "Value must be of type int"

# Arithmetic operation validation
try:
    arr1 = Array((3, 3), int)
    arr2 = Array((2, 2), int)  # Different dimensions
    result = arr1 + arr2
except ValueError as e:
    print(e)  # "Arrays must have the same dimensions"
```

## Best Practices

### Memory Management

```python
# Use appropriate data types for memory efficiency
small_ints = Array((100, 100), int)      # For integer values
floating_point = Array((100, 100), float) # For decimal values
flags = Array((100, 100), bool)          # For boolean flags

# Create copies when needed for isolation
original = Array((50, 50), float)
working_copy = original.copy()  # Safe to modify without affecting original
```

### Type Safety

```python
# Let the Array handle type conversion automatically
arr = Array((10, 10), int)
arr[0, 0] = "42"    # Automatically converted to int(42)
arr[0, 1] = 3.7     # Automatically converted to int(3)

# Check types when needed
if arr.type == int:
    print("This is an integer array")
```

### Thread Safety

```python
# Share data structures between threads safely
shared_data = Matrix((100, 100))

# No need for external locking - built-in thread safety
def process_data(thread_id):
    shared_data[thread_id, 0] = f"Result from thread {thread_id}"
    return shared_data[thread_id, 0]
```

## Examples

See `example.py` for comprehensive usage examples including:
- Basic matrix and array operations
- Thread safety demonstrations
- Performance testing
- Error handling examples
- Real-world usage patterns
