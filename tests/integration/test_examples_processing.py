"""
Integration Tests for processing Examples

Validates the examples in suitkaise/_docs_copy/processing/examples.md
with detailed assertions.
"""

import asyncio
import multiprocessing
import hashlib
import math
import sys
import warnings
from pathlib import Path

# Add project root to path (auto-detect by marker files)


def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent
    return start


project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import timing
from suitkaise.processing import Pipe, Pool, Share, Skprocess
from suitkaise.processing import ProcessTimeoutError, ProcessError, autoreconnect
from suitkaise.timing import Sktimer, TimeThis


# =============================================================================
# Test Infrastructure
# =============================================================================


class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


def _run_test_in_subprocess(func, queue):
    try:
        func()
        queue.put((True, ""))
    except AssertionError as exc:
        queue.put((False, str(exc)))
    except Exception as exc:
        queue.put((False, f"{type(exc).__name__}: {exc}"))


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = "\033[92m"
        self.RED = "\033[91m"
        self.YELLOW = "\033[93m"
        self.CYAN = "\033[96m"
        self.BOLD = "\033[1m"
        self.RESET = "\033[0m"

    def run_test(self, name: str, test_func, timeout: float | None = None):
        if timeout is None:
            try:
                test_func()
                self.results.append(TestResult(name, True))
            except AssertionError as e:
                self.results.append(TestResult(name, False, error=str(e)))
            except Exception as e:
                self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))
            return

        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        proc = ctx.Process(target=_run_test_in_subprocess, args=(test_func, queue))
        proc.start()
        proc.join(timeout=timeout)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=1.0)
            self.results.append(TestResult(name, False, error=f"Timeout after {timeout}s"))
            return
        try:
            ok, error = queue.get_nowait()
        except Exception:
            ok, error = False, "No result returned"
        if ok:
            self.results.append(TestResult(name, True))
        else:
            self.results.append(TestResult(name, False, error=error))

    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'=' * 70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'=' * 70}{self.RESET}\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        for result in self.results:
            status = f"{self.GREEN}✓ PASS{self.RESET}" if result.passed else f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")

        print(f"\n{self.BOLD}{'-' * 70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-' * 70}{self.RESET}\n")

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
# Helpers (module-level for subprocess safety)
# =============================================================================


def _prime_factors(n: int) -> list[int]:
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def pool_square(x):
    return x * x


def pool_add(a, b):
    return a + b


def pool_work_hash(item: int):
    data = str(item).encode()
    for _ in range(100):
        data = hashlib.sha256(data).digest()
    return item


def pool_slow_function(x):
    for _ in range(100_000):
        _ = math.sqrt(123.456)
    return x


def pool_compute(x):
    return x * x


def pool_cpu_work(x):
    return x + 1


def pool_process_pair(x, y):
    return x + y


def pool_risky_function(x):
    if x == 3:
        raise ValueError("bad")
    return x * 2


class CounterProcessBasic(Skprocess):
    def __init__(self, target: int = 10):
        self.target = target
        self.counter = 0
        self.process_config.runs = target

    def __run__(self):
        self.counter += 1

    def __result__(self):
        return self.counter


class QuickProcessRunner(Skprocess):
    def __init__(self, data: list[int]):
        self.data = data
        self.results = []
        self.process_config.runs = len(data)

    def __run__(self):
        item = self.data[self._current_run]
        self.results.append(item * 2)

    def __result__(self):
        return self.results


class DataProcessorLifecycle(Skprocess):
    def __init__(self, batch_size: int = 3):
        self.batch_size = batch_size
        self.process_config.runs = 2
        self.processed_batches = []
        self.total_items = 0
        self.current_batch = None

    def __prerun__(self):
        batch_number = self._current_run
        self.current_batch = [f"item_{batch_number}_{i}" for i in range(self.batch_size)]

    def __run__(self):
        processed = []
        for item in self.current_batch:
            processed.append(item.upper())
            self.total_items += 1
        self._processed = processed

    def __postrun__(self):
        self.processed_batches.append(self._processed)
        self.current_batch = None
        self._processed = None

    def __onfinish__(self):
        self.finished = True

    def __result__(self):
        return {"batches": self.processed_batches, "total_items": self.total_items}


