"""Thread-safe matrix and array library for multi-dimensional data structures.

This module provides thread-safe Matrix and Array classes that support:
- Multi-dimensional data storage
- Thread-safe operations using RLock
- Type-enforced arrays with arithmetic operations
- Numpy-powered vectorized operations

Requires numpy for vectorized operations.
"""

import threading
try:
    import numpy as np
except ImportError:
    raise ImportError("numpy is required for this library. Install with: pip install numpy")

from typing import Tuple, Any, Union

class Matrix:
    """A thread-safe, multi-dimensional matrix that can store any type of data.
    
    This class provides a thread-safe wrapper around numpy arrays with support for
    arbitrary data types and dimensions. All operations are protected by RLock
    for thread safety.
    
    Attributes:
        dimensions: Tuple of dimensions for each axis
        num_dimensions: Number of dimensions
        size: Total number of elements
        matrix: Underlying numpy array storing the data
    """

    def __init__(self, dimensions: Tuple[int, ...]):
        """Initialize a new Matrix with specified dimensions.
        
        Args:
            dimensions: Tuple of positive integers specifying the size of each dimension
            
        Examples:
            >>> matrix = Matrix((3, 4))  # 2D matrix: 3 rows, 4 columns
            >>> matrix = Matrix((2, 3, 4))  # 3D matrix
            >>> matrix = Matrix((10,))  # 1D matrix (vector)
            
        Raises:
            TypeError: If dimensions is not a tuple
            ValueError: If any dimension is not a positive integer
        """
        # check if dimensions is a tuple of positive integers
        if not isinstance(dimensions, tuple):
            raise TypeError("Dimensions must be a tuple")
        
        # get size and validate dimensions
        self._size = 1
        for dimension in dimensions:
            if not isinstance(dimension, int) or dimension <= 0:
                raise ValueError("Dimensions must be positive integers")
            self._size *= dimension

        self._dimensions = dimensions
        self._num_dimensions = len(dimensions)
        
        # create matrix based on dimensions - initialize with None
        self.matrix = np.empty(dimensions, dtype=object)
        
        # init RLock for thread safety
        self._lock = threading.RLock() 

    def __getitem__(self, index: Tuple[int, ...]):
        """Get the value at the specified index.
        
        Args:
            index: Tuple of integers specifying the position in each dimension
            
        Returns:
            The value stored at the specified index
            
        Examples:
            >>> matrix = Matrix((3, 4))
            >>> matrix[1, 2] = "hello"
            >>> value = matrix[1, 2]  # Returns "hello"
            >>> matrix = Matrix((2, 3, 4))
            >>> matrix[0, 1, 2] = 42
            >>> value = matrix[0, 1, 2]  # Returns 42
            
        Raises:
            IndexError: If index dimensions don't match matrix dimensions or out of bounds
        """
        # check if index len is same as num_dimensions
        if not isinstance(index, tuple):
            index = (index,) if not hasattr(index, '__iter__') else tuple(index)
        
        if len(index) != self._num_dimensions:
            raise IndexError(f"Index must have {self._num_dimensions} dimensions, got {len(index)}")
        
        # validate index bounds
        for i, (idx, dim) in enumerate(zip(index, self._dimensions)):
            if not isinstance(idx, int) or idx < 0 or idx >= dim:
                raise IndexError(f"Index {idx} out of bounds for dimension {i} with size {dim}")
        
        # return the value at the index (thread-safe read)
        with self._lock:
            return self.matrix[index]

    def __setitem__(self, index: Tuple[int, ...], value: Any):
        """Set the value at the specified index.
        
        Args:
            index: Tuple of integers specifying the position in each dimension
            value: The value to store at the specified index
            
        Examples:
            >>> matrix = Matrix((3, 4))
            >>> matrix[1, 2] = "hello"  # Store string
            >>> matrix[0, 0] = 42       # Store integer
            >>> matrix[2, 3] = [1, 2, 3]  # Store list
            >>> matrix = Matrix((2, 3, 4))
            >>> matrix[0, 1, 2] = {"key": "value"}  # Store dictionary
            
        Raises:
            IndexError: If index dimensions don't match matrix dimensions or out of bounds
        """
        # check if index len is same as num_dimensions
        if not isinstance(index, tuple):
            index = (index,) if not hasattr(index, '__iter__') else tuple(index)
        
        if len(index) != self._num_dimensions:
            raise IndexError(f"Index must have {self._num_dimensions} dimensions, got {len(index)}")
        
        # validate index bounds
        for i, (idx, dim) in enumerate(zip(index, self._dimensions)):
            if not isinstance(idx, int) or idx < 0 or idx >= dim:
                raise IndexError(f"Index {idx} out of bounds for dimension {i} with size {dim}")
        
        # set the value at the index with RLock
        with self._lock:
            self.matrix[index] = value

    def __len__(self):
        return self._size

    def equalmatrix(self, other: "Matrix"):
        """Check if this matrix is equal to another matrix.
        
        Args:
            other: Another Matrix instance to compare with
            
        Returns:
            True if matrices have same dimensions and all elements are equal
            
        Examples:
            >>> matrix1 = Matrix((2, 2))
            >>> matrix2 = Matrix((2, 2))
            >>> matrix1[0, 0] = "hello"
            >>> matrix2[0, 0] = "hello"
            >>> matrix1.equalmatrix(matrix2)  # False (other elements are different)
            >>> matrix1.fill("test")
            >>> matrix2.fill("test")
            >>> matrix1.equalmatrix(matrix2)  # True
        """
        # check if other is same dimensions
        if not isinstance(other, Matrix):
            return False
        
        if self._dimensions != other._dimensions:
            return False
        
        # check if each index is equal using numpy vectorized operations
        with self._lock, other._lock:
            return np.array_equal(self.matrix, other.matrix)

    def __eq__(self, other: "Matrix"):
        return self.equalmatrix(other)


    def get_dimension(self, index: int):
        """Get the size of a specific dimension.
        
        Args:
            index: The dimension index (0-based)
            
        Returns:
            The size of the specified dimension
            
        Examples:
            >>> matrix = Matrix((3, 4, 5))
            >>> matrix.get_dimension(0)  # Returns 3
            >>> matrix.get_dimension(1)  # Returns 4
            >>> matrix.get_dimension(2)  # Returns 5
        """
        return self._dimensions[index]

    @property
    def dimensions(self):
        return self._dimensions

    @property
    def num_dimensions(self):
        return self._num_dimensions

    @property
    def size(self):
        return self._size

    def replace(self, other: "Matrix"):
        """Replace truthy values from another matrix into this matrix.
        
        Args:
            other: Another Matrix with dimensions that fit within this matrix
            
        Examples:
            >>> matrix1 = Matrix((3, 3))
            >>> matrix1.fill("original")
            >>> matrix2 = Matrix((2, 2))
            >>> matrix2[0, 0] = "new_value"
            >>> matrix2[1, 1] = "another_new"
            >>> matrix1.replace(matrix2)  # Replaces truthy values from matrix2
            
        Raises:
            TypeError: If other is not a Matrix
            ValueError: If other matrix dimensions exceed this matrix's dimensions
        """
        # check if other dimensions are less than or equal to self dimensions
        if not isinstance(other, Matrix):
            raise TypeError("Other must be a Matrix")
        
        if len(other._dimensions) > len(self._dimensions):
            raise ValueError("Other matrix cannot have more dimensions than self")
        
        # check if other dimensions fit within self dimensions
        for i, dim in enumerate(other._dimensions):
            if dim > self._dimensions[i]:
                raise ValueError(f"Other dimension {i} ({dim}) exceeds self dimension ({self._dimensions[i]})")
        
        # replace truthy values from other to self
        with self._lock, other._lock:
            # Create a mask for truthy values in other matrix
            other_array = other.matrix
            
            # Create slices to match dimensions
            slices = tuple(slice(0, dim) for dim in other._dimensions)
            if len(slices) < len(self._dimensions):
                slices += tuple(slice(None) for _ in range(len(self._dimensions) - len(slices)))
            
            # Get the subarray to replace
            target_subarray = self.matrix[slices]
            
            # Create mask for truthy values (handling None and falsy values)
            # First check for non-None values
            non_none_mask = other_array != None
            
            # Then check for truthy values, handling different data types
            if other_array.dtype == object:
                # For object arrays, manually check each element
                truthy_values = np.array([bool(x) if x is not None else False for x in other_array.flat])
                truthy_mask = truthy_values.reshape(other_array.shape)
            else:
                # For numeric arrays, check if not zero
                truthy_mask = other_array != 0
            
            mask = np.logical_and(non_none_mask, truthy_mask)
            
            # Apply replacement where mask is True
            if other_array.shape == target_subarray.shape:
                np.copyto(target_subarray, other_array, where=mask)
            else:
                # Handle broadcasting for smaller other matrix
                broadcast_mask = np.broadcast_to(mask, target_subarray.shape)
                broadcast_other = np.broadcast_to(other_array, target_subarray.shape)
                np.copyto(target_subarray, broadcast_other, where=broadcast_mask)
    
    def copy(self):
        """Create a deep copy of the matrix.
        
        Returns:
            A new Matrix instance with the same dimensions and data
            
        Examples:
            >>> original = Matrix((2, 3))
            >>> original[0, 0] = "data"
            >>> copy = original.copy()
            >>> copy[0, 0] = "modified"
            >>> original[0, 0]  # Still "data" - independent copies
        """
        new_matrix = Matrix(self._dimensions)
        with self._lock:
            new_matrix.matrix = self.matrix.copy()
        return new_matrix
    
    def fill(self, value: Any):
        """Fill the entire matrix with a single value.
        
        Args:
            value: The value to fill all positions with
            
        Examples:
            >>> matrix = Matrix((3, 3))
            >>> matrix.fill(0)     # Fill with zeros
            >>> matrix.fill("empty")  # Fill with string
            >>> matrix.fill(None)  # Fill with None
            >>> matrix[1, 1]  # Returns the fill value
        """
        with self._lock:
            self.matrix.fill(value)
    
    def __repr__(self):
        return f"Matrix({self.dimensions})"
    
    def __str__(self):
        return f"Matrix({self.dimensions})"





