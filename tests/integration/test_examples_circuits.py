"""
Integration Tests for circuits Examples

Validates the examples in suitkaise/_docs_copy/circuits/examples.md
with detailed assertions.
"""

import asyncio
import json
import threading
import sys
from queue import Queue
from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import Circuit, BreakingCircuit


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
            status = f"{self.GREEN}✓ PASS{self.RESET}" if result.passed else f"{self.RED}✗ FAIL{self.RESET}"
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

def test_circuit_basic_short() -> None:
    rate_limiter = Circuit(
        num_shorts_to_trip=3,
        sleep_time_after_trip=0.0,
        backoff_factor=1.5,
        max_sleep_time=1.0,
    )
    trips = 0
    for _ in range(7):
        if rate_limiter.short():
            trips += 1
    assert trips >= 2
    assert rate_limiter.total_trips >= 2


def test_breaking_circuit() -> None:
    circ = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=0.0)
    for _ in range(3):
        circ.short()
    assert circ.broken is True


def test_dual_circuit_usage() -> None:
    outer = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0.0)
    inner = BreakingCircuit(num_shorts_to_trip=2, sleep_time_after_trip=0.0)
    items = [1, 2, 3]
    failures = 0
    for item in items:
        inner.reset()
        while not inner.broken:
            try:
                if item % 2 == 0:
                    raise RuntimeError("fail")
                break
            except RuntimeError:
                inner.short()
        if inner.broken:
            failures += 1
            outer.short()
    assert failures >= 1


def test_async_circuit_short() -> None:
    circ = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0.01)

    async def main():
        await circ.short.asynced()()
        await circ.short.asynced()()
        assert circ.total_trips >= 1

    asyncio.run(main())


def test_shared_circuit_multithreading() -> None:
    class FatalError(RuntimeError):
        pass

    class TransientError(RuntimeError):
        pass

    circuit = BreakingCircuit(num_shorts_to_trip=2, sleep_time_after_trip=0.0)
    queue = Queue()
    results: list[int] = []
    for item in range(10):
        queue.put(item)

    def process_item(item: int) -> int:
        if item == 7:
            raise FatalError()
        if item % 4 == 0:
            raise TransientError()
        return item * 2

    def worker(worker_id: int):
        while not circuit.broken:
            try:
                item = queue.get(timeout=0.1)
            except Exception:
                continue
            try:
                results.append(process_item(item))
            except FatalError:
                circuit.trip()
            except TransientError:
                circuit.short()
            finally:
                queue.task_done()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert circuit.broken is True


def test_api_client_with_breaking_circuit() -> None:
    class OperationError(RuntimeError):
        pass

    class APIClient:
        def __init__(self):
            self.circuit = BreakingCircuit(
                num_shorts_to_trip=2,
                sleep_time_after_trip=0.0,
                backoff_factor=2.0,
                max_sleep_time=1.0,
                jitter=0.0,
            )

        def get(self, data: dict) -> dict | None:
            if self.circuit.broken:
                return None
            try:
                if data.get("fail"):
                    raise OperationError("fail")
                return data
            except OperationError:
                self.circuit.short()
                return None

        def reset(self):
            self.circuit.reset()

    client = APIClient()
    assert client.get({"id": 1}) == {"id": 1}
    client.get({"fail": True})
    client.get({"fail": True})
    assert client.circuit.broken is True


def test_connection_pool_breaker() -> None:
    class ConnectionPoolExhausted(RuntimeError):
        pass

    class ConnectionPool:
        def __init__(self):
            self.circuit = BreakingCircuit(
                num_shorts_to_trip=2,
                sleep_time_after_trip=0.0,
                backoff_factor=1.5,
                max_sleep_time=1.0,
            )
            self._fail = True

        def _acquire_connection(self):
            if self._fail:
                raise ConnectionError("fail")
            return object()

        def get_connection(self):
            if self.circuit.broken:
                raise ConnectionPoolExhausted("Circuit breaker is open")
            try:
                return self._acquire_connection()
            except ConnectionError:
                self.circuit.short()
                raise

        def mark_healthy(self):
            if self.circuit.broken:
                self.circuit.reset()
                self.circuit.reset_backoff()

    pool = ConnectionPool()
    try:
        pool.get_connection()
        assert False, "Expected ConnectionError"
    except ConnectionError:
        pass
    try:
        pool.get_connection()
        assert False, "Expected ConnectionError"
    except ConnectionError:
        pass
    try:
        pool.get_connection()
        assert False, "Expected ConnectionPoolExhausted"
    except ConnectionPoolExhausted:
        pass