class MonitorProcessIndefinite(Skprocess):
    def __init__(self):
        self.process_config.runs = None
        self.events = []

    def __run__(self):
        payload = f"{self._current_run}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        self.events.append({"run": self._current_run, "hash": digest[:8]})

    def __result__(self):
        return self.events


class TimeBoundProcessJoin(Skprocess):
    def __init__(self, max_seconds: float = 0.05):
        self.process_config.runs = None
        self.process_config.join_in = max_seconds
        self.iterations = 0

    def __run__(self):
        payload = f"iter_{self._current_run}".encode()
        _ = hashlib.sha256(payload).digest()
        self.iterations += 1

    def __result__(self):
        return self.iterations


class UnreliableProcessLives(Skprocess):
    def __init__(self):
        self.process_config.runs = 5
        self.process_config.lives = 3
        self.successful_runs = 0
        self.attempt_count = 0

    def __prerun__(self):
        self.attempt_count += 1

    def __run__(self):
        payload = f"run:{self._current_run}".encode()
        digest = hashlib.sha256(payload).digest()
        if digest[0] % 5 == 0:
            raise RuntimeError("Content failure")
        self.successful_runs += 1

    def __error__(self):
        return {"status": "failed", "successful_runs": self.successful_runs}

    def __result__(self):
        return {"status": "success", "successful_runs": self.successful_runs}


class SlowProcessTimeout(Skprocess):
    def __init__(self):
        self.process_config.runs = 3
        self.process_config.timeouts.run = 0.01
        self.completed_runs = 0

    def __run__(self):
        if self._current_run == 1:
            for _ in range(200_000):
                _ = math.sqrt(12345.6789)
        else:
            for _ in range(5000):
                _ = math.sqrt(123.456)
        self.completed_runs += 1

    def __error__(self):
        if isinstance(self.error, ProcessTimeoutError):
            return {"status": "timeout", "completed_runs": self.completed_runs}
        return {"status": "error"}

    def __result__(self):
        return {"status": "success", "completed_runs": self.completed_runs}


class TimedProcessAccess(Skprocess):
    def __init__(self, runs: int = 5):
        self.process_config.runs = runs
        self.data = [f"data_{i}" for i in range(200)]

    def __prerun__(self):
        self.data = self.data[-1:] + self.data[:-1]

    def __run__(self):
        iterations = 50 + (self._current_run * 7 % 100)
        for _ in range(iterations):
            for item in self.data[:50]:
                hashlib.sha256(item.encode()).hexdigest()

    def __postrun__(self):
        sorted(self.data[:50])

    def __result__(self):
        return "done"


class AsyncFriendlyProcessExample(Skprocess):
    def __init__(self, process_id: int, data_chunks: list[str]):
        self.process_id = process_id
        self.data_chunks = data_chunks
        self.process_config.runs = len(data_chunks)
        self.results = []

    def __run__(self):
        chunk = self.data_chunks[self._current_run]
        digest = hashlib.sha256(chunk.encode()).hexdigest()[:8]
        self.results.append({"id": self.process_id, "chunk": chunk, "hash": digest})

    def __result__(self):
        return self.results


class BackgroundProcessExample(Skprocess):
    def __init__(self, numbers: list[int]):
        self.numbers = numbers
        self.process_config.runs = len(numbers)
        self.results = []

    def __run__(self):
        n = self.numbers[self._current_run]
        self.results.append({"number": n, "factors": _prime_factors(n)})

    def __result__(self):
        return self.results


