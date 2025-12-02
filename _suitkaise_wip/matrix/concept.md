```python
from matrix import Matrix, Array

matrix = Matrix((3, 4, 5, 6))

matrix[0, 0, 0, 0] = "hello"
matrix[1, 1, 1, 1] = 3.14
matrix[2, 2, 2, 2] = 8

# __eq__
if matrix1 == matrix2:
    print("matrix1 and matrix2 are equal")
else:
    print("matrix1 and matrix2 are not equal")



array = Array((3, 4, 5, 6), int)

array[0, 0, 0, 0] = 1
array[1, 1, 1, 1] = 2
array[2, 2, 2, 2] = 3

array2 = array.copy()

array3 = array + array2
array4 = array * array2
array5 = array / array2
array6 = array - array2

array7 = array.replace(array2)

```