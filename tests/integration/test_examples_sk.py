"""
Integration Tests for sk Examples

Validates the examples in suitkaise/_docs_copy/sk/examples.md
with detailed assertions.
"""

import asyncio
import json
import time
import tempfile
import sys

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import sk, blocking
from suitkaise.processing import Share
from suitkaise.sk import FunctionTimeoutError, SkModifierError
# Temp dir helper for file-based examples
def _tmp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="sk_examples_"))


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

def test_sk_decorate_function() -> None:
    tmp_path = _tmp_dir()

    @sk
    def load_users(path: Path) -> list[dict]:
        data = json.loads(path.read_text())
        return data["users"]

    data_path = tmp_path / "data" / "users.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps({"users": [{"id": 1, "name": "Ana"}]}))

    users = load_users(data_path)
    assert users == [{"id": 1, "name": "Ana"}], f"Unexpected users: {users}"


def test_sk_as_function() -> None:
    def streamline_format(text: str) -> str:
        return text.strip().lower().replace(" ", "-")

    streamline_format = sk(streamline_format)
    assert streamline_format("Hello World") == "hello-world"


def test_sk_chaining_modifiers() -> None:
    tmp_path = _tmp_dir()

    @sk
    def read_and_hash(path: Path) -> str:
        return __import__("hashlib").sha256(path.read_bytes()).hexdigest()

    data_path = tmp_path / "data" / "blob.bin"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_bytes(b"real data" * 50_000)

    digest_a = read_and_hash.retry(times=3, delay=0.01).timeout(1.0)(data_path)
    digest_b = read_and_hash.timeout(1.0).retry(times=3, delay=0.01)(data_path)
    assert digest_a == digest_b
    assert len(digest_a) == 64


def test_sk_timeout_handling() -> None:
    @sk
    def count_primes(limit: int) -> int:
        primes = []
        for n in range(2, limit):
            is_prime = True
            for p in primes:
                if p * p > n:
                    break
                if n % p == 0:
                    is_prime = False
                    break
            if is_prime:
                primes.append(n)
        return len(primes)

    try:
        count_primes.timeout(0.0001)(200_000)
        assert False, "Expected FunctionTimeoutError"
    except FunctionTimeoutError:
        pass


def test_sk_background_execution() -> None:
    tmp_path = _tmp_dir()

    @sk
    def hash_file(path: Path) -> str:
        return __import__("hashlib").sha256(path.read_bytes()).hexdigest()

    data_path = tmp_path / "data" / "large.bin"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_bytes(b"x" * 1_000_000)

    future = hash_file.background()(data_path)
    result = future.result()
    assert result == hash_file(data_path)


def test_sk_rate_limiting() -> None:
    tmp_path = _tmp_dir()

    @sk
    def file_size(path: Path) -> int:
        return path.stat().st_size

    data_path = tmp_path / "data" / "sample.txt"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("real content\n" * 100)

    limited = file_size.rate_limit(5.0)
    start = time.monotonic()
    sizes = [limited(data_path) for _ in range(3)]
    elapsed = time.monotonic() - start

    assert sizes == [data_path.stat().st_size] * 3
    assert elapsed >= 0.2


def test_sk_custom_retry_exceptions() -> None:
    tmp_path = _tmp_dir()

    class ApiError(RuntimeError):
        pass

    @sk
    def load_config(path: Path) -> dict:
        text = path.read_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            path.write_text(text + "}")
            raise ApiError("Config was incomplete, repaired and retrying")

    config_path = tmp_path / "data" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('{"name": "demo"')

    config = load_config.retry(times=2, delay=0.01, exceptions=(ApiError,))(config_path)
    assert config["name"] == "demo"