class DataTransformerProcess(Skprocess):
    def __init__(self, input_data: dict):
        self.input_data = input_data
        self.process_config.runs = 1
        self.transformed = None

    def __run__(self):
        data = self.input_data
        self.transformed = {
            "id": data["id"],
            "doubled": data["value"] * 2,
        }

    def __result__(self):
        return self.transformed


class CounterProcessShare(Skprocess):
    def __init__(self, shared: Share, amount: int = 1):
        self.shared = shared
        self.amount = amount
        self.process_config.runs = 5

    def __postrun__(self):
        self.shared.counter.increment(self.amount)

    def __result__(self):
        return "done"


class TimedWorkerProcess(Skprocess):
    def __init__(self, shared: Share, work_count: int = 3):
        self.shared = shared
        self.process_config.runs = work_count

    def __run__(self):
        with timing.TimeThis() as run_timer:
            data = b"benchmark_data"
            iterations = 500 + (self._current_run * 97 % 1500)
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
        self.shared.timer.add_time(run_timer.most_recent)

    def __result__(self):
        return "done"


class Counter:
    def __init__(self):
        self.value = 0

    def increment(self, amount=1):
        self.value += amount


class WorkerProcessShare(Skprocess):
    def __init__(self, shared: Share):
        self.shared = shared
        self.process_config.runs = 5

    def __postrun__(self):
        self.shared.my_counter.increment(1)

    def __result__(self):
        return "done"


class Stats:
    def __init__(self):
        self.processed = 0
        self.errors = 0
        self.successes = 0

    def record_success(self):
        self.processed += 1
        self.successes += 1

    def record_error(self):
        self.processed += 1
        self.errors += 1


class DataProcessorShare(Skprocess):
    def __init__(self, shared: Share, item: dict):
        self.shared = shared
        self.item = item
        self.process_config.runs = 1

    def __run__(self):
        with timing.TimeThis() as run_timer:
            data = self.item["data"].encode()
            checksum = hashlib.sha256(data).digest()
            if checksum[0] % 5 == 0:
                self.shared.stats.record_error()
            else:
                for _ in range(200):
                    data = hashlib.sha256(data).digest()
                self.shared.stats.record_success()
        self.shared.timer.add_time(run_timer.most_recent)

    def __result__(self):
        return self.item["id"]


class IterativeWorkerShare(Skprocess):
    def __init__(self, shared: Share):
        self.shared = shared
        self.process_config.runs = 10

    def __run__(self):
        with TimeThis() as run_timer:
            data = f"iteration_{self._current_run}".encode()
            iterations = 200 + (hashlib.sha256(data).digest()[0] % 600)
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
        self.shared.progress += 1
        self.shared.timer.add_time(run_timer.most_recent)

    def __result__(self):
        return "complete"


class IncrementerProcess(Skprocess):
    def __init__(self, shared: Share):
        self.shared = shared
        self.process_config.runs = 3

    def __postrun__(self):
        self.shared.count.increment(1)

    def __result__(self):
        return "done"


class PipeWorkerProcess(Skprocess):
    def __init__(self, pipe_point: Pipe.Point):
        self.pipe = pipe_point
        self.process_config.runs = 1

    def __run__(self):
        command = self.pipe.recv()
        self.pipe.send({"result": command["value"] * 2})

    def __result__(self):
        return "done"


class DataReceiverProcess(Skprocess):
    def __init__(self, pipe_point: Pipe.Point):
        self.pipe = pipe_point
        self.process_config.runs = 1
        self.received_data = []

    def __run__(self):
        while True:
            data = self.pipe.recv()
            if data is None:
                break
            self.received_data.append(data)

    def __result__(self):
        return self.received_data


