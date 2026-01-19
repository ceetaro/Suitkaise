"""
Cerial IR JSON Conversion Tests
"""

import sys
import json

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import cerial


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
# IR JSON Tests
# =============================================================================

def _find_marker(node, marker: str) -> bool:
    if isinstance(node, dict):
        if node.get("__cerial_json__") == marker:
            return True
        return any(_find_marker(v, marker) for v in node.values())
    if isinstance(node, list):
        return any(_find_marker(item, marker) for item in node)
    return False


def _find_cerial_type(node, cerial_type: str) -> bool:
    if isinstance(node, dict):
        if node.get("__cerial_type__") == cerial_type:
            return True
        return any(_find_cerial_type(v, cerial_type) for v in node.values())
    if isinstance(node, list):
        return any(_find_cerial_type(item, cerial_type) for item in node)
    return False


def test_ir_to_json_output_is_valid():
    """ir_to_json should return valid JSON text."""
    obj = {"a": {1, 2}, 3: b"hi", "t": (1, 2), "c": complex(1, 2)}
    ir = cerial.serialize_ir(obj)
    json_text = cerial.ir_to_json(ir)
    
    parsed = json.loads(json_text)
    assert isinstance(parsed, dict), "JSON output should parse to dict"


def test_to_json_matches_ir_path():
    """to_json should produce valid JSON without manual IR step."""
    obj = {"a": {1, 2}, 3: b"hi", "t": (1, 2), "c": complex(1, 2)}
    json_text = cerial.to_json(obj)
    parsed = json.loads(json_text)
    assert isinstance(parsed, dict), "JSON output should parse to dict"


def test_ir_to_jsonable_contains_markers():
    """ir_to_jsonable should tag non-JSON-native structures."""
    obj = {"a": {1, 2}, 3: b"hi", "t": (1, 2), "c": complex(1, 2)}
    ir = cerial.serialize_ir(obj)
    jsonable = cerial.ir_to_jsonable(ir)
    
    assert _find_marker(jsonable, "dict") or _find_cerial_type(jsonable, "dict"), \
        "Should represent dicts in JSON output"
    assert _find_marker(jsonable, "bytes"), "Should mark bytes values"
    assert _find_marker(jsonable, "set") or _find_cerial_type(jsonable, "set"), \
        "Should represent sets in JSON output"
    assert _find_marker(jsonable, "tuple") or _find_cerial_type(jsonable, "tuple"), \
        "Should represent tuples in JSON output"
    assert _find_marker(jsonable, "complex") or _find_cerial_type(jsonable, "complex"), \
        "Should represent complex numbers in JSON output"


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    runner = TestRunner("Cerial IR JSON Tests")
    runner.run_test("JSON output is valid", test_ir_to_json_output_is_valid)
    runner.run_test("to_json output is valid", test_to_json_matches_ir_path)
    runner.run_test("JSON markers present", test_ir_to_jsonable_contains_markers)
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
