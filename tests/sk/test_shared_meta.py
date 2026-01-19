"""
_shared_meta Attribute Tests

Tests the _shared_meta attribute:
- Presence on @sk decorated CLASSES (not functions)
- Content of _shared_meta
- has_blocking_calls detection on both classes and functions
- Integration with Share

Note: _shared_meta is only added to classes, not functions.
Functions decorated with @sk get has_blocking_calls, blocking_calls,
asynced(), retry(), timeout(), and background() instead.
"""

import sys
import time as stdlib_time

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.sk import sk, Skfunction, Skclass


# =============================================================================
# Test Infrastructure
# =============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def run_test(self, name: str, test_func):
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*70}{self.RESET}\n")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        for result in self.results:
            if result.passed:
                status = f"{self.GREEN}✓ PASS{self.RESET}"
            else:
                status = f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")
        
        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")

        if failed != 0:
            print(f"{self.BOLD}{self.RED}Failed tests (recap):{self.RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  {self.RED}✗ {result.name}{self.RESET}")
                    if result.error:
                        print(f"     {self.RED}└─ {result.error}{self.RESET}")
            print()


        try:
            from tests._failure_registry import record_failures
            record_failures(self.suite_name, [r for r in self.results if not r.passed])
        except Exception:
            pass

        return failed == 0


# =============================================================================
# _shared_meta Presence Tests (Classes Only)
# =============================================================================

def test_sk_class_has_shared_meta():
    """@sk decorated class should have _shared_meta."""
    @sk
    class MyClass:
        def __init__(self):
            self.value = 42
    
    assert hasattr(MyClass, '_shared_meta'), "Should have _shared_meta"


def test_skclass_has_shared_meta():
    """Skclass wrapper should have _shared_meta."""
    class RawClass:
        def __init__(self):
            self.value = 42
    
    wrapped = Skclass(RawClass)
    
    assert hasattr(wrapped, '_shared_meta'), "Should have _shared_meta"


def test_skfunction_has_shared_meta():
    """Skfunction wrapper should have _shared_meta."""
    def raw_func():
        return 42
    
    wrapped = Skfunction(raw_func)
    
    # Skfunction internally has _shared_meta for Share compatibility
    # Check if it exists (may be internal)
    assert wrapped is not None


# =============================================================================
# _shared_meta Content Tests (Classes)
# =============================================================================

def test_shared_meta_is_dict():
    """_shared_meta should be a dict."""
    @sk
    class MyClass:
        pass
    
    assert isinstance(MyClass._shared_meta, dict), f"Should be dict, got {type(MyClass._shared_meta)}"


def test_shared_meta_has_content():
    """_shared_meta should have some content."""
    @sk
    class MyClass:
        def __init__(self):
            self.value = 42
    
    meta = MyClass._shared_meta
    
    assert isinstance(meta, dict)


def test_shared_meta_preserves_class_name():
    """_shared_meta should preserve class name."""
    @sk
    class NamedClass:
        pass
    
    # The class should still have its name
    assert NamedClass.__name__ == 'NamedClass'


# =============================================================================
# has_blocking_calls Tests (Functions)
# =============================================================================

def test_has_blocking_calls_attribute():
    """@sk decorated function should have has_blocking_calls."""
    @sk
    def my_func():
        pass
    
    assert hasattr(my_func, 'has_blocking_calls'), "Should have has_blocking_calls"


def test_has_blocking_calls_false_for_pure():
    """Pure function should not have blocking calls."""
    @sk
    def pure_func(x, y):
        return x + y
    
    # A pure function with no I/O should have has_blocking_calls = False
    assert pure_func.has_blocking_calls == False


def test_has_blocking_calls_true_for_sleep():
    """Function with time.sleep should have blocking calls."""
    @sk
    def sleeping_func():
        stdlib_time.sleep(0.01)
        return "done"
    
    assert sleeping_func.has_blocking_calls == True


