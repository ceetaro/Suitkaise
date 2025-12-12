# sktest

sktest is a module designed to quickly and easily test your code. it is designed like:

```python
from suitkaise import sktest

@sktest.test(title="Test Function", description="Test the function", expected_results=[True])
def test_function():
    return True

# sktest.test will then assert that the function returns True and display the test with title, description, and expected results. it will also be formatted and track what tests passed and what tests failed.
```

## Core Features

- Quick and easy testing
- Easy to use
- Easy to understand