"""
Tests for processing Pipe wrapper.
"""

import multiprocessing
import pickle
import sys
from pathlib import Path

# Add project root to path
def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing import Pipe
from suitkaise.cerial import serialize, deserialize, SerializationError
from suitkaise.processing._int.pipe import PipeEndpointError


class TestResult:
    def __init__(self, name: str, passed: bool, error: str = ""):
        self.name = name
        self.passed = passed
        self.error = error


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
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
            status = f"{self.GREEN}✓ PASS{self.RESET}" if result.passed else f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")

        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")

        return failed == 0


def _assert_raises(exc_type, func):
    try:
        func()
    except exc_type:
        return
    raise AssertionError(f"Expected {exc_type.__name__} to be raised")


def test_anchor_locked_always():
    anchor, _ = Pipe.pair()
    try:
        assert anchor.locked is True
        _assert_raises(PipeEndpointError, anchor.unlock)
    finally:
        anchor.close()


def test_point_serialize_deserialize_round_trip():
    anchor, point = Pipe.pair()
    restored = None
    try:
        state = point.__serialize__()
        restored = Pipe.Point.__deserialize__(state)
        if point._conn is not None and hasattr(point._conn, "_handle"):
            point._conn._handle = None
        restored.send({"ok": True})
        result = anchor.recv()
        assert result == {"ok": True}
    finally:
        if restored is not None:
            try:
                restored.close()
            except Exception:
                pass
        point._conn = None
        anchor.close()


def test_point_cerial_round_trip():
    anchor, point = Pipe.pair()
    restored = None
    try:
        payload = serialize(point)
        restored = deserialize(payload)
        if point._conn is not None and hasattr(point._conn, "_handle"):
            point._conn._handle = None
        restored.send("hello")
        assert anchor.recv() == "hello"
    finally:
        if restored is not None:
            try:
                restored.close()
            except Exception:
                pass
        point._conn = None
        anchor.close()


def test_locked_point_serialize_raises():
    _, point = Pipe.pair()
    try:
        point.lock()
        _assert_raises(PipeEndpointError, point.__serialize__)
    finally:
        point.close()


def test_anchor_serialize_raises():
    anchor, _ = Pipe.pair()
    try:
        _assert_raises(SerializationError, lambda: serialize(anchor))
    finally:
        anchor.close()


def test_anchor_pickle_raises():
    anchor, _ = Pipe.pair()
    try:
        _assert_raises(PipeEndpointError, lambda: pickle.dumps(anchor))
    finally:
        anchor.close()


def test_point_without_peer_raises():
    point = Pipe.Point(None, False, "point")
    _assert_raises(PipeEndpointError, lambda: point.send({"ok": True}))
    _assert_raises(PipeEndpointError, point.recv)


def _child_round_trip(point, payload):
    try:
        received = point.recv()
        point.send({"received": received, "payload": payload})
    finally:
        try:
            point.close()
        except Exception:
            pass


def test_point_multiprocess_round_trip():
    ctx = multiprocessing.get_context("spawn")
    anchor, point = Pipe.pair()
    payload = {"data": [1, 2, 3], "ok": True}
    try:
        proc = ctx.Process(target=_child_round_trip, args=(point, payload))
        proc.start()
        anchor.send({"hello": "child"})
        result = anchor.recv()
        proc.join(timeout=5)
        assert proc.exitcode == 0
        assert result == {"received": {"hello": "child"}, "payload": payload}
    finally:
        anchor.close()
        point.close()


def run_all_tests():
    runner = TestRunner("Pipe Tests")
    runner.run_test("anchor locked always", test_anchor_locked_always)
    runner.run_test("point serialize/deserialize", test_point_serialize_deserialize_round_trip)
    runner.run_test("point cerial round trip", test_point_cerial_round_trip)
    runner.run_test("locked point serialize raises", test_locked_point_serialize_raises)
    runner.run_test("anchor serialize raises", test_anchor_serialize_raises)
    runner.run_test("anchor pickle raises", test_anchor_pickle_raises)
    runner.run_test("point without peer raises", test_point_without_peer_raises)
    runner.run_test("point multiprocess round trip", test_point_multiprocess_round_trip)
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