class DualPipeWorkerProcess(Skprocess):
    def __init__(self, cmd_pipe: Pipe.Point, data_pipe: Pipe.Point):
        self.cmd_pipe = cmd_pipe
        self.data_pipe = data_pipe
        self.process_config.runs = None

    def __run__(self):
        cmd = self.cmd_pipe.recv()
        if cmd["action"] == "process":
            data = self.data_pipe.recv()
            self.cmd_pipe.send({"status": "done", "result": sum(data)})
        elif cmd["action"] == "stop":
            self.stop()

    def __result__(self):
        return "done"


class CommandableProcessExample(Skprocess):
    def __init__(self):
        self.process_config.runs = None
        self.multiplier = 1
        self.results = []

    def __prerun__(self):
        command = self.listen(timeout=0.1)
        if command and command.get("action") == "set_multiplier":
            self.multiplier = command["value"]
        elif command and command.get("action") == "stop":
            self.stop()

    def __run__(self):
        data = f"run_{self._current_run}_mult_{self.multiplier}".encode()
        for _ in range(50 * self.multiplier):
            data = hashlib.sha256(data).digest()
        value = int.from_bytes(data[:4], "big") % 1000
        self.results.append({"run": self._current_run, "value": value})
        if self._current_run % 3 == 0:
            self.tell({"progress": self._current_run, "latest": value})

    def __result__(self):
        return self.results


class AsyncWorkerExample(Skprocess):
    def __init__(self, data_items: list[str]):
        self.data_items = data_items
        self.process_config.runs = len(data_items)
        self.results = []

    def __run__(self):
        item = self.data_items[self._current_run]
        digest = hashlib.sha256(item.encode()).hexdigest()
        self.results.append(digest[:16])
        if self._current_run % 2 == 0:
            self.tell({"run": self._current_run, "status": "working"})

    def __result__(self):
        return self.results


class FakeConnection:
    def __init__(self, name: str):
        self.name = name

    def cursor(self):
        return self

    def execute(self, query: str):
        self.query = query

    def fetchall(self):
        return [(self.name,)]

    def close(self):
        pass


@autoreconnect(start_threads=False, **{"FakeConnection": {"*": "secret"}})
class DatabaseWorkerExample(Skprocess):
    def __init__(self, db_connection, query: str):
        self.db = db_connection
        self.query = query
        self.process_config.runs = 1
        self.results = None

    def __run__(self):
        cursor = self.db.cursor()
        cursor.execute(self.query)
        self.results = cursor.fetchall()
        cursor.close()

    def __result__(self):
        return self.results


class TaskStats:
    def __init__(self):
        self.total_tasks = 0
        self.completed = 0
        self.failed = 0
        self.retried = 0

    def record_complete(self):
        self.completed += 1
        self.total_tasks += 1

    def record_fail(self):
        self.failed += 1
        self.total_tasks += 1

    def record_retry(self):
        self.retried += 1


class TaskWorkerExample(Skprocess):
    def __init__(self, shared: Share, task: dict):
        self.shared = shared
        self.task = task
        self.process_config.runs = 1
        self.process_config.lives = 2
        self.process_config.timeouts.run = 2.0
        self.result_data = None
        self.attempts = 0

    def __prerun__(self):
        self.attempts += 1
        if self.attempts > 1:
            self.shared.stats.record_retry()

    def __run__(self):
        start = timing.time()
        try:
            iterations = 100 + (self.task["id"] * 7 % 200)
            data = self.task["data"].encode()
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
            checksum = hashlib.sha256(self.task["data"].encode()).digest()
            if checksum[0] % 10 == 0:
                raise RuntimeError("content failure")
            self.result_data = {"task_id": self.task["id"], "status": "success"}
            self.shared.stats.record_complete()
        finally:
            self.shared.timer.add_time(timing.elapsed(start))

    def __error__(self):
        self.shared.stats.record_fail()
        return {"task_id": self.task["id"], "status": "failed"}

    def __result__(self):
        return self.result_data


class Results:
    def __init__(self):
        self.items = []
        self.count = 0

    def add(self, item):
        self.items.append(item)
        self.count += 1