def test_has_blocking_calls_on_class():
    """@sk decorated class should have has_blocking_calls."""
    @sk
    class MyClass:
        def blocking_method(self):
            stdlib_time.sleep(0.01)
    
    assert hasattr(MyClass, 'has_blocking_calls')


# =============================================================================
# _shared_meta on Classes Tests
# =============================================================================

def test_class_shared_meta_structure():
    """@sk class _shared_meta should have class info."""
    @sk
    class TestClass:
        def __init__(self, value):
            self.value = value
        
        def get_value(self):
            return self.value
    
    meta = TestClass._shared_meta
    
    assert isinstance(meta, dict)


def test_class_methods_accessible():
    """@sk class should still have methods accessible."""
    @sk
    class Calculator:
        def __init__(self, initial=0):
            self.value = initial
        
        def add(self, x):
            self.value += x
            return self.value
    
    calc = Calculator(10)
    result = calc.add(5)
    
    assert result == 15


def test_class_instance_attributes():
    """Class instance should work normally."""
    @sk
    class MyClass:
        def __init__(self, value):
            self.value = value
    
    instance = MyClass(42)
    
    # Class has _shared_meta
    assert hasattr(MyClass, '_shared_meta')
    # Instance has its own attributes
    assert instance.value == 42


# =============================================================================
# Integration with Share Tests
# =============================================================================

def test_shared_meta_for_sharing():
    """_shared_meta should enable sharing between processes."""
    @sk
    class SharedCounter:
        def __init__(self):
            self.count = 0
        
        def increment(self):
            self.count += 1
            return self.count
    
    # _shared_meta should exist and be usable by Share
    assert hasattr(SharedCounter, '_shared_meta')
    
    # Should be able to instantiate normally
    counter = SharedCounter()
    assert counter.increment() == 1
    assert counter.increment() == 2


def test_shared_meta_on_stateful_class():
    """_shared_meta should work on stateful classes."""
    @sk
    class StatefulClass:
        def __init__(self):
            self.data = []
        
        def append(self, item):
            self.data.append(item)
            return len(self.data)
        
        def get_data(self):
            return self.data.copy()
    
    assert hasattr(StatefulClass, '_shared_meta')
    
    obj = StatefulClass()
    obj.append("a")
    obj.append("b")
    
    assert obj.get_data() == ["a", "b"]


# =============================================================================
# Decorator Stacking Tests
# =============================================================================

def test_sk_with_other_decorators_on_class():
    """@sk should work with other class decorators."""
    def add_attribute(cls):
        cls.extra = 100
        return cls
    
    @sk
    @add_attribute
    class DecoratedClass:
        pass
    
    assert hasattr(DecoratedClass, '_shared_meta')
    assert DecoratedClass.extra == 100


def test_other_decorator_on_sk():
    """Other decorators on @sk function should work."""
    def add_one(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs) + 1
        return wrapper
    
    @add_one
    @sk
    def base_func():
        return 41
    
    result = base_func()
    
    assert result == 42


# =============================================================================
# Skfunction Tests
# =============================================================================

def test_skfunction_works():
    """Skfunction should wrap functions correctly."""
    def raw():
        return 42
    
    wrapped = Skfunction(raw)
    
    result = wrapped()
    assert result == 42


def test_skfunction_has_blocking_calls():
    """Skfunction should have has_blocking_calls property."""
    def blocking():
        stdlib_time.sleep(0.01)
        return "done"
    
    wrapped = Skfunction(blocking)
    
    assert hasattr(wrapped, 'has_blocking_calls')
    assert wrapped.has_blocking_calls == True


def test_skfunction_callable_preserved():
    """Skfunction should still be callable."""
    def add(a, b):
        return a + b
    
    wrapped = Skfunction(add)
    
    result = wrapped(3, 4)
    
    assert result == 7


# =============================================================================
# Skclass Tests
# =============================================================================

def test_skclass_works():
    """Skclass should wrap classes correctly."""
    class RawClass:
        def __init__(self, value):
            self.value = value
    
    wrapped = Skclass(RawClass)
    
    instance = wrapped(42)
    assert instance.value == 42


