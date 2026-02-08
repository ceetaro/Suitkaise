"""
Cucumber Module Benchmarks

Performance benchmarks for serialization:
- Primitive serialization speed
- Complex object serialization speed
- Comparison with pickle
"""

import sys
import time as stdlib_time
import pickle
import threading
import logging
import asyncio
import contextlib
import contextvars
import functools
import inspect
import mmap
import os
import queue
import re
import socket
import sqlite3
import subprocess
import tempfile
import types
import uuid
import weakref
from collections import deque, Counter, OrderedDict, defaultdict, ChainMap, namedtuple
from concurrent.futures import Future, ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, IntEnum, Flag, IntFlag
from fractions import Fraction
from pathlib import Path, PurePath, PosixPath, WindowsPath
from typing import NamedTuple, TypedDict
import multiprocessing
from multiprocessing import shared_memory

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _suppress_windows_invalid_handle() -> None:
    """Avoid noisy WinError 6 during handle finalization on Windows."""
    if os.name != "nt":
        return
    try:
        _orig_handle_close = subprocess.Handle.Close  # type: ignore[attr-defined]
    except Exception:
        _orig_handle_close = None
    if _orig_handle_close:
        def _safe_handle_close(self):
            try:
                return _orig_handle_close(self)
            except OSError as exc:
                if getattr(exc, "winerror", None) == 6:
                    return None
                raise
        subprocess.Handle.Close = _safe_handle_close  # type: ignore[attr-defined]
    try:
        import multiprocessing.connection as _mp_conn
    except Exception:
        return
    for _name in ("_close", "_CloseHandle"):
        if hasattr(_mp_conn, _name):
            _orig = getattr(_mp_conn, _name)
            def _safe_close(handle, _orig=_orig):
                try:
                    return _orig(handle)
                except OSError as exc:
                    if getattr(exc, "winerror", None) == 6:
                        return None
                    raise
            setattr(_mp_conn, _name, _safe_close)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))
_suppress_windows_invalid_handle()

from suitkaise.cucumber import (
    serialize,
    deserialize,
    reconnect_all,
    SerializationError,
    DeserializationError,
)
from suitkaise.timing import Sktimer, TimeThis
from suitkaise.circuits import Circuit, BreakingCircuit
from suitkaise.paths import Skpath, CustomRoot, PathDetectionError
from suitkaise.processing import (
    Skprocess,
    Pool,
    Share,
    ProcessTimers,
    ProcessError,
    PreRunError,
    RunError,
    PostRunError,
    OnFinishError,
    ResultError,
    ErrorHandlerError,
    ProcessTimeoutError,
    ResultTimeoutError,
)
from suitkaise.sk import SkModifierError, FunctionTimeoutError
from suitkaise.sk.api import Skclass, Skfunction
from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
from suitkaise.cucumber._int.handlers.pipe_handler import PipeReconnector
from suitkaise.cucumber._int.handlers.network_handler import (
    SocketReconnector,
    PostgresReconnector,
    MySQLReconnector,
    SQLiteReconnector,
    MongoReconnector,
    RedisReconnector,
    SQLAlchemyReconnector,
    CassandraReconnector,
    ElasticsearchReconnector,
    Neo4jReconnector,
    InfluxDBReconnector,
    ODBCReconnector,
    ClickHouseReconnector,
    MSSQLReconnector,
    OracleReconnector,
    SnowflakeReconnector,
    DuckDBReconnector,
)
from suitkaise.cucumber._int.handlers.subprocess_handler import SubprocessReconnector
from suitkaise.cucumber._int.handlers.threading_handler import ThreadReconnector
from suitkaise.cucumber._int.handlers.regex_handler import MatchReconnector, MatchObjectHandler


class _BenchEnum(Enum):
    A = 1


class _BenchIntEnum(IntEnum):
    A = 1


class _BenchFlag(Flag):
    A = 1


class _BenchIntFlag(IntFlag):
    A = 1

try:
    import dill
except Exception:
    dill = None

try:
    import cloudpickle
except Exception:
    cloudpickle = None


# =============================================================================
# Benchmark Infrastructure
# =============================================================================

class Benchmark:
    def __init__(self, name: str, ops_per_sec: float, us_per_op: float, extra: str = ""):
        self.name = name
        self.ops_per_sec = ops_per_sec
        self.us_per_op = us_per_op
        self.extra = extra


class BenchmarkRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def bench(self, name: str, iterations: int, func, *args, **kwargs):
        for _ in range(min(100, iterations // 10)):
            func(*args, **kwargs)
        
        start = stdlib_time.perf_counter()
        for _ in range(iterations):
            func(*args, **kwargs)
        elapsed = stdlib_time.perf_counter() - start
        
        ops_per_sec = iterations / elapsed
        us_per_op = (elapsed / iterations) * 1_000_000
        
        self.results.append(Benchmark(name, ops_per_sec, us_per_op))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*80}{self.RESET}\n")
        
        print(f"  {'Benchmark':<40} {'ops/sec':>15} {'µs/op':>12}")
        print(f"  {'-'*40} {'-'*15} {'-'*12}")
        
        for result in self.results:
            print(f"  {result.name:<40} {result.ops_per_sec:>15,.0f} {result.us_per_op:>12.3f}")
        
        print(f"\n{self.BOLD}{'-'*80}{self.RESET}\n")


class CompatibilityResult:
    def __init__(self, type_name: str, library: str, success: bool, us_per_op: float | None, error: str = ""):
        self.type_name = type_name
        self.library = library
        self.success = success
        self.us_per_op = us_per_op
        self.error = error


class CompatibilityRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results: list[CompatibilityResult] = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.ORANGE = '\033[38;5;208m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def check(self, type_name: str, library: str, func):
        start = stdlib_time.perf_counter()
        try:
            func()
            elapsed = stdlib_time.perf_counter() - start
            self.results.append(CompatibilityResult(type_name, library, True, elapsed * 1_000_000))
        except Exception as e:
            self.results.append(CompatibilityResult(type_name, library, False, None, f"{type(e).__name__}: {e}"))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*110}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^110}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*110}{self.RESET}\n")
        
        headers = ["Type", "cucumber", "pickle", "dill", "cloudpickle"]
        print(f"  {headers[0]:<30} {headers[1]:>18} {headers[2]:>18} {headers[3]:>18} {headers[4]:>18}")
        print(f"  {'-'*30} {'-'*18} {'-'*18} {'-'*18} {'-'*18}")
        
        by_type: dict[str, dict[str, CompatibilityResult]] = {}
        for result in self.results:
            by_type.setdefault(result.type_name, {})[result.library] = result
        
        def _strip_ansi(text: str) -> str:
            import re
            return re.sub(r"\x1b\[[0-9;]*m", "", text)
        
        def _pad_cell(text: str, width: int) -> str:
            visible = len(_strip_ansi(text))
            if visible >= width:
                return text
            return text + (" " * (width - visible))
        
        for type_name, libs in by_type.items():
            def format_cell(lib_name: str) -> str:
                res = libs.get(lib_name)
                if res is None:
                    return f"{self.YELLOW}n/a{self.RESET}"
                if res.success:
                    return f"{self.GREEN}{res.us_per_op:.1f}µs{self.RESET}"
                return f"{self.ORANGE}fail{self.RESET}"
            
            cucumber_cell = _pad_cell(format_cell("cucumber"), 18)
            pickle_cell = _pad_cell(format_cell("pickle"), 18)
            dill_cell = _pad_cell(format_cell("dill"), 18)
            cloud_cell = _pad_cell(format_cell("cloudpickle"), 18)
            print(
                f"  {type_name:<30} {cucumber_cell} {pickle_cell} "
                f"{dill_cell} {cloud_cell}"
            )
        
        failures = [r for r in self.results if not r.success]
        cucumber_failures = [r for r in failures if r.library == "cucumber"]
        if failures:
            if cucumber_failures:
                print(f"\n{self.BOLD}{self.ORANGE}Cucumber failures:{self.RESET}")
                for fail in cucumber_failures:
                    print(f"  - {self.ORANGE}{fail.type_name}{self.RESET}: {fail.error}")
            print(f"\n{self.BOLD}{self.ORANGE}Failures:{self.RESET}")
            for fail in failures:
                print(f"  - {self.ORANGE}{fail.type_name}{self.RESET} ({fail.library}): {fail.error}")
        
        print(f"\n{self.BOLD}{'-'*110}{self.RESET}\n")


# =============================================================================
# Reconnector Showcase
# =============================================================================

class ReconnectorShowcaseResult:
    def __init__(self, name: str, status: str, detail: str = "", error: str = ""):
        self.name = name
        self.status = status
        self.detail = detail
        self.error = error


class ReconnectorShowcaseRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results: list[ReconnectorShowcaseResult] = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def add(self, name: str, func):
        try:
            detail = func()
            self.results.append(ReconnectorShowcaseResult(name, "ok", detail=detail))
        except Exception as e:
            self.results.append(ReconnectorShowcaseResult(name, "fail", error=f"{type(e).__name__}: {e}"))
    
    def skip(self, name: str, reason: str):
        self.results.append(ReconnectorShowcaseResult(name, "skip", detail=reason))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*80}{self.RESET}\n")
        
        for result in self.results:
            if result.status == "ok":
                status = f"{self.GREEN}✓ OK{self.RESET}"
                detail = f" - {result.detail}" if result.detail else ""
                print(f"  {status}  {result.name}{detail}")
            elif result.status == "skip":
                status = f"{self.YELLOW}• SKIP{self.RESET}"
                detail = f" - {result.detail}" if result.detail else ""
                print(f"  {status}  {result.name}{detail}")
            else:
                status = f"{self.RED}✗ FAIL{self.RESET}"
                detail = f" - {result.error}" if result.error else ""
                print(f"  {status}  {result.name}{detail}")
        
        print(f"\n{self.BOLD}{'-'*80}{self.RESET}\n")


def _roundtrip_reconnector(obj):
    data = serialize(obj)
    restored = deserialize(data)
    reconnected = reconnect_all(restored)
    return restored, reconnected


def _extract_reconnected_value(reconnected):
    if isinstance(reconnected, dict) and "value" in reconnected:
        return reconnected["value"]
    return reconnected


