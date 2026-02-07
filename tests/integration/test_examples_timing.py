"""
Integration Tests for timing Examples

Validates the examples in suitkaise/_docs_copy/timing/examples.md
with detailed assertions.
"""

import asyncio
import threading
import sys
import tempfile
from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import timing


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

def test_timing_simple_start_stop() -> None:
    timer = timing.Sktimer()
    timer.start()
    total = sum(i * i for i in range(100_000))
    assert total > 0
    elapsed = timer.stop()
    assert elapsed > 0
    assert timer.most_recent == elapsed


def test_timing_elapsed() -> None:
    start = timing.time()
    payload = b"elapsed_example"
    for _ in range(5000):
        payload = __import__("hashlib").sha256(payload).digest()
    elapsed = timing.elapsed(start)
    assert elapsed > 0
    end = timing.time()
    elapsed2 = timing.elapsed(start, end)
    assert elapsed2 > 0
    assert abs(timing.elapsed(end, start) - elapsed2) < 1e-6


def test_timing_multiple_measurements() -> None:
    timer = timing.Sktimer()
    for i in range(10):
        timer.start()
        payload = b"x" * (2000 + (i % 5) * 500)
        __import__("hashlib").sha256(payload).hexdigest()
        timer.stop()
    assert timer.num_times == 10
    assert timer.mean > 0
    assert timer.median > 0


def test_timing_lap() -> None:
    timer = timing.Sktimer()
    items = ["a", "b", "c"]
    timer.start()
    for item in items:
        __import__("hashlib").sha256((item * 1000).encode()).hexdigest()
        lap_time = timer.lap()
        assert lap_time > 0
    timer.discard()
    assert timer.num_times == len(items)


def test_timing_pause_resume() -> None:
    timer = timing.Sktimer()
    timer.start()
    data = b"phase1"
    for _ in range(5000):
        data = __import__("hashlib").sha256(data).digest()
    timer.pause()
    data = b"paused_work"
    for _ in range(8000):
        data = __import__("hashlib").sha256(data).digest()
    timer.resume()
    data = b"phase2"
    for _ in range(5000):
        data = __import__("hashlib").sha256(data).digest()
    elapsed = timer.stop()
    assert elapsed > 0
    assert timer.total_time_paused >= 0


def test_timing_timethis_context_manager() -> None:
    with timing.TimeThis() as timer:
        total = sum(range(100_000))
    assert total > 0
    assert timer.most_recent > 0


def test_timing_shared_timer_timethis() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        api_timer = timing.Sktimer()
        data_dir = tmp_path / "api"
        data_dir.mkdir(parents=True, exist_ok=True)
        for user_id in range(3):
            (data_dir / f"user_{user_id}.json").write_text(
                f'{{"id": {user_id}, "name": "User {user_id}"}}'
            )
            (data_dir / f"posts_{user_id}.json").write_text(
                '[{"id": 1, "title": "Post 1"}]'
            )

        def fetch_user(user_id: int) -> dict:
            with timing.TimeThis(api_timer):
                text = (data_dir / f"user_{user_id}.json").read_text()
                digest = __import__("hashlib").sha256(text.encode()).hexdigest()
                return {"hash": digest[:8], **__import__("json").loads(text)}

        def fetch_posts(user_id: int) -> list[dict]:
            with timing.TimeThis(api_timer):
                text = (data_dir / f"posts_{user_id}.json").read_text()
                posts = __import__("json").loads(text)
                return posts

        for user_id in range(3):
            assert fetch_user(user_id)["id"] == user_id
            assert fetch_posts(user_id)

        assert api_timer.num_times == 6


def test_timing_threshold() -> None:
    slow_timer = timing.Sktimer()

    def process_item(item: int) -> None:
        with timing.TimeThis(slow_timer, threshold=0.0001):
            data = f"item_{item}".encode()
            iterations = 2000 if item % 5 == 0 else 200
            for _ in range(iterations):
                data = __import__("hashlib").sha256(data).digest()

    for i in range(10):
        process_item(i)
    assert slow_timer.num_times >= 1


def test_timing_shared_timer_across_functions() -> None:
    math_timer = timing.Sktimer()

    @timing.timethis(math_timer)
    def add(a, b):
        __import__("hashlib").sha256(f"{a}+{b}".encode()).digest()
        return a + b

    @timing.timethis(math_timer)
    def multiply(a, b):
        __import__("hashlib").sha256(f"{a}*{b}".encode()).digest()
        return a * b

    @timing.timethis(math_timer)
    def divide(a, b):
        __import__("hashlib").sha256(f"{a}/{b}".encode()).digest()
        return a / b if b else 0

    for i in range(1, 6):
        add(i, i + 1)
        multiply(i, i + 1)
        divide(i, i + 1)
    assert math_timer.num_times == 15


def test_timing_stacked_decorators() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "db.json"
        db_path.write_text("{}")
        db_timer = timing.Sktimer()

        @timing.timethis()
        @timing.timethis(db_timer)
        def db_read(key):
            data = __import__("json").loads(db_path.read_text())
            return data.get(key)

        @timing.timethis()
        @timing.timethis(db_timer)
        def db_write(key, value):
            data = __import__("json").loads(db_path.read_text())
            data[key] = value
            db_path.write_text(__import__("json").dumps(data))
            return True

        for i in range(5):
            db_write(f"key_{i}", f"value_{i}")
            assert db_read(f"key_{i}") == f"value_{i}"
        assert db_timer.num_times == 10