def test_file_processor_with_circuit() -> None:
    class ProcessingError(RuntimeError):
        pass

    circ = Circuit(
        num_shorts_to_trip=2,
        sleep_time_after_trip=0.0,
        backoff_factor=2.0,
        max_sleep_time=1.0,
    )
    tmp_dir = Path("tmp_circuit_files")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        (tmp_dir / f"file_{i}.txt").write_text("ok")
    (tmp_dir / "bad.txt").write_text("")

    processed = 0
    errors = 0
    for file_path in tmp_dir.rglob("*.txt"):
        try:
            if file_path.read_text() == "":
                raise ProcessingError()
            processed += 1
        except ProcessingError:
            errors += 1
            circ.short()
    assert processed >= 5
    assert errors >= 1


def test_worker_graceful_degradation() -> None:
    class PrimaryServiceError(RuntimeError):
        pass

    class FallbackServiceError(RuntimeError):
        pass

    class Worker:
        def __init__(self):
            self.primary = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0.0)
            self.fallback = BreakingCircuit(num_shorts_to_trip=2, sleep_time_after_trip=0.0)

        def process(self, item: dict):
            try:
                return self._process_primary(item)
            except PrimaryServiceError:
                self.primary.short()
            if not self.fallback.broken:
                try:
                    return self._process_fallback(item)
                except FallbackServiceError:
                    self.fallback.short()
            return None

        def _process_primary(self, item):
            if item.get("primary_fail"):
                raise PrimaryServiceError()
            return {"primary": True, **item}

        def _process_fallback(self, item):
            if item.get("fallback_fail"):
                raise FallbackServiceError()
            return {"fallback": True, **item}

    worker = Worker()
    assert worker.process({"id": 1})["primary"] is True
    assert worker.process({"id": 2, "primary_fail": True})["fallback"] is True


def test_monitor_circuit_state() -> None:
    circ = Circuit(num_shorts_to_trip=3, sleep_time_after_trip=0.0, backoff_factor=2.0)
    for _ in range(3):
        circ.short()
    assert circ.total_trips >= 1


def test_full_script_in_memory() -> None:
    data_store = {
        "mem://users/1": (200, {"id": 1, "name": "Ada"}),
        "mem://users/2": (200, {"id": 2, "name": "Lin"}),
        "mem://users/3": (429, {"detail": "rate limited"}),
        "mem://users/4": (500, {"detail": "server error"}),
        "mem://users/5": (404, {"detail": "not found"}),
    }

    class WebScraper:
        def __init__(self, data_store: dict[str, tuple[int, dict]]):
            self.data_store = data_store
            self.rate_limiter = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0.0)
            self.failure_circuit = BreakingCircuit(num_shorts_to_trip=2, sleep_time_after_trip=0.0)

        async def scrape(self, urls: list[str]):
            results = []
            for url in urls:
                if self.failure_circuit.broken:
                    results.append({"url": url, "status": "skipped"})
                    continue
                results.append(await self._scrape_url(url))
            return results

        async def _scrape_url(self, url: str):
            status, payload = self.data_store[url]
            data_bytes = json.dumps(payload).encode()
            digest = __import__("hashlib").sha256(data_bytes).hexdigest()
            if status == 429:
                await self.rate_limiter.short.asynced()()
                return {"url": url, "status": "rate_limited"}
            if status >= 500:
                await self.failure_circuit.short.asynced()()
                return {"url": url, "status": "server_error"}
            if status >= 400:
                return {"url": url, "status": "client_error"}
            return {"url": url, "status": "success", "hash": digest[:8]}

    async def main():
        scraper = WebScraper(data_store)
        return await scraper.scrape(list(data_store.keys()))

    results = asyncio.run(main())
    assert any(r["status"] == "success" for r in results)


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    runner = TestRunner("Integration - circuits Examples")

    runner.run_test("Circuit short()", test_circuit_basic_short)
    runner.run_test("BreakingCircuit short()", test_breaking_circuit)
    runner.run_test("Dual circuit usage", test_dual_circuit_usage)
    runner.run_test("Async circuit short", test_async_circuit_short)
    runner.run_test("Shared circuit multithread", test_shared_circuit_multithreading)
    runner.run_test("API client with circuit", test_api_client_with_breaking_circuit)
    runner.run_test("Connection pool breaker", test_connection_pool_breaker)
    runner.run_test("File processor circuit", test_file_processor_with_circuit)
    runner.run_test("Graceful degradation", test_worker_graceful_degradation)
    runner.run_test("Monitor circuit state", test_monitor_circuit_state)
    runner.run_test("Full script in memory", test_full_script_in_memory)

    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