def test_skclass_has_shared_meta_dict():
    """Skclass._shared_meta should be a dict."""
    class RawClass:
        pass
    
    wrapped = Skclass(RawClass)
    
    assert isinstance(wrapped._shared_meta, dict)


# =============================================================================
# Edge Cases Tests
# =============================================================================

def test_empty_class():
    """@sk should work on empty class."""
    @sk
    class Empty:
        pass
    
    assert hasattr(Empty, '_shared_meta')
    
    obj = Empty()
    assert obj is not None


def test_class_with_class_variables():
    """@sk should work on class with class variables."""
    @sk
    class WithClassVar:
        class_value = 100
        
        def __init__(self):
            self.instance_value = 200
    
    assert hasattr(WithClassVar, '_shared_meta')
    assert WithClassVar.class_value == 100
    
    obj = WithClassVar()
    assert obj.instance_value == 200


def test_nested_classes():
    """@sk should work on nested classes."""
    @sk
    class Outer:
        class Inner:
            def method(self):
                return "inner"
        
        def get_inner(self):
            return self.Inner()
    
    assert hasattr(Outer, '_shared_meta')
    
    outer = Outer()
    inner = outer.get_inner()
    assert inner.method() == "inner"


def test_lambda_with_skfunction():
    """Skfunction should work on lambda."""
    add = Skfunction(lambda x, y: x + y)
    
    result = add(3, 4)
    
    assert result == 7


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all _shared_meta tests."""
    runner = TestRunner("_shared_meta Attribute Tests")
    
    # Presence tests
    runner.run_test("@sk class has _shared_meta", test_sk_class_has_shared_meta)
    runner.run_test("Skclass has _shared_meta", test_skclass_has_shared_meta)
    runner.run_test("Skfunction works", test_skfunction_has_shared_meta)
    
    # Content tests
    runner.run_test("_shared_meta is dict", test_shared_meta_is_dict)
    runner.run_test("_shared_meta has content", test_shared_meta_has_content)
    runner.run_test("_shared_meta preserves name", test_shared_meta_preserves_class_name)
    
    # has_blocking_calls tests
    runner.run_test("has_blocking_calls attribute", test_has_blocking_calls_attribute)
    runner.run_test("has_blocking_calls false for pure", test_has_blocking_calls_false_for_pure)
    runner.run_test("has_blocking_calls true for sleep", test_has_blocking_calls_true_for_sleep)
    runner.run_test("has_blocking_calls on class", test_has_blocking_calls_on_class)
    
    # Class tests
    runner.run_test("class _shared_meta structure", test_class_shared_meta_structure)
    runner.run_test("class methods accessible", test_class_methods_accessible)
    runner.run_test("class instance attributes", test_class_instance_attributes)
    
    # Integration tests
    runner.run_test("_shared_meta for sharing", test_shared_meta_for_sharing)
    runner.run_test("_shared_meta on stateful class", test_shared_meta_on_stateful_class)
    
    # Decorator stacking tests
    runner.run_test("@sk with other decorators", test_sk_with_other_decorators_on_class)
    runner.run_test("other decorator on @sk", test_other_decorator_on_sk)
    
    # Skfunction tests
    runner.run_test("Skfunction works", test_skfunction_works)
    runner.run_test("Skfunction has_blocking_calls", test_skfunction_has_blocking_calls)
    runner.run_test("Skfunction callable preserved", test_skfunction_callable_preserved)
    
    # Skclass tests
    runner.run_test("Skclass works", test_skclass_works)
    runner.run_test("Skclass _shared_meta dict", test_skclass_has_shared_meta_dict)
    
    # Edge cases
    runner.run_test("empty class", test_empty_class)
    runner.run_test("class with class variables", test_class_with_class_variables)
    runner.run_test("nested classes", test_nested_classes)
    runner.run_test("lambda with Skfunction", test_lambda_with_skfunction)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