def test_sk_asynced_csv_sum() -> None:
    tmp_path = _tmp_dir()

    @sk
    def sum_csv(path: Path) -> int:
        total = 0
        with open(path, "r", newline="") as f:
            for row in __import__("csv").reader(f):
                total += int(row[0])
        return total

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(3):
        p = data_dir / f"numbers_{i}.csv"
        p.write_text("\n".join(str(n) for n in range(1, 100)))
        paths.append(p)

    async def main() -> list[int]:
        return await asyncio.gather(
            sum_csv.asynced()(paths[0]),
            sum_csv.asynced()(paths[1]),
            sum_csv.asynced()(paths[2]),
        )

    results = asyncio.run(main())
    assert results == [sum(range(1, 100))] * 3


def test_sk_async_retry_timeout() -> None:
    tmp_path = _tmp_dir()

    @sk
    def load_report(path: Path) -> dict:
        text = path.read_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            path.write_text(text + "}")
            raise ValueError("Report was incomplete, repaired and retrying")

    report_path = tmp_path / "data" / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('{"ok": true')

    async def main() -> dict:
        return await (
            load_report.asynced()
            .retry(times=2, delay=0.01, exceptions=(ValueError,))
            .timeout(0.5)
        )(report_path)

    report = asyncio.run(main())
    assert report == {"ok": True}


def test_sk_async_rate_limit() -> None:
    tmp_path = _tmp_dir()

    @sk
    def hash_text(path: Path) -> str:
        data = path.read_text().encode()
        return __import__("hashlib").sha256(data).hexdigest()

    data_path = tmp_path / "data" / "log.txt"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("log line\n" * 100)

    async def main() -> list[str]:
        limited = hash_text.asynced().rate_limit(20.0)
        return await asyncio.gather(*[limited(data_path) for _ in range(5)])

    results = asyncio.run(main())
    assert len(set(results)) == 1


def test_sk_blocking_detection() -> None:
    tmp_path = _tmp_dir()

    @sk
    def load_text(path: Path) -> str:
        with open(path, "r") as f:
            return f.read()

    data_path = tmp_path / "data" / "readme.txt"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("real text")

    assert load_text.has_blocking_calls is True
    assert load_text.blocking_calls


def test_sk_blocking_decorator_background() -> None:
    @sk
    @blocking
    def heavy_math(n: int) -> int:
        return sum(range(n))

    future = heavy_math.background()(10_000)
    assert future.result() == sum(range(10_000))


def test_sk_class_decorate_and_modifiers() -> None:
    tmp_path = _tmp_dir()

    @sk
    class DataStore:
        def __init__(self):
            self.data = {}

        def set(self, key: str, value: dict):
            self.data[key] = value

        def save(self, path: str):
            with open(path, "w") as f:
                f.write(json.dumps(self.data))

    store = DataStore()
    store.set("a", {"value": 1})
    output_path = tmp_path / "output.json"
    store.save(str(output_path))
    store.save.timeout(2.0)(str(output_path))
    assert json.loads(output_path.read_text()) == {"a": {"value": 1}}


def test_sk_class_level_async() -> None:
    tmp_path = _tmp_dir()

    @sk
    class FileReader:
        @blocking
        def read(self, path: Path) -> str:
            with open(path, "r") as f:
                return f.read()

    data_path = tmp_path / "data" / "message.txt"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("hello from disk")

    async def main() -> str:
        reader = FileReader()
        return await reader.read.asynced()(data_path)

    result = asyncio.run(main())
    assert result == "hello from disk"


def test_sk_modifier_error() -> None:
    @sk
    class Counter:
        def __init__(self):
            self.value = 0

        def inc(self):
            self.value += 1

    try:
        Counter.asynced()
        assert False, "Expected SkModifierError"
    except SkModifierError:
        pass


def test_sk_share_compatibility() -> None:
    @sk
    class Counter:
        def __init__(self):
            self.value = 0

        def inc(self):
            self.value += 1

    with Share() as share:
        share.counter = Counter()
        share.counter.inc()
        share.counter.inc()
        assert share.counter.value == 2


