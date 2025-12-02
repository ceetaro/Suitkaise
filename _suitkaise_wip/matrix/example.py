#!/usr/bin/env python3
"""Example usage of the thread-safe Matrix and Array classes."""

from matrix import Matrix, Array
import threading
import time


def test_matrix():
    """Test basic Matrix functionality."""
    print("=== Testing Matrix ===")
    
    # Create a 3D matrix
    matrix = Matrix((2, 3, 4))
    print(f"Created matrix: {matrix}")
    print(f"Dimensions: {matrix.dimensions}")
    print(f"Size: {matrix.size}")
    
    # Set and get values
    matrix[0, 1, 2] = "Hello"
    matrix[1, 2, 3] = 42
    
    print(f"matrix[0, 1, 2] = {matrix[0, 1, 2]}")
    print(f"matrix[1, 2, 3] = {matrix[1, 2, 3]}")
    
    # Test copy
    matrix_copy = matrix.copy()
    print(f"Copy created: {matrix_copy}")
    print(f"Are equal: {matrix == matrix_copy}")


def test_array():
    """Test basic Array functionality."""
    print("\n=== Testing Array ===")
    
    # Create integer arrays
    arr1 = Array((2, 3), int)
    arr2 = Array((2, 3), int)
    print(f"Created arrays: {arr1}")
    
    # Fill with values
    arr1.fill(5)
    arr2.fill(3)
    
    print(f"arr1 filled with 5")
    print(f"arr2 filled with 3")
    
    # Test arithmetic operations
    result_add = arr1 + arr2
    result_sub = arr1 - arr2
    result_mul = arr1 * arr2
    result_div = arr1 / arr2
    
    print(f"arr1 + arr2 = Array with all values: {result_add[0, 0]}")
    print(f"arr1 - arr2 = Array with all values: {result_sub[0, 0]}")
    print(f"arr1 * arr2 = Array with all values: {result_mul[0, 0]}")
    print(f"arr1 / arr2 = Array with all values: {result_div[0, 0]}")
    
    # Test scalar operations
    scalar_result = arr1 + 10
    print(f"arr1 + 10 = Array with all values: {scalar_result[0, 0]}")


def test_thread_safety():
    """Test thread safety of operations."""
    print("\n=== Testing Thread Safety ===")
    
    matrix = Matrix((100, 100))
    results = []
    
    def worker(thread_id):
        """Worker function for threading test."""
        for i in range(10):
            try:
                matrix[thread_id, i] = f"Thread-{thread_id}-{i}"
                value = matrix[thread_id, i]
                results.append(f"Thread {thread_id}: Set and got {value}")
                time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                results.append(f"Thread {thread_id}: Error - {e}")
    
    # Create and start threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"Completed {len(results)} thread operations")
    # Print first few results as example
    for result in results[:10]:
        print(f"  {result}")


if __name__ == "__main__":
    try:
        test_matrix()
        test_array()
        test_thread_safety()
        print("\n=== All tests completed successfully! ===")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