class DataPipelineWorkerExample(Skprocess):
    def __init__(self, shared: Share, worker_id: int):
        self.shared = shared
        self.worker_id = worker_id
        self.process_config.runs = None
        self.processed = 0

    def __prerun__(self):
        msg = self.listen(timeout=0.1)
        if msg and msg.get("action") == "stop":
            self.stop()
        elif msg and msg.get("action") == "data":
            self._pending_data = msg["payload"]
        else:
            self._pending_data = None

    def __run__(self):
        if self._pending_data is None:
            return
        with TimeThis() as run_timer:
            data = self._pending_data
            data_bytes = data.encode()
            for _ in range(200):
                data_bytes = hashlib.sha256(data_bytes).digest()
            output = hashlib.sha256(data_bytes).hexdigest()[:16]
            result = {"worker": self.worker_id, "input": data, "output": output}
        self.shared.results.add(result)
        self.shared.timer.add_time(run_timer.most_recent)
        self.processed += 1
        self._pending_data = None

    def __result__(self):
        return {"worker_id": self.worker_id, "total_processed": self.processed}


def run_task_queue(tasks: list[dict], workers: int = 2):
    with Share() as share:
        share.stats = TaskStats()
        share.timer = Sktimer()
        args = [(share, task) for task in tasks]
        with Pool(workers=workers) as pool:
            results = pool.star().map(TaskWorkerExample, args)
        return results, share.stats


def run_pipeline(data_stream, num_workers: int = 2, timeout: float = 1.0):
    with Share() as share:
        share.results = Results()
        share.timer = Sktimer()
        workers = []
        for i in range(num_workers):
            worker = DataPipelineWorkerExample(share, worker_id=i)
            worker.start()
            workers.append(worker)
        start_time = timing.time()
        worker_idx = 0
        for item in data_stream:
            if timing.elapsed(start_time) > timeout:
                break
            workers[worker_idx].tell({"action": "data", "payload": item})
            worker_idx = (worker_idx + 1) % num_workers
        for worker in workers:
            worker.tell({"action": "stop"})
        for worker in workers:
            worker.wait()
        worker_results = [worker.result() for worker in workers]
        return share.results.items, worker_results


def generate_data(n):
    for i in range(n):
        yield f"item_{i}"


# =============================================================================
# Tests
# =============================================================================


def test_processing_basic_skprocess_counter() -> None:
    process = CounterProcessBasic(target=50)
    process.start()
    process.wait()
    assert process.result() == 50


def test_processing_run_method() -> None:
    results = QuickProcessRunner([1, 2, 3]).run()
    assert results == [2, 4, 6]


def test_processing_full_lifecycle() -> None:
    result = DataProcessorLifecycle(batch_size=2).run()
    assert result["total_items"] == 4
    assert len(result["batches"]) == 2


def test_processing_indefinite_stop() -> None:
    process = MonitorProcessIndefinite()
    process.start()
    timing.sleep(0.05)
    for _ in range(5):
        _ = hashlib.sha256(b"monitor").digest()
    process.stop()
    process.wait()
    result = process.result()
    assert isinstance(result, list)


def test_processing_join_in() -> None:
    result = TimeBoundProcessJoin(max_seconds=0.02).run()
    assert result > 0


def test_processing_lives() -> None:
    try:
        result = UnreliableProcessLives().run()
        assert result["status"] == "success"
    except ProcessError as exc:
        assert "Process failed:" in str(exc)


def test_processing_timeouts() -> None:
    result = SlowProcessTimeout().run()
    assert result["status"] in {"timeout", "success"}


def test_processing_timing_access() -> None:
    process = TimedProcessAccess(runs=5)
    process.run()
    assert process.__run__.timer.num_times == 5
    assert process.process_timer.num_times == 5