def test_timing_rolling_window() -> None:
    @timing.timethis(max_times=10)
    def process_request():
        payload = b"request_payload" * 100
        __import__("hashlib").sha256(payload).hexdigest()

    for _ in range(25):
        process_request()
    assert process_request.timer.num_times == 10


def test_timing_concurrent_threads() -> None:
    timer = timing.Sktimer()

    def worker(worker_id, iterations):
        for i in range(iterations):
            timer.start()
            payload = f"{worker_id}-{i}".encode()
            for _ in range(200):
                payload = __import__("hashlib").sha256(payload).digest()
            timer.stop()

    threads = [threading.Thread(target=worker, args=(i, 5)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert timer.num_times == 15


def test_timing_benchmarking() -> None:
    def benchmark(name, func, iterations=20):
        timer = timing.Sktimer()
        for _ in range(iterations):
            timer.start()
            func()
            timer.stop()
        return {
            "name": name,
            "mean": timer.mean,
            "stdev": timer.stdev,
        }

    def list_append():
        result = []
        for i in range(1000):
            result.append(i)
        return result

    def list_comprehension():
        return [i for i in range(1000)]

    results = [
        benchmark("list.append()", list_append),
        benchmark("list comprehension", list_comprehension),
    ]
    assert all(r["mean"] > 0 for r in results)


def test_timing_discard_failed() -> None:
    timer = timing.Sktimer()
    success = 0
    failure = 0

    def unreliable_operation(item_id: int):
        payload = f"item_{item_id}".encode()
        digest = __import__("hashlib").sha256(payload).digest()
        if digest[0] % 3 == 0:
            raise RuntimeError("Operation failed")
        return digest[:8].hex()

    for i in range(30):
        timer.start()
        try:
            unreliable_operation(i)
            timer.stop()
            success += 1
        except RuntimeError:
            timer.discard()
            failure += 1

    assert timer.num_times == success
    assert success + failure == 30


def test_timing_async_timing() -> None:
    async def fetch_data(item_id: int, base: Path) -> str:
        path = base / f"async_{item_id}.txt"
        path.write_text("async data\n" * 100)
        return await asyncio.to_thread(path.read_text)

    async def main() -> float:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            timer = timing.Sktimer()
            for i in range(3):
                timer.start()
                data = await fetch_data(i, tmp_path)
                assert data.startswith("async data")
                timer.stop()
            return timer.mean

    mean = asyncio.run(main())
    assert mean > 0


def test_timing_full_monitor_script() -> None:
    class EndpointStats:
        def __init__(self, name: str):
            self.name = name
            self.timer = timing.Sktimer()

    class APIMonitor:
        def __init__(self, max_measurements: int = 1000):
            self.overall_timer = timing.Sktimer(max_times=max_measurements)
            self._endpoints: dict[str, EndpointStats] = {}
            self._lock = threading.RLock()

        def _get_endpoint(self, name: str) -> EndpointStats:
            with self._lock:
                if name not in self._endpoints:
                    self._endpoints[name] = EndpointStats(name)
                return self._endpoints[name]

        def time_request(self, endpoint: str):
            endpoint_stats = self._get_endpoint(endpoint)

            class DualTimer:
                def __init__(self, overall, endpoint):
                    self.overall = overall
                    self.endpoint = endpoint

                def __enter__(self):
                    self.overall.start()
                    self.endpoint.start()
                    return self

                def __exit__(self, *args):
                    self.overall.stop()
                    self.endpoint.stop()

            return DualTimer(self.overall_timer, endpoint_stats.timer)

    def run_api_calls(monitor: APIMonitor, num_calls: int):
        endpoints = ["/users", "/posts", "/comments"]
        payloads = {
            "/users": b"user\n" * 200,
            "/posts": b"post\n" * 400,
            "/comments": b"comment\n" * 800,
        }
        for i in range(num_calls):
            endpoint = endpoints[i % len(endpoints)]
            with monitor.time_request(endpoint):
                __import__("hashlib").sha256(payloads[endpoint]).digest()

    monitor = APIMonitor()
    threads = [threading.Thread(target=run_api_calls, args=(monitor, 20)) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert monitor.overall_timer.num_times == 40


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    runner = TestRunner("Integration - timing Examples")

    runner.run_test("Simple start/stop", test_timing_simple_start_stop)
    runner.run_test("Elapsed timing", test_timing_elapsed)
    runner.run_test("Multiple measurements", test_timing_multiple_measurements)
    runner.run_test("Lap timing", test_timing_lap)
    runner.run_test("Pause/resume", test_timing_pause_resume)
    runner.run_test("TimeThis context", test_timing_timethis_context_manager)
    runner.run_test("Shared timer TimeThis", test_timing_shared_timer_timethis)
    runner.run_test("Threshold timing", test_timing_threshold)
    runner.run_test("Shared timer across funcs", test_timing_shared_timer_across_functions)
    runner.run_test("Stacked decorators", test_timing_stacked_decorators)
    runner.run_test("Rolling window", test_timing_rolling_window)
    runner.run_test("Concurrent threads", test_timing_concurrent_threads)
    runner.run_test("Benchmarking", test_timing_benchmarking)
    runner.run_test("Discard failed", test_timing_discard_failed)
    runner.run_test("Async timing", test_timing_async_timing)
    runner.run_test("Full monitor script", test_timing_full_monitor_script)

    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
