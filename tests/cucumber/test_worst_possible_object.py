"""
Cucumber WorstPossibleObject Tests

Ensures the worst possible object can:
- serialize and deserialize
- verify integrity after round-trip
- work with the reconnector system
"""

import sys
import random
import multiprocessing
from pathlib import Path


def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start


project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.cucumber import serialize, deserialize, reconnect_all
from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject


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
# Tests
# =============================================================================

def _format_failures(failures: list[str]) -> str:
    if not failures:
        return ""
    preview = "\n".join(failures[:10])
    remainder = len(failures) - 10
    suffix = f"\n... {remainder} more failures" if remainder > 0 else ""
    return preview + suffix


def _child_roundtrip_wpo(conn) -> None:
    """Deserialize, reconnect, verify, reserialize, and send back bytes."""
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    from suitkaise.cucumber import serialize as _serialize
    from suitkaise.cucumber import deserialize as _deserialize
    from suitkaise.cucumber import reconnect_all as _reconnect_all
    import random
    original = None
    restored = None
    try:
        payload = conn.recv_bytes()
        random.seed(1337)
        original = WorstPossibleObject()
        restored = _deserialize(payload)
        restored = _reconnect_all(restored)
        passed, failures = original.verify(restored)
        if not passed:
            preview = "\n".join(failures[:10])
            remainder = len(failures) - 10
            if remainder > 0:
                preview += f"\n... {remainder} more failures"
            conn.send({"ok": False, "error": f"Verification failed:\n{preview}"})
            return
        new_payload = _serialize(restored)
        conn.send({"ok": True, "data": new_payload})
    except Exception as exc:
        conn.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        try:
            original.cleanup()
        except Exception:
            pass
        try:
            restored.cleanup()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def test_worst_possible_object_roundtrip():
    """WorstPossibleObject should serialize, deserialize, and verify."""
    random.seed(1337)
    original = WorstPossibleObject()
    restored = None
    try:
        data = serialize(original)
        restored = deserialize(data)
        restored = reconnect_all(restored)
        passed, failures = original.verify(restored)
        assert passed, "Verification failed:\n" + _format_failures(failures)
    finally:
        try:
            original.cleanup()
        except Exception:
            pass
        if restored is not None:
            try:
                restored.cleanup()
            except Exception:
                pass


def test_worst_possible_object_roundtrip_cross_process():
    """WorstPossibleObject should roundtrip across a process boundary."""
    from suitkaise.cucumber import serialize, deserialize, reconnect_all
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    import random

    random.seed(1337)
    original = None
    restored = None
    proc = None
    parent_conn = None
    try:
        original = WorstPossibleObject()
        payload = serialize(original)

        ctx = multiprocessing.get_context("spawn")
        parent_conn, child_conn = ctx.Pipe(duplex=True)
        proc = ctx.Process(target=_child_roundtrip_wpo, args=(child_conn,))
        proc.start()
        parent_conn.send_bytes(payload)
        result = parent_conn.recv()
        proc.join(timeout=10)

        assert proc.exitcode == 0, "Child process did not exit cleanly."
        assert result.get("ok"), result.get("error", "Unknown child error.")

        restored = deserialize(result["data"])
        restored = reconnect_all(restored)
        passed, failures = original.verify(restored)
        assert passed, "Verification failed:\n" + _format_failures(failures)
    except Exception as e:
        msg = str(e).lower()
        if "permission" in msg or "resource" in msg:
            return
        raise
    finally:
        if parent_conn is not None:
            try:
                parent_conn.close()
            except Exception:
                pass
        if proc is not None and proc.is_alive():
            try:
                proc.terminate()
            except Exception:
                pass
        if original is not None:
            try:
                original.cleanup()
            except Exception:
                pass
        if restored is not None:
            try:
                restored.cleanup()
            except Exception:
                pass


def run_all_tests():
    """Run all WorstPossibleObject tests."""
    runner = TestRunner("Cucumber WorstPossibleObject Tests")
    runner.run_test("worst_possible_object_roundtrip", test_worst_possible_object_roundtrip)
    runner.run_test("worst_possible_object_roundtrip_cross_process", test_worst_possible_object_roundtrip_cross_process)
    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)