def test_processing_async_execution() -> None:
    async def main():
        all_data = [
            [f"data_{i}_{j}" for j in range(3)] for i in range(2)
        ]
        processes = []
        for i, data in enumerate(all_data):
            p = AsyncFriendlyProcessExample(i, data)
            p.start()
            processes.append(p)
        await asyncio.gather(*[p.wait.asynced()() for p in processes])
        return [p.result() for p in processes]

    results = asyncio.run(main())
    assert len(results) == 2


def test_processing_background_future() -> None:
    numbers = [123457, 99991]
    process = BackgroundProcessExample(numbers)
    future = process.run.background()()
    result = future.result()
    assert len(result) == 2


def test_processing_pool_map() -> None:
    with Pool(workers=2) as pool:
        results = pool.map(pool_square, [1, 2, 3])
    assert results == [1, 4, 9]


def test_processing_pool_star() -> None:
    with Pool(workers=2) as pool:
        pairs = [(1, 2), (3, 4)]
        sums = pool.star().map(pool_add, pairs)
    assert sums == [3, 7]


def test_processing_pool_unordered_map() -> None:
    with Pool(workers=2) as pool:
        results = pool.unordered_map(pool_work_hash, list(range(5)))
    assert sorted(results) == list(range(5))


def test_processing_pool_imap() -> None:
    with Pool(workers=2) as pool:
        results = list(pool.imap(pool_work_hash, list(range(5))))
    assert results == list(range(5))


def test_processing_pool_unordered_imap() -> None:
    with Pool(workers=2) as pool:
        results = list(pool.unordered_imap(pool_work_hash, list(range(5))))
    assert sorted(results) == list(range(5))


def test_processing_pool_timeout() -> None:
    with Pool(workers=2) as pool:
        results = pool.map.timeout(2.0)(pool_slow_function, [1, 2, 3])
    assert results == [1, 2, 3]


def test_processing_pool_background() -> None:
    with Pool(workers=2) as pool:
        future = pool.map.background()(pool_compute, [1, 2, 3])
        results = future.result()
    assert results == [1, 4, 9]


def test_processing_pool_async() -> None:
    async def main():
        with Pool(workers=2) as pool:
            results = await asyncio.gather(
                pool.map.asynced()(pool_cpu_work, [1, 2]),
                pool.map.asynced()(pool_cpu_work, [3, 4]),
            )
        return results

    results = asyncio.run(main())
    assert results == [[2, 3], [4, 5]]


def test_processing_pool_skprocess() -> None:
    items = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
    with Pool(workers=2) as pool:
        results = pool.map(DataTransformerProcess, items)
    assert results == [{"id": 1, "doubled": 20}, {"id": 2, "doubled": 40}]


def test_processing_pool_star_modifiers() -> None:
    async def main():
        with Pool(workers=2) as pool:
            pairs = [(1, 2), (3, 4)]
            results = pool.star().map.timeout(2.0)(pool_process_pair, pairs)
            async_results = await pool.star().map.asynced()(pool_process_pair, pairs)
            return results, async_results

    results, async_results = asyncio.run(main())
    assert results == [3, 7]
    assert async_results == [3, 7]


def test_processing_pool_error_handling() -> None:
    with Pool(workers=2) as pool:
        try:
            pool.map(pool_risky_function, [1, 2, 3])
            assert False, "Expected pool error"
        except RuntimeError:
            pass
        results = pool.map(pool_risky_function, [1, 2, 4])
    assert results == [2, 4, 8]


def test_processing_share_basic_counter() -> None:
    with Share() as share:
        share.counter = Counter()
        with Pool(workers=2) as pool:
            pool.map(CounterProcessShare, [share] * 2)
        assert share.counter.value == 10


def test_processing_share_timer() -> None:
    with Share() as share:
        share.timer = Sktimer()
        with Pool(workers=2) as pool:
            pool.map(TimedWorkerProcess, [share] * 2)
        assert share.timer.num_times == 6