def _pipe_end():
    conn1, conn2 = multiprocessing.Pipe()
    conn2.close()
    return conn1


@contextmanager
def _reconnector_payload(name, factory):
    obj = factory()
    try:
        yield obj
    finally:
        # cleanup for common types
        if name == "socket.socket" and isinstance(obj, socket.socket):
            obj.close()
        if name == "sqlite3.Connection" and isinstance(obj, sqlite3.Connection):
            obj.close()
        if name == "subprocess.Popen" and isinstance(obj, subprocess.Popen):
            try:
                obj.terminate()
                obj.wait(timeout=5)
            except Exception:
                pass
            for stream in (obj.stdin, obj.stdout, obj.stderr):
                if stream:
                    with contextlib.suppress(Exception):
                        stream.close()
        if name == "multiprocessing.Pipe":
            try:
                if isinstance(obj, multiprocessing.connection.Connection):
                    obj.close()
            except Exception:
                pass


def benchmark_reconnector_showcase():
    runner = ReconnectorShowcaseRunner("Reconnector Showcase (serialize → reconnect)")
    
    def add_roundtrip(name, factory, expected_type):
        def _run():
            with _reconnector_payload(name, factory) as obj:
                restored, reconnected = _roundtrip_reconnector(obj)
                value = _extract_reconnected_value(reconnected)
                return f"{type(restored).__name__} → {type(value).__name__}"
        runner.add(name, _run)
    
    # Objects that serialize into reconnectors
    add_roundtrip("socket.socket", lambda: socket.socket(), socket.socket)
    add_roundtrip("multiprocessing.Pipe", _pipe_end, object)
    add_roundtrip(
        "subprocess.Popen",
        lambda: subprocess.Popen([sys.executable, "-c", "pass"], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
        subprocess.Popen,
    )
    add_roundtrip("threading.Thread", lambda: threading.Thread(target=lambda: None), threading.Thread)
    add_roundtrip("re.Match", lambda: re.search(r"a(b)c", "zabc"), re.Match)
    add_roundtrip("sqlite3.Connection", lambda: sqlite3.connect(":memory:"), sqlite3.Connection)
    
    # Reconnector classes (network/db types)
    reconnector_classes = [
        ("PostgresReconnector", PostgresReconnector(details={"host": "localhost", "database": "db"})),
        ("MySQLReconnector", MySQLReconnector(details={"host": "localhost", "database": "db"})),
        ("SQLiteReconnector", SQLiteReconnector(details={"path": ":memory:"})),
        ("MongoReconnector", MongoReconnector(details={"host": "localhost"})),
        ("RedisReconnector", RedisReconnector(details={"host": "localhost"})),
        ("SQLAlchemyReconnector", SQLAlchemyReconnector(details={"url": "sqlite:///:memory:"})),
        ("CassandraReconnector", CassandraReconnector(details={"hosts": ["localhost"]})),
        ("ElasticsearchReconnector", ElasticsearchReconnector(details={"hosts": ["localhost"]})),
        ("Neo4jReconnector", Neo4jReconnector(details={"uri": "bolt://localhost:7687"})),
        ("InfluxDBReconnector", InfluxDBReconnector(details={"url": "http://localhost:8086"})),
        ("ODBCReconnector", ODBCReconnector(details={"dsn": "example"})),
        ("ClickHouseReconnector", ClickHouseReconnector(details={"host": "localhost"})),
        ("MSSQLReconnector", MSSQLReconnector(details={"host": "localhost"})),
        ("OracleReconnector", OracleReconnector(details={"dsn": "localhost"})),
        ("SnowflakeReconnector", SnowflakeReconnector(details={"account": "acct"})),
        ("DuckDBReconnector", DuckDBReconnector(details={"path": ":memory:"})),
    ]
    
    for name, reconnector in reconnector_classes:
        def _make_run(rec=reconnector):
            restored, reconnected = _roundtrip_reconnector(rec)
            return f"{type(restored).__name__} → {type(reconnected).__name__}"
        runner.add(name, _make_run)
    
    return runner

# =============================================================================
# Test Data
# =============================================================================

class SimpleClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class ClassWithLock:
    def __init__(self, value):
        self.value = value
        self.lock = threading.Lock()


class _BenchCustomClass:
    def __init__(self, value):
        self.value = value
    def get_value(self):
        return self.value


class _BenchSkClassDemo:
    def __init__(self):
        self.value = 1
    def inc(self):
        self.value += 1


# =============================================================================
# Primitive Benchmarks
# =============================================================================

def benchmark_primitives():
    """Measure primitive serialization speed."""
    runner = BenchmarkRunner("Primitive Serialization Benchmarks")
    
    # Integer
    runner.bench("cucumber: int", 10_000, lambda: serialize(42))
    runner.bench("pickle: int", 50_000, lambda: pickle.dumps(42))
    
    # String
    runner.bench("cucumber: str", 10_000, lambda: serialize("hello world"))
    runner.bench("pickle: str", 50_000, lambda: pickle.dumps("hello world"))
    
    # List
    test_list = [1, 2, 3, 4, 5]
    runner.bench("cucumber: list[5]", 5_000, lambda: serialize(test_list))
    runner.bench("pickle: list[5]", 20_000, lambda: pickle.dumps(test_list))
    
    # Dict
    test_dict = {"a": 1, "b": 2, "c": 3}
    runner.bench("cucumber: dict[3]", 5_000, lambda: serialize(test_dict))
    runner.bench("pickle: dict[3]", 20_000, lambda: pickle.dumps(test_dict))
    
    return runner


def benchmark_deserialization():
    """Measure deserialization speed."""
    runner = BenchmarkRunner("Deserialization Benchmarks")
    
    # Pre-serialize data
    int_data = serialize(42)
    str_data = serialize("hello world")
    list_data = serialize([1, 2, 3, 4, 5])
    dict_data = serialize({"a": 1, "b": 2, "c": 3})
    
    int_pickle = pickle.dumps(42)
    str_pickle = pickle.dumps("hello world")
    list_pickle = pickle.dumps([1, 2, 3, 4, 5])
    
    runner.bench("cucumber: deserialize int", 10_000, lambda: deserialize(int_data))
    runner.bench("pickle: loads int", 50_000, lambda: pickle.loads(int_pickle))
    
    runner.bench("cucumber: deserialize str", 10_000, lambda: deserialize(str_data))
    runner.bench("pickle: loads str", 50_000, lambda: pickle.loads(str_pickle))
    
    runner.bench("cucumber: deserialize list", 5_000, lambda: deserialize(list_data))
    runner.bench("pickle: loads list", 20_000, lambda: pickle.loads(list_pickle))
    
    return runner


# =============================================================================
# Complex Object Benchmarks
# =============================================================================

def benchmark_complex():
    """Measure complex object serialization speed."""
    runner = BenchmarkRunner("Complex Object Serialization Benchmarks")
    
    # Simple class (pickle can handle)
    simple = SimpleClass(1, 2)
    runner.bench("cucumber: SimpleClass", 2_000, lambda: serialize(simple))
    runner.bench("pickle: SimpleClass", 10_000, lambda: pickle.dumps(simple))
    
    # Class with lock (pickle cannot handle)
    with_lock = ClassWithLock(42)
    runner.bench("cucumber: ClassWithLock", 2_000, lambda: serialize(with_lock))
    # pickle.dumps(with_lock) would fail
    
    # Nested structure
    nested = {"data": [SimpleClass(i, i*2) for i in range(5)]}
    runner.bench("cucumber: nested structure", 1_000, lambda: serialize(nested))
    runner.bench("pickle: nested structure", 5_000, lambda: pickle.dumps(nested))
    
    return runner


# =============================================================================
# Large Data Benchmarks
# =============================================================================

def benchmark_large_data():
    """Measure large data serialization speed."""
    runner = BenchmarkRunner("Large Data Serialization Benchmarks")
    
    # Large list
    large_list = list(range(1000))
    runner.bench("cucumber: list[1000]", 500, lambda: serialize(large_list))
    runner.bench("pickle: list[1000]", 2_000, lambda: pickle.dumps(large_list))
    
    # Large dict
    large_dict = {str(i): i for i in range(500)}
    runner.bench("cucumber: dict[500]", 200, lambda: serialize(large_dict))
    runner.bench("pickle: dict[500]", 1_000, lambda: pickle.dumps(large_dict))
    
    # Large string
    large_str = "x" * 10000
    runner.bench("cucumber: str[10000]", 1_000, lambda: serialize(large_str))
    runner.bench("pickle: str[10000]", 5_000, lambda: pickle.dumps(large_str))
    
    return runner


# =============================================================================
# Round-Trip Benchmarks
# =============================================================================

def benchmark_roundtrip():
    """Measure full round-trip (serialize + deserialize)."""
    runner = BenchmarkRunner("Round-Trip Benchmarks")
    
    def cucumber_roundtrip(obj):
        return deserialize(serialize(obj))
    
    def pickle_roundtrip(obj):
        return pickle.loads(pickle.dumps(obj))
    
    test_data = {"users": [{"name": f"user{i}", "age": 20 + i} for i in range(10)]}
    
    runner.bench("cucumber: roundtrip dict", 500, lambda: cucumber_roundtrip(test_data))
    runner.bench("pickle: roundtrip dict", 2_000, lambda: pickle_roundtrip(test_data))
    
    simple = SimpleClass(100, 200)
    runner.bench("cucumber: roundtrip SimpleClass", 1_000, lambda: cucumber_roundtrip(simple))
    runner.bench("pickle: roundtrip SimpleClass", 5_000, lambda: pickle_roundtrip(simple))
    runner.bench("cucumber: reconnect_all", 500, lambda: reconnect_all(_reconnect_all_payload()))
    
    return runner


# =============================================================================
# Worst Possible Object Benchmarks
# =============================================================================

def benchmark_worst_possible_object():
    """Measure serialization for WorstPossibleObject."""
    runner = BenchmarkRunner("WorstPossibleObject Benchmarks")
    
    wpo = WorstPossibleObject()
    
    runner.bench("cucumber: WorstPossibleObject serialize", 5, lambda: serialize(wpo))
    wpo_bytes = serialize(wpo)
    runner.bench("cucumber: WorstPossibleObject deserialize", 5, lambda: deserialize(wpo_bytes))
    runner.bench("cucumber: WorstPossibleObject roundtrip", 3, lambda: deserialize(serialize(wpo)))
    
    if hasattr(wpo, "cleanup"):
        wpo.cleanup()
    
    return runner


# =============================================================================
# Supported Types Compatibility Benchmarks
# =============================================================================

@contextmanager
def _temp_file_handle():
    handle = tempfile.NamedTemporaryFile()
    try:
        yield handle
    finally:
        handle.close()


@contextmanager
def _spooled_temp():
    f = tempfile.SpooledTemporaryFile()
    try:
        yield f
    finally:
        f.close()


@contextmanager
def _file_io_handle():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.close()
        f = __import__("io").FileIO(tmp.name, mode="r")
        try:
            yield f
        finally:
            f.close()
    finally:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass


@contextmanager
def _buffered_reader_handle():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.close()
        with open(tmp.name, "rb") as raw:
            reader = __import__("io").BufferedReader(raw)
            try:
                yield reader
            finally:
                reader.close()
    finally:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass


@contextmanager
def _buffered_writer_handle():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.close()
        with open(tmp.name, "wb") as raw:
            writer = __import__("io").BufferedWriter(raw)
            try:
                yield writer
            finally:
                writer.close()
    finally:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass


@contextmanager
def _mmap_handle():
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(b"0" * 1024)
        tmp.flush()
        mm = mmap.mmap(tmp.fileno(), 0)
        try:
            yield mm
        finally:
            mm.close()


@contextmanager
def _sqlite_conn():
    conn = sqlite3.connect(":memory:")
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def _sqlite_cursor():
    with _sqlite_conn() as conn:
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()


@contextmanager
def _socket_handle():
    s = socket.socket()
    try:
        yield s
    finally:
        s.close()


@contextmanager
def _subprocess_popen():
    proc = subprocess.Popen([sys.executable, "-c", "pass"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        yield proc
    finally:
        with contextlib.suppress(Exception):
            proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream:
                with contextlib.suppress(Exception):
                    stream.close()


@contextmanager
def _shared_memory():
    shm = shared_memory.SharedMemory(create=True, size=16)
    try:
        yield shm
    finally:
        shm.close()
        shm.unlink()


@contextmanager
def _manager():
    manager = multiprocessing.Manager()
    try:
        yield manager
    finally:
        manager.shutdown()


@contextmanager
def _pipe():
    conn1, conn2 = multiprocessing.Pipe()
    try:
        yield (conn1, conn2)
    finally:
        conn1.close()
        conn2.close()


def _reconnect_all_payload():
    match = re.search(r"a(b)c", "zabc")
    match_state = MatchObjectHandler().extract_state(match)
    return {
        "pipe": PipeReconnector(),
        "socket": SocketReconnector(state={
            "family": socket.AF_INET,
            "type": socket.SOCK_STREAM,
            "proto": 0,
            "timeout": None,
            "blocking": True,
            "local_addr": None,
            "remote_addr": None,
        }),
        "db": SQLiteReconnector(details={"path": ":memory:"}),
        "proc": SubprocessReconnector(state={
            "args": [sys.executable, "-c", "pass"],
            "returncode": 0,
            "pid": 123,
            "poll_result": 0,
            "stdout_data": None,
            "stderr_data": None,
        }),
        "match": MatchReconnector(state=match_state),
        "thread": ThreadReconnector(state={
            "name": "worker",
            "daemon": True,
            "target": lambda: None,
            "args": (),
            "kwargs": {},
            "is_alive": False,
        }),
        "nested": {
            "list": [PipeReconnector(), SQLiteReconnector(details={"path": ":memory:"})]
        }
    }


@contextmanager
def _asyncio_loop():
    loop = asyncio.new_event_loop()
    try:
        prev_loop = asyncio.get_event_loop()
    except RuntimeError:
        prev_loop = None
    try:
        asyncio.set_event_loop(loop)
        yield loop
    finally:
        loop.close()
        asyncio.set_event_loop(prev_loop)


@contextmanager
def _asyncio_future():
    with _asyncio_loop() as loop:
        fut = loop.create_future()
        fut.set_result(1)
        yield fut


@contextmanager
def _asyncio_task():
    async def _coro():
        return 1
    with _asyncio_loop() as loop:
        task = loop.create_task(_coro())
        yield task
        if not task.done():
            task.cancel()
        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass


@contextmanager
def _coroutine_obj():
    async def _coro():
        return 1
    coro = _coro()
    try:
        yield coro
    finally:
        coro.close()


@contextmanager
def _async_generator_obj():
    async def _agen():
        yield 1
    ag = _agen()
    try:
        yield ag
    finally:
        with _asyncio_loop() as loop:
            loop.run_until_complete(ag.aclose())


@contextmanager
def _requests_session():
    try:
        import requests  # type: ignore
    except Exception:
        yield None
        return
    sess = requests.Session()
    try:
        yield sess
    finally:
        sess.close()


@contextmanager
def _file_handler():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    handler = logging.FileHandler(path)
    try:
        yield handler
    finally:
        handler.close()
        try:
            os.remove(path)
        except OSError:
            pass


@contextmanager
def _thread_pool_executor():
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        yield executor
    finally:
        executor.shutdown(wait=True)


@contextmanager
def _process_pool_executor():
    executor = ProcessPoolExecutor(max_workers=1)
    try:
        yield executor
    finally:
        executor.shutdown(wait=True)


@contextmanager
def _file_descriptor():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.close()
        fd = os.open(tmp.name, os.O_RDONLY)
        try:
            yield fd
        finally:
            os.close(fd)
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass


@contextmanager
def _frame_object():
    frame = inspect.currentframe()
    try:
        yield frame
    finally:
        del frame


def _get_supported_objects():
    class _Descriptor:
        def __get__(self, obj, objtype=None):
            return 1
    class _Context:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
    class _WeakRefTarget:
        pass
    class _DemoProcess(Skprocess):
        def __init__(self):
            self.value = 1
        def __run__(self):
            self.value += 1
        def __result__(self):
            return self.value
    class _NamedTuple(NamedTuple):
        x: int
    class _TypedDict(TypedDict):
        x: int
    Nt = namedtuple("Nt", ["x"])

    def _sample_func():
        return 1
    def _blocking_func():
        import time as _time
        _time.sleep(0)
        return 1
    def _sample_gen():
        yield 1
    def _sample_async_gen():
        yield 1

    @contextmanager
    def _pipe_fds():
        r, w = os.pipe()
        try:
            yield (r, w)
        finally:
            os.close(r)
            os.close(w)

    @contextmanager
    def _contextmanager_function():
        @contextmanager
        def _ctx():
            yield "ok"
        yield _ctx


    @contextmanager
    def _contextvar_token():
        var = contextvars.ContextVar("x")
        token = var.set(1)
        try:
            yield token
        finally:
            var.reset(token)
    
    @dataclass
    class _Dataclass:
        x: int
    
    objects = [
        ("None", lambda: None),
        ("bool", lambda: True),
        ("int", lambda: 1),
        ("float", lambda: 1.5),
        ("complex", lambda: 1 + 2j),
        ("str", lambda: "hello"),
        ("bytes", lambda: b"bytes"),
        ("bytearray", lambda: bytearray(b"bytes")),
        ("Ellipsis", lambda: Ellipsis),
        ("NotImplemented", lambda: NotImplemented),
        ("list", lambda: [1, 2, 3]),
        ("tuple", lambda: (1, 2, 3)),
        ("dict", lambda: {"a": 1}),
        ("set", lambda: {1, 2}),
        ("frozenset", lambda: frozenset({1, 2})),
        ("range", lambda: range(10)),
        ("slice", lambda: slice(0, 10, 2)),
        ("deque", lambda: deque([1, 2])),
        ("Counter", lambda: Counter({"a": 1})),
        ("OrderedDict", lambda: OrderedDict([("a", 1)])),
        ("defaultdict", lambda: defaultdict(int, {"a": 1})),
        ("ChainMap", lambda: ChainMap({"a": 1}, {"b": 2})),
        ("namedtuple", lambda: Nt(1)),
        ("datetime", lambda: __import__("datetime").datetime.utcnow()),
        ("date", lambda: __import__("datetime").date.today()),
        ("time", lambda: __import__("datetime").time(12, 0, 0)),
        ("timedelta", lambda: __import__("datetime").timedelta(seconds=1)),
        ("timezone", lambda: __import__("datetime").timezone.utc),
        ("Decimal", lambda: Decimal("1.5")),
        ("Fraction", lambda: Fraction(1, 3)),
        ("UUID", lambda: uuid.uuid4()),
        ("Path", lambda: Path.cwd()),
        ("PurePath", lambda: PurePath("a/b")),
        ("PosixPath", lambda: PosixPath("/tmp") if os.name != "nt" else None),
        ("WindowsPath", lambda: WindowsPath("C:/Temp") if os.name == "nt" else None),
        ("Logger", lambda: logging.getLogger("cucumber_bench")),
        ("StreamHandler", lambda: logging.StreamHandler()),
        ("FileHandler", _file_handler),
        ("Formatter", lambda: logging.Formatter("%(message)s")),
        ("threading.Lock", threading.Lock),
        ("threading.RLock", threading.RLock),
        ("threading.Semaphore", threading.Semaphore),
        ("threading.BoundedSemaphore", threading.BoundedSemaphore),
        ("threading.Barrier", lambda: threading.Barrier(1)),
        ("threading.Condition", threading.Condition),
        ("threading.Event", threading.Event),
        ("threading.Thread", lambda: threading.Thread(target=lambda: None)),
        ("threading.local", threading.local),
        ("multiprocessing.Queue", multiprocessing.Queue),
        ("multiprocessing.Event", multiprocessing.Event),
        ("multiprocessing.Pipe", _pipe),
        ("multiprocessing.Manager", _manager),
        ("SharedMemory", _shared_memory),
        ("queue.Queue", queue.Queue),
        ("queue.LifoQueue", queue.LifoQueue),
        ("queue.PriorityQueue", queue.PriorityQueue),
        ("queue.SimpleQueue", queue.SimpleQueue),
        ("TextIOWrapper", _temp_file_handle),
        ("BufferedReader", _buffered_reader_handle),
        ("BufferedWriter", _buffered_writer_handle),
        ("FileIO", _file_io_handle),
        ("StringIO", lambda: __import__("io").StringIO("hi")),
        ("BytesIO", lambda: __import__("io").BytesIO(b"hi")),
        ("NamedTemporaryFile", _temp_file_handle),
        ("SpooledTemporaryFile", _spooled_temp),
        ("mmap", _mmap_handle),
        ("re.Pattern", lambda: re.compile("abc")),
        ("re.Match", lambda: re.match("abc", "abc")),
        ("sqlite3.Connection", _sqlite_conn),
        ("sqlite3.Cursor", _sqlite_cursor),
        ("requests.Session", _requests_session),
        ("socket.socket", _socket_handle),
        ("FunctionType", lambda: _sample_func),
        ("lambda", lambda: (lambda x: x + 1)),
        ("functools.partial", lambda: functools.partial(_sample_func)),
        ("MethodType", lambda: types.MethodType(_sample_func, object())),
        ("staticmethod", lambda: staticmethod(_sample_func)),
        ("classmethod", lambda: classmethod(lambda cls: 1)),
        ("GeneratorType", lambda: _sample_gen()),
        ("range_iterator", lambda: iter(range(3))),
        ("enumerate", lambda: enumerate([1, 2])),
        ("zip", lambda: zip([1], [2])),
        ("map", lambda: map(lambda x: x + 1, [1, 2])),
        ("filter", lambda: filter(lambda x: x > 0, [1, -1])),
        ("CoroutineType", _coroutine_obj),
        ("AsyncGeneratorType", _async_generator_obj),
        ("asyncio.Task", _asyncio_task),
        ("asyncio.Future", _asyncio_future),
        ("concurrent.futures.Future", lambda: Future()),
        ("ThreadPoolExecutor", _thread_pool_executor),
        ("ProcessPoolExecutor", _process_pool_executor),
        ("weakref.ref", lambda: weakref.ref(_WeakRefTarget())),
        ("WeakValueDictionary", lambda: weakref.WeakValueDictionary()),
        ("WeakKeyDictionary", lambda: weakref.WeakKeyDictionary()),
        ("Enum", lambda: _BenchEnum.A),
        ("IntEnum", lambda: _BenchIntEnum.A),
        ("Flag", lambda: _BenchFlag.A),
        ("IntFlag", lambda: _BenchIntFlag.A),
        ("ContextVar", lambda: contextvars.ContextVar("x")),
        ("Token", _contextvar_token),
        ("contextmanager", _contextmanager_function),
        ("ContextObject", lambda: _Context()),
        ("subprocess.Popen", _subprocess_popen),
        ("CompletedProcess", lambda: subprocess.CompletedProcess(["echo"], 0)),
        ("CodeType", lambda: _sample_func.__code__),
        ("FrameType", _frame_object),
        ("property", lambda: property(lambda self: 1)),
        ("CustomDescriptor", lambda: _Descriptor()),
        ("ModuleType", lambda: types.ModuleType("mod")),
        ("OS pipes", _pipe_fds),
        ("File descriptors", _file_descriptor),
        ("PipeReconnector", lambda: PipeReconnector()),
        ("SQLiteReconnector", lambda: SQLiteReconnector(details={"path": ":memory:"})),
        ("typing.NamedTuple", lambda: _NamedTuple(1)),
        ("typing.TypedDict", lambda: _TypedDict(x=1)),
        ("Class object", lambda: _BenchCustomClass),
        ("Class instance", lambda: _BenchCustomClass(1)),
        ("dataclass", lambda: _Dataclass(1)),
        ("slots class", lambda: type("S", (), {"__slots__": ("x",), "__init__": lambda self: setattr(self, "x", 1)})()),
        ("slots+dict class", lambda: type("SD", (), {"__slots__": ("x", "__dict__"), "__init__": lambda self: setattr(self, "x", 1)})()),
        ("Sktimer", lambda: Sktimer()),
        ("TimeThis", lambda: TimeThis()),
        ("Circuit", lambda: Circuit(num_shorts_to_trip=1)),
        ("BreakingCircuit", lambda: BreakingCircuit(num_shorts_to_trip=1)),
        ("Skpath", lambda: Skpath("file.txt")),
        ("CustomRoot", lambda: CustomRoot(os.getcwd())),
        ("Skprocess", lambda: _DemoProcess()),
        ("Pool", lambda: Pool(workers=1)),
        ("Share", lambda: Share()),
        ("ProcessTimers", lambda: ProcessTimers()),
        ("ProcessError", lambda: ProcessError("error")),
        ("PreRunError", lambda: PreRunError(0)),
        ("RunError", lambda: RunError(0)),
        ("PostRunError", lambda: PostRunError(0)),
        ("OnFinishError", lambda: OnFinishError(0)),
        ("ResultError", lambda: ResultError(0)),
        ("ErrorHandlerError", lambda: ErrorHandlerError(0)),
        ("ProcessTimeoutError", lambda: ProcessTimeoutError("run", 1.0, 0)),
        ("ResultTimeoutError", lambda: ResultTimeoutError("timeout")),
        ("PathDetectionError", lambda: PathDetectionError("path error")),
        ("SerializationError", lambda: SerializationError("serialization error")),
        ("DeserializationError", lambda: DeserializationError("deserialization error")),
        ("SkModifierError", lambda: SkModifierError("not asynced")),
        ("FunctionTimeoutError", lambda: FunctionTimeoutError("timeout")),
        ("Skclass", lambda: Skclass(_BenchSkClassDemo)),
        ("Skfunction", lambda: Skfunction(_sample_func)),
        ("Skfunction.asynced()", lambda: Skfunction(_blocking_func).asynced()),
    ]
    return objects


def _cleanup_object(obj):
    if obj is None:
        return
    try:
        if isinstance(obj, subprocess.Popen):
            with contextlib.suppress(Exception):
                obj.terminate()
            with contextlib.suppress(Exception):
                obj.wait(timeout=5)
            for stream in (obj.stdin, obj.stdout, obj.stderr):
                if stream:
                    with contextlib.suppress(Exception):
                        stream.close()
            return
        if isinstance(obj, multiprocessing.connection.Connection):
            with contextlib.suppress(Exception):
                obj.close()
            return
        if isinstance(obj, socket.socket):
            with contextlib.suppress(Exception):
                obj.close()
            return
        if isinstance(obj, sqlite3.Cursor):
            with contextlib.suppress(Exception):
                obj.close()
            return
        if isinstance(obj, sqlite3.Connection):
            with contextlib.suppress(Exception):
                obj.close()
            return
        if isinstance(obj, logging.Handler):
            with contextlib.suppress(Exception):
                obj.close()
            return
    except Exception:
        return
    if hasattr(obj, "close"):
        with contextlib.suppress(Exception):
            obj.close()
    if hasattr(obj, "join_thread"):
        with contextlib.suppress(Exception):
            obj.join_thread()
    if hasattr(obj, "shutdown"):
        with contextlib.suppress(Exception):
            obj.shutdown()
    if hasattr(obj, "terminate"):
        with contextlib.suppress(Exception):
            obj.terminate()
    if hasattr(obj, "join"):
        with contextlib.suppress(Exception):
            obj.join(timeout=0)


def benchmark_supported_types_compatibility():
    """Attempt serialization of every supported type across serializers."""
    runner = CompatibilityRunner("Supported Types Compatibility Benchmarks")
    libs = {
        "cucumber": lambda obj: serialize(obj),
        "pickle": lambda obj: pickle.dumps(obj),
        "dill": (lambda obj: dill.dumps(obj)) if dill else None,
        "cloudpickle": (lambda obj: cloudpickle.dumps(obj)) if cloudpickle else None,
    }
    
    missing = [name for name, func in libs.items() if func is None]
    if missing:
        print(f"  [warning] Missing serializers: {', '.join(missing)} (install to compare)")
    
    for type_name, factory in _get_supported_objects():
        obj_or_cm = factory() if callable(factory) else factory
        if hasattr(obj_or_cm, "__enter__"):
            with obj_or_cm as obj:
                if obj is None:
                    continue
                for lib_name, func in libs.items():
                    if func is None:
                        continue
                    runner.check(type_name, lib_name, lambda f=func, o=obj: f(o))
        else:
            if obj_or_cm is None:
                continue
            for lib_name, func in libs.items():
                if func is None:
                    continue
                runner.check(type_name, lib_name, lambda f=func, o=obj_or_cm: f(o))
            _cleanup_object(obj_or_cm)
    
    return runner


def benchmark_supported_types_throughput():
    """Measure cucumber throughput across all supported types."""
    runner = BenchmarkRunner("Supported Types Throughput (cucumber)")
    
    for type_name, factory in _get_supported_objects():
        obj_or_cm = factory() if callable(factory) else factory
        if hasattr(obj_or_cm, "__enter__"):
            with obj_or_cm as obj:
                if obj is None:
                    continue
                try:
                    runner.bench(f"cucumber: {type_name}", 200, lambda o=obj: serialize(o))
                except Exception as e:
                    print(f"  [skip] cucumber: {type_name} ({type(e).__name__}: {e})")
        else:
            if obj_or_cm is None:
                continue
            try:
                runner.bench(f"cucumber: {type_name}", 200, lambda o=obj_or_cm: serialize(o))
            except Exception as e:
                print(f"  [skip] cucumber: {type_name} ({type(e).__name__}: {e})")
            _cleanup_object(obj_or_cm)
    
    return runner


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_benchmarks():
    """Run all cucumber benchmarks."""
    print("\n" + "="*80)
    print(" CUCUMBER MODULE BENCHMARKS ".center(80, "="))
    print("="*80)
    
    runners = [
        benchmark_primitives(),
        benchmark_deserialization(),
        benchmark_complex(),
        benchmark_large_data(),
        benchmark_roundtrip(),
        benchmark_worst_possible_object(),
        benchmark_reconnector_showcase(),
        benchmark_supported_types_throughput(),
        benchmark_supported_types_compatibility(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()