class Array(Matrix):
    """A thread-safe, type-enforced multi-dimensional array with arithmetic operations.
    
    This class extends Matrix to enforce a single data type across all elements
    and provides arithmetic operations (+, -, *, /) that work with both other
    Arrays and scalar values.
    
    Attributes:
        data_type: The enforced data type for all elements
        All Matrix attributes are inherited
    """


    def __init__(self, dimensions: Tuple[int, ...], data_type: type):
        """Initialize a new type-enforced Array with specified dimensions.
        
        Args:
            dimensions: Tuple of positive integers specifying the size of each dimension
            data_type: The Python type that all elements must conform to
            
        Examples:
            >>> arr = Array((3, 4), int)     # 2D integer array
            >>> arr = Array((2, 3, 4), float)  # 3D float array
            >>> arr = Array((10,), str)      # 1D string array
            >>> arr = Array((5, 5), bool)    # 2D boolean array
            
        Raises:
            TypeError: If dimensions is not a tuple
            ValueError: If any dimension is not a positive integer
        """
        super().__init__(dimensions)
        self.data_type = data_type
        # Initialize with zeros of the specified type
        if data_type in (int, float, complex):
            self.matrix = np.zeros(dimensions, dtype=data_type)
        else:
            # For other types, keep object array but validate type on set
            self.matrix = np.full(dimensions, None, dtype=object)

    def __getitem__(self, index: Tuple[int, ...]):
        # Use parent implementation with thread safety
        return super().__getitem__(index)


    def __setitem__(self, index: Tuple[int, ...], value: Any):
        """Set the value at the specified index with type enforcement.
        
        Args:
            index: Tuple of integers specifying the position in each dimension
            value: The value to store (will be converted to array's data type)
            
        Examples:
            >>> arr = Array((2, 2), int)
            >>> arr[0, 0] = 5      # Store integer
            >>> arr[0, 1] = 3.7    # Converted to int(3)
            >>> arr[1, 0] = "42"   # Converted to int(42)
            
            >>> str_arr = Array((2, 2), str)
            >>> str_arr[0, 0] = "hello"
            >>> str_arr[0, 1] = 123  # Converted to "123"
            
        Raises:
            TypeError: If value cannot be converted to the array's data type
            IndexError: If index is out of bounds
        """
        # ensure value is of the specified type
        if not isinstance(value, self.data_type):
            try:
                # Try to convert to the specified type
                value = self.data_type(value)
            except (ValueError, TypeError):
                raise TypeError(f"Value must be of type {self.data_type.__name__}")
        
        # Use parent implementation with thread safety
        super().__setitem__(index, value)

    def __add__(self, other: Union["Array", int, float, complex]):
        """Add another Array or scalar value to this Array.
        
        Args:
            other: Another Array with same dimensions and type, or a scalar value
            
        Returns:
            New Array containing the element-wise sum
            
        Examples:
            >>> arr1 = Array((2, 2), int)
            >>> arr1.fill(5)
            >>> arr2 = Array((2, 2), int)
            >>> arr2.fill(3)
            >>> result = arr1 + arr2  # All elements = 8
            
            >>> scalar_result = arr1 + 10  # All elements = 15
            
        Raises:
            TypeError: If other is not Array or numeric type, or types don't match
            ValueError: If Array dimensions don't match
        """
        # Handle scalar addition
        if isinstance(other, (int, float, complex)):
            if not isinstance(other, self.data_type):
                other = self.data_type(other)
            
            result = Array(self._dimensions, self.data_type)
            with self._lock:
                result.matrix = self.matrix + other
            return result
        
        # Handle Array addition
        if not isinstance(other, Array):
            raise TypeError("Can only add Array or numeric types")
        
        if self.data_type != other.data_type:
            raise TypeError("Arrays must have the same data type")
        
        if self._dimensions != other._dimensions:
            raise ValueError("Arrays must have the same dimensions")
        
        # add each index using numpy vectorized operations
        result = Array(self._dimensions, self.data_type)
        with self._lock, other._lock:
            result.matrix = self.matrix + other.matrix
        return result

    def __sub__(self, other: Union["Array", int, float, complex]):
        """Subtract another Array or scalar value from this Array.
        
        Args:
            other: Another Array with same dimensions and type, or a scalar value
            
        Returns:
            New Array containing the element-wise difference
            
        Examples:
            >>> arr1 = Array((2, 2), int)
            >>> arr1.fill(10)
            >>> arr2 = Array((2, 2), int)
            >>> arr2.fill(3)
            >>> result = arr1 - arr2  # All elements = 7
            
            >>> scalar_result = arr1 - 5  # All elements = 5
            
        Raises:
            TypeError: If other is not Array or numeric type, or types don't match
            ValueError: If Array dimensions don't match
        """
        # Handle scalar subtraction
        if isinstance(other, (int, float, complex)):
            if not isinstance(other, self.data_type):
                other = self.data_type(other)
            
            result = Array(self._dimensions, self.data_type)
            with self._lock:
                result.matrix = self.matrix - other
            return result
        
        # Handle Array subtraction
        if not isinstance(other, Array):
            raise TypeError("Can only subtract Array or numeric types")
        
        if self.data_type != other.data_type:
            raise TypeError("Arrays must have the same data type")
        
        if self._dimensions != other._dimensions:
            raise ValueError("Arrays must have the same dimensions")
        
        # subtract each index using numpy vectorized operations
        result = Array(self._dimensions, self.data_type)
        with self._lock, other._lock:
            result.matrix = self.matrix - other.matrix
        return result

    def __mul__(self, other: Union["Array", int, float, complex]):
        """Multiply this Array by another Array or scalar value.
        
        Args:
            other: Another Array with same dimensions and type, or a scalar value
            
        Returns:
            New Array containing the element-wise product
            
        Examples:
            >>> arr1 = Array((2, 2), int)
            >>> arr1.fill(4)
            >>> arr2 = Array((2, 2), int)
            >>> arr2.fill(3)
            >>> result = arr1 * arr2  # All elements = 12
            
            >>> scalar_result = arr1 * 2  # All elements = 8
            
        Raises:
            TypeError: If other is not Array or numeric type, or types don't match
            ValueError: If Array dimensions don't match
        """
        # Handle scalar multiplication
        if isinstance(other, (int, float, complex)):
            if not isinstance(other, self.data_type):
                other = self.data_type(other)
            
            result = Array(self._dimensions, self.data_type)
            with self._lock:
                result.matrix = self.matrix * other
            return result
        
        # Handle Array multiplication
        if not isinstance(other, Array):
            raise TypeError("Can only multiply Array or numeric types")
        
        if self.data_type != other.data_type:
            raise TypeError("Arrays must have the same data type")
        
        if self._dimensions != other._dimensions:
            raise ValueError("Arrays must have the same dimensions")
        
        # multiply each index using numpy vectorized operations
        result = Array(self._dimensions, self.data_type)
        with self._lock, other._lock:
            result.matrix = self.matrix * other.matrix
        return result

    def __truediv__(self, other: Union["Array", int, float, complex]):
        """Divide this Array by another Array or scalar value.
        
        Args:
            other: Another Array with same dimensions and type, or a scalar value
            
        Returns:
            New Array containing the element-wise quotient
            
        Examples:
            >>> arr1 = Array((2, 2), float)
            >>> arr1.fill(12.0)
            >>> arr2 = Array((2, 2), float)
            >>> arr2.fill(3.0)
            >>> result = arr1 / arr2  # All elements = 4.0
            
            >>> scalar_result = arr1 / 2  # All elements = 6.0
            
        Raises:
            TypeError: If other is not Array or numeric type, or types don't match
            ValueError: If Array dimensions don't match
            ZeroDivisionError: If division by zero occurs
        """
        # Handle scalar division
        if isinstance(other, (int, float, complex)):
            if other == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            
            if not isinstance(other, self.data_type):
                other = self.data_type(other)
            
            result = Array(self._dimensions, self.data_type)
            with self._lock:
                result.matrix = self.matrix / other
            return result
        
        # Handle Array division
        if not isinstance(other, Array):
            raise TypeError("Can only divide Array or numeric types")
        
        if self.data_type != other.data_type:
            raise TypeError("Arrays must have the same data type")
        
        if self._dimensions != other._dimensions:
            raise ValueError("Arrays must have the same dimensions")
        
        # Check for division by zero
        with other._lock:
            if np.any(other.matrix == 0):
                raise ZeroDivisionError("Cannot divide by zero")
        
        # divide each index using numpy vectorized operations
        result = Array(self._dimensions, self.data_type)
        with self._lock, other._lock:
            result.matrix = self.matrix / other.matrix
        return result
    

    def __eq__(self, other: "Array"):
        return self.equalarray(other)

    def equalarray(self, other: "Array"):
        """Check if this Array is equal to another Array.
        
        Args:
            other: Another Array instance to compare with
            
        Returns:
            True if arrays have same dimensions, type, and all elements are equal
            
        Examples:
            >>> arr1 = Array((2, 2), int)
            >>> arr2 = Array((2, 2), int)
            >>> arr1.fill(5)
            >>> arr2.fill(5)
            >>> arr1.equalarray(arr2)  # True
            
            >>> arr3 = Array((2, 2), float)  # Different type
            >>> arr1.equalarray(arr3)  # False
        """
        # check if other is same dimensions and same type
        if not isinstance(other, Array):
            return False
        
        if self.data_type != other.data_type:
            return False
        
        if self._dimensions != other._dimensions:
            return False
        
        # check if each index is equal using numpy vectorized operations
        with self._lock, other._lock:
            return np.array_equal(self.matrix, other.matrix)

    def __repr__(self):
        return f"Array({self.dimensions}, {self.data_type.__name__})"

    def __str__(self):
        return f"Array({self.dimensions}, {self.data_type.__name__})"
    
    @property
    def type(self):
        """Get the data type of the array."""
        return self.data_type
    
    def copy(self):
        """Create a deep copy of the array.
        
        Returns:
            A new Array instance with the same dimensions, type, and data
            
        Examples:
            >>> original = Array((2, 3), int)
            >>> original.fill(42)
            >>> copy = original.copy()
            >>> copy[0, 0] = 99
            >>> original[0, 0]  # Still 42 - independent copies
        """
        new_array = Array(self._dimensions, self.data_type)
        with self._lock:
            new_array.matrix = self.matrix.copy()
        return new_array
    
    def fill(self, value: Any):
        """Fill the entire array with a single value.
        
        Args:
            value: The value to fill all positions with (will be converted to array's type)
            
        Examples:
            >>> arr = Array((3, 3), int)
            >>> arr.fill(42)     # Fill with integer
            >>> arr.fill(3.7)    # Converted to int(3)
            
            >>> str_arr = Array((2, 2), str)
            >>> str_arr.fill("hello")  # Fill with string
            >>> str_arr.fill(123)      # Converted to "123"
            
        Raises:
            TypeError: If value cannot be converted to the array's data type
        """
        if not isinstance(value, self.data_type):
            try:
                value = self.data_type(value)
            except (ValueError, TypeError):
                raise TypeError(f"Value must be of type {self.data_type.__name__}")
        
        with self._lock:
            self.matrix.fill(value)