def test_processing_share_context_manager() -> None:
    with Share() as share:
        share.my_counter = Counter()
        with Pool(workers=2) as pool:
            pool.map(WorkerProcessShare, [share] * 2)
        assert share.my_counter.value == 10


def test_processing_share_multiple_objects() -> None:
    with Share() as share:
        share.stats = Stats()
        share.timer = timing.Sktimer()
        items = [{"id": i, "data": f"item_{i}"} for i in range(10)]
        with Pool(workers=2) as pool:
            args = [(share, item) for item in items]
            pool.star().map(DataProcessorShare, args)
        assert share.stats.processed == 10


def test_processing_share_single_process() -> None:
    with Share() as share:
        share.progress = 0
        share.timer = Sktimer()
        process = IterativeWorkerShare(share)
        process.start()
        while process.is_alive:
            _ = hashlib.sha256(b"progress").digest()
        process.wait()
        assert share.progress == 10


def test_processing_share_start_stop() -> None:
    share = Share(auto_start=False)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            share.counter = 0
            assert any("Share is stopped" in str(w.message) for w in caught)
        share.start()
        share.counter = 100
        share.stop()
        share.start()
        assert share.counter == 100
    finally:
        share.stop()


def test_processing_share_clear() -> None:
    with Share() as share:
        share.count = Counter()
        with Pool(workers=2) as pool:
            pool.map(IncrementerProcess, [share] * 2)
        assert share.count.value == 6
        share.clear()
        share.count = Counter()
        with Pool(workers=2) as pool:
            pool.map(IncrementerProcess, [share] * 1)
        assert share.count.value == 3


def test_processing_pipe_basic() -> None:
    anchor, point = Pipe.pair()
    process = PipeWorkerProcess(point)
    process.start()
    point.close()
    anchor.send({"value": 21})
    response = anchor.recv()
    process.wait()
    anchor.close()
    assert response["result"] == 42


def test_processing_pipe_one_way() -> None:
    anchor, point = Pipe.pair(one_way=True)
    process = DataReceiverProcess(point)
    process.start()
    point.close()
    for i in range(3):
        anchor.send({"id": i})
    anchor.send(None)
    process.wait()
    result = process.result()
    anchor.close()
    assert len(result) == 3


def test_processing_pipe_multiple() -> None:
    cmd_anchor, cmd_point = Pipe.pair()
    data_anchor, data_point = Pipe.pair()
    process = DualPipeWorkerProcess(cmd_point, data_point)
    process.start()
    cmd_point.close()
    data_point.close()
    cmd_anchor.send({"action": "process"})
    data_anchor.send([1, 2, 3])
    result = cmd_anchor.recv()
    cmd_anchor.send({"action": "stop"})
    process.wait()
    cmd_anchor.close()
    data_anchor.close()
    assert result["result"] == 6


def test_processing_tell_listen() -> None:
    process = CommandableProcessExample()
    process.start()
    for _ in range(1000):
        _ = hashlib.sha256(b"parent_work").digest()
    process.tell({"action": "set_multiplier", "value": 2})
    for _ in range(1000):
        _ = hashlib.sha256(b"parent_work_2").digest()
    msgs = []
    for _ in range(20):
        msg = process.listen(timeout=0.1)
        if msg is not None:
            msgs.append(msg)
    process.tell({"action": "stop"})
    process.wait()
    while True:
        msg = process.listen(timeout=0.1)
        if msg is None:
            break
        msgs.append(msg)
    assert process.result()
    assert msgs


def test_processing_tell_listen_async() -> None:
    async def main():
        data = [f"item_{i}" for i in range(6)]
        process = AsyncWorkerExample(data)
        process.start()
        statuses = []
        while process.is_alive:
            msg = await process.listen.asynced()(timeout=0.2)
            if msg:
                statuses.append(msg)
        await process.wait.asynced()()
        return process.result(), statuses

    results, statuses = asyncio.run(main())
    assert len(results) == 6
    assert statuses