def test_sk_retry_timeout_background() -> None:
    tmp_path = _tmp_dir()

    @sk
    def load_payload(path: Path) -> dict:
        text = path.read_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            path.write_text(text + "}")
            raise RuntimeError("Payload incomplete, repaired and retrying")

    payload_path = tmp_path / "data" / "payload.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text('{"id": 1, "value": 42')

    future = (
        load_payload.retry(times=2, delay=0.01)
        .timeout(1.0)
        .background()
    )(payload_path)
    result = future.result()
    assert result == {"id": 1, "value": 42}


def test_sk_rate_limit_shared() -> None:
    tmp_path = _tmp_dir()

    @sk
    def read_lines(path: Path) -> int:
        return len(path.read_text().splitlines())

    log_path = tmp_path / "data" / "log.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("line\n" * 50)

    limited = read_lines.rate_limit(10.0)
    results = [limited(log_path) for _ in range(3)]
    assert results == [50, 50, 50]


def test_sk_full_script() -> None:
    class TransientError(RuntimeError):
        pass

    def seed_records() -> list[str]:
        payloads = []
        for record_id in range(1, 6):
            record = {"id": record_id, "value": record_id * 3}
            text = json.dumps(record)
            if record_id == 4:
                text = text[:-1]
            payloads.append(text)
        return payloads

    @sk
    @blocking
    def load_record(index: int, payloads: list[str]) -> dict:
        text = payloads[index]
        try:
            record = json.loads(text)
        except json.JSONDecodeError:
            payloads[index] = text + "}"
            raise TransientError("Record incomplete, repaired and retrying")
        return record

    @sk
    @blocking
    def score_record(record: dict) -> dict:
        payload = f"{record['id']}:{record['value']}".encode()
        digest = __import__("hashlib").sha256(payload).hexdigest()
        score = int(digest[:8], 16) % 1000
        return {**record, "score": score}

    async def main() -> list[dict]:
        payloads = seed_records()
        loader = (
            load_record.asynced()
            .retry(times=2, delay=0.01, exceptions=(TransientError,))
            .timeout(0.5)
            .rate_limit(20.0)
        )
        results = await asyncio.gather(
            *[loader(i, payloads) for i in range(len(payloads))],
            return_exceptions=True,
        )
        records = [r for r in results if isinstance(r, dict)]
        futures = [score_record.background()(record) for record in records]
        return [future.result() for future in futures]

    scored = asyncio.run(main())
    assert scored, "No scored records returned"
    assert all("score" in record for record in scored)


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    runner = TestRunner("Integration - sk Examples")

    runner.run_test("Decorate function", test_sk_decorate_function)
    runner.run_test("sk() as function", test_sk_as_function)
    runner.run_test("Chaining modifiers", test_sk_chaining_modifiers)
    runner.run_test("Timeout handling", test_sk_timeout_handling)
    runner.run_test("Background execution", test_sk_background_execution)
    runner.run_test("Rate limiting", test_sk_rate_limiting)
    runner.run_test("Custom retry exceptions", test_sk_custom_retry_exceptions)
    runner.run_test("Async CSV sum", test_sk_asynced_csv_sum)
    runner.run_test("Async retry + timeout", test_sk_async_retry_timeout)
    runner.run_test("Async rate limiting", test_sk_async_rate_limit)
    runner.run_test("Blocking detection", test_sk_blocking_detection)
    runner.run_test("Blocking decorator background", test_sk_blocking_decorator_background)
    runner.run_test("Class decorate + modifiers", test_sk_class_decorate_and_modifiers)
    runner.run_test("Class-level async", test_sk_class_level_async)
    runner.run_test("SkModifierError", test_sk_modifier_error)
    runner.run_test("Share compatibility", test_sk_share_compatibility)
    runner.run_test("Retry + timeout + background", test_sk_retry_timeout_background)
    runner.run_test("Rate limit shared", test_sk_rate_limit_shared)
    runner.run_test("Full script", test_sk_full_script)

    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