def test_processing_autoreconnect_decorator() -> None:
    result = DatabaseWorkerExample(FakeConnection("db"), "select").run()
    assert result == [("db",)]


def test_processing_full_task_queue() -> None:
    tasks = [{"id": i, "data": f"task_{i}"} for i in range(10)]
    results, stats = run_task_queue(tasks)
    assert len(results) == 10
    assert stats.total_tasks == 10


def test_processing_full_pipeline() -> None:
    results, worker_stats = run_pipeline(generate_data(20), num_workers=2, timeout=1.0)
    assert results
    assert len(worker_stats) == 2


# =============================================================================
# Main Entry Point
# =============================================================================


def run_all_tests():
    runner = TestRunner("Integration - processing Examples")
    default_timeout = 20.0

    runner.run_test("Basic Skprocess", test_processing_basic_skprocess_counter, default_timeout)
    runner.run_test("run() method", test_processing_run_method, default_timeout)
    runner.run_test("Full lifecycle", test_processing_full_lifecycle, default_timeout)
    runner.run_test("Indefinite stop", test_processing_indefinite_stop, default_timeout)
    runner.run_test("join_in", test_processing_join_in, default_timeout)
    runner.run_test("Lives/retries", test_processing_lives, default_timeout)
    runner.run_test("Timeouts", test_processing_timeouts, default_timeout)
    runner.run_test("Timing access", test_processing_timing_access, default_timeout)
    runner.run_test("Async execution", test_processing_async_execution, default_timeout)
    runner.run_test("Background future", test_processing_background_future, default_timeout)
    runner.run_test("Pool map", test_processing_pool_map, default_timeout)
    runner.run_test("Pool star", test_processing_pool_star, default_timeout)
    runner.run_test("Pool unordered_map", test_processing_pool_unordered_map, default_timeout)
    runner.run_test("Pool imap", test_processing_pool_imap, default_timeout)
    runner.run_test("Pool unordered_imap", test_processing_pool_unordered_imap, default_timeout)
    runner.run_test("Pool timeout", test_processing_pool_timeout, default_timeout)
    runner.run_test("Pool background", test_processing_pool_background, default_timeout)
    runner.run_test("Pool async", test_processing_pool_async, default_timeout)
    runner.run_test("Pool with Skprocess", test_processing_pool_skprocess, default_timeout)
    runner.run_test("Pool star modifiers", test_processing_pool_star_modifiers, default_timeout)
    runner.run_test("Pool error handling", test_processing_pool_error_handling, default_timeout)
    runner.run_test("Share basic counter", test_processing_share_basic_counter, default_timeout)
    runner.run_test("Share timer", test_processing_share_timer, default_timeout)
    runner.run_test("Share context manager", test_processing_share_context_manager, default_timeout)
    runner.run_test("Share multiple objects", test_processing_share_multiple_objects, default_timeout)
    runner.run_test("Share single process", test_processing_share_single_process, default_timeout)
    runner.run_test("Share start/stop", test_processing_share_start_stop, default_timeout)
    runner.run_test("Share clear", test_processing_share_clear, default_timeout)
    runner.run_test("Pipe basic", test_processing_pipe_basic, default_timeout)
    runner.run_test("Pipe one-way", test_processing_pipe_one_way, default_timeout)
    runner.run_test("Pipe multiple", test_processing_pipe_multiple, default_timeout)
    runner.run_test("tell/listen", test_processing_tell_listen, default_timeout)
    runner.run_test("tell/listen async", test_processing_tell_listen_async, default_timeout)
    runner.run_test("autoreconnect decorator", test_processing_autoreconnect_decorator, default_timeout)
    runner.run_test("Full task queue", test_processing_full_task_queue, default_timeout)
    runner.run_test("Full pipeline", test_processing_full_pipeline, default_timeout)

    return runner.print_results()


if __name__ == "__main__":
    run_all_tests()
