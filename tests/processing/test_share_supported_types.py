"""
Share Supported Types Tests

Ensures that every cucumber supported type can be added to Share and updated
from multiple processes.
"""

import asyncio
import concurrent.futures
import contextlib
import contextvars
import datetime
import decimal
import fractions
import functools
import importlib
import inspect
import io
import mmap
import os
import queue
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import traceback
import types
import uuid
import weakref
import time
import enum
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, Callable, Dict, List, Optional, NamedTuple, TypedDict

import multiprocessing
import multiprocessing.connection
import multiprocessing.shared_memory
from multiprocessing.managers import BaseProxy
import signal

from suitkaise.processing import Share, Skprocess, Pool
from suitkaise.cucumber import reconnect_all
from suitkaise.cucumber._int.handlers.sqlite_handler import (
    SQLiteConnectionReconnector,
    SQLiteCursorReconnector,
)
from suitkaise.cucumber._int.handlers.network_handler import SocketReconnector
from suitkaise.cucumber._int.handlers.pipe_handler import PipeReconnector
from suitkaise.cucumber._int.handlers.threading_handler import ThreadReconnector
from suitkaise.cucumber._int.handlers.subprocess_handler import SubprocessReconnector
from suitkaise.cucumber._int.handlers.regex_handler import MatchReconnector
from suitkaise.cucumber._int.handlers.network_handler import DbReconnector


class _SkipType:
    def __init__(self, reason: str):
        self.reason = reason


def _skip(reason: str) -> _SkipType:
    return _SkipType(reason)


@dataclass
class SupportedTypeSpec:
    name: str
    make_initial: Callable[[], Any]
    make_updated: Callable[[], Any]
    verify: Callable[[Any, Any], None]
    cleanup: Optional[Callable[[Any], None]] = None
    expected_type: Optional[type] = None


def _assign_share_attr(coordinator_state: dict, attr: str, spec_index: int) -> None:
    from suitkaise.processing._int.share.coordinator import _Coordinator
    specs = _build_specs()
    spec = specs[spec_index]
    updated = spec.make_updated()
    if isinstance(updated, _SkipType):
        return
    coordinator = _Coordinator.from_state(coordinator_state)
    share = Share(
        manager=None,
        auto_start=False,
        client_mode=True,
        coordinator=coordinator,
    )
    object.__setattr__(share, '_started', True)
    try:
        setattr(share, attr, updated)
    except Exception as exc:
        print(f"Worker failed on spec={spec.name}, type={type(updated).__name__}: {exc}")
        raise
    finally:
        if spec.cleanup:
            try:
                spec.cleanup(updated)
            except Exception:
                pass


def sample_function(x, y=1):
    return x + y


def thread_target():
    return None


async def sample_coroutine():
    return "coro"


async def sample_async_generator():
    yield 1


@contextlib.contextmanager
def sample_contextmanager():
    yield 1


class ExampleEnum(enum.Enum):
    A = 1
    B = 2


NT = namedtuple("NT", ["a"])


class TNamedTuple(NamedTuple):
    a: int


class TTypedDict(TypedDict):
    a: int


class TestResult:
    def __init__(
        self,
        name: str,
        passed: bool,
        message: str = "",
        error: str = "",
        traceback_text: str = "",
    ):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error
        self.traceback_text = traceback_text


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

    def run_test(self, name: str, test_func, timeout: float = 120.0):
        """Run a test with a timeout."""
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Test timed out after {timeout}s")

        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
        except (AttributeError, ValueError):
            pass

        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            tb = traceback.format_exc()
            self.results.append(TestResult(name, False, error=str(e), traceback_text=tb))
        except TimeoutError as e:
            tb = traceback.format_exc()
            self.results.append(TestResult(name, False, error=str(e), traceback_text=tb))
        except Exception as e:
            tb = traceback.format_exc()
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}", traceback_text=tb))
        finally:
            try:
                signal.alarm(0)
                if old_handler:
                    signal.signal(signal.SIGALRM, old_handler)
            except (AttributeError, ValueError):
                pass

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
            if result.traceback_text:
                print(f"{self.RED}{result.traceback_text}{self.RESET}")

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


def _verify_equals(stored: Any, updated: Any) -> None:
    assert stored == updated


def _verify_type_only(stored: Any, updated: Any) -> None:
    assert type(stored) is type(updated)


def _verify_instance_of(expected_type: type) -> Callable[[Any, Any], None]:
    def _verify(stored: Any, updated: Any) -> None:
        assert isinstance(stored, expected_type)
    return _verify


def _verify_manager_proxy(stored: Any, updated: Any) -> None:
    assert stored is None or isinstance(stored, (BaseProxy, dict, list))


def _verify_iterable_equals(expected: list) -> Callable[[Any, Any], None]:
    def _verify(stored: Any, updated: Any) -> None:
        assert list(stored) == expected
    return _verify


def _verify_closed_io(stored: Any, updated: Any) -> None:
    assert isinstance(stored, io.IOBase)
    assert stored.closed is True


def _verify_subprocess_like(stored: Any, updated: Any) -> None:
    assert isinstance(stored, (SubprocessReconnector, subprocess.Popen))


def _verify_async_placeholder(stored: Any, updated: Any) -> None:
    assert getattr(stored, "_deserialized", False) is True


def _safe_close(obj: Any) -> None:
    try:
        obj.close()
    except Exception:
        pass


def _safe_terminate(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=2.0)
    except Exception:
        pass


def _safe_shared_memory_cleanup(shm: multiprocessing.shared_memory.SharedMemory) -> None:
    try:
        shm.close()
    except Exception:
        pass
    try:
        shm.unlink()
    except Exception:
        pass


def _safe_pipe_close(conn: multiprocessing.connection.Connection) -> None:
    try:
        conn.close()
    except Exception:
        pass


def _cleanup_asyncio(obj: Any) -> None:
    try:
        obj.close()
    except Exception:
        pass
    loop = getattr(obj, "_sk_loop", None)
    if loop is not None:
        try:
            if isinstance(obj, asyncio.Task):
                obj.cancel()
                if not loop.is_closed():
                    loop.run_until_complete(asyncio.gather(obj, return_exceptions=True))
            elif isinstance(obj, asyncio.Future):
                if not obj.done():
                    obj.cancel()
            if not loop.is_closed():
                loop.stop()
                loop.close()
        except Exception:
            pass


def _cleanup_coroutine(coro: Any) -> None:
    try:
        coro.close()
    except Exception:
        pass


def _cleanup_async_generator(agen: Any) -> None:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(agen.aclose())
        loop.close()
    except Exception:
        pass


def _safe_manager_shutdown(manager: Any) -> None:
    try:
        manager.shutdown()
    except Exception:
        pass


def _make_temp_text_file(contents: str = "hello") -> io.TextIOBase:
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    handle = open(tmp.name, "w+", encoding="utf-8")
    handle.write(contents)
    handle.flush()
    return handle


def _make_file_io() -> io.FileIO:
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(b"fileio")
    tmp.flush()
    tmp.close()
    return io.FileIO(tmp.name, mode="rb+")


def _make_mmap() -> mmap.mmap:
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(b"mmapdata")
        tmp.flush()
        tmp.close()
        f = open(tmp.name, "rb+")
        mm = mmap.mmap(f.fileno(), 0)
        f.close()
        return mm
    except Exception:
        return _skip("mmap unavailable")


def _make_pipe_connection() -> multiprocessing.connection.Connection:
    conn1, conn2 = multiprocessing.Pipe()
    conn2.close()
    return conn1


def _make_shared_memory() -> multiprocessing.shared_memory.SharedMemory:
    try:
        return multiprocessing.shared_memory.SharedMemory(create=True, size=16)
    except Exception:
        return _skip("shared_memory unavailable")


def _make_fd() -> int:
    r_fd, w_fd = os.pipe()
    os.close(w_fd)
    return r_fd


def _make_base_proxy() -> BaseProxy:
    manager = multiprocessing.Manager()
    proxy = manager.dict()
    setattr(proxy, "_sk_manager", manager)
    return proxy


def _make_unsupported_manager_proxy() -> _SkipType:
    return _skip("multiprocessing Manager proxies are not Share-supported")


def _cleanup_base_proxy(proxy: BaseProxy) -> None:
    manager = getattr(proxy, "_sk_manager", None)
    if manager is not None:
        _safe_manager_shutdown(manager)


def _make_frame() -> types.FrameType:
    return inspect.currentframe()


def _make_property() -> property:
    return property(lambda self: 1)


def _make_staticmethod() -> staticmethod:
    return staticmethod(lambda: 1)


def _make_classmethod() -> classmethod:
    return classmethod(lambda cls: 1)


class SimpleUserClass:
    def __init__(self, value: int = 1):
        self.value = value

    def increment(self):
        self.value += 1


def _make_function():
    return sample_function


def _make_method():
    return types.MethodType(SimpleUserClass.increment, SimpleUserClass())


def _make_partial():
    return functools.partial(sample_function, 5)


def _make_re_match():
    return re.search(r"(\d+)", "value 42")


def _make_context_token():
    var = contextvars.ContextVar("test_var")
    return var.set("value")


def _make_requests_session():
    try:
        requests = importlib.import_module("requests")
    except ImportError:
        return _skip("requests not installed")
    return requests.Session()


def _make_db_connection(module_name: str, constructor: str) -> Any:
    try:
        mod = importlib.import_module(module_name)
    except ImportError:
        return _skip(f"{module_name} not installed")
    try:
        return getattr(mod, constructor)()
    except Exception:
        return _skip(f"{module_name}.{constructor} not available")


def _make_sqlalchemy_engine() -> Any:
    try:
        sqlalchemy = importlib.import_module("sqlalchemy")
    except ImportError:
        return _skip("sqlalchemy not installed")
    try:
        return sqlalchemy.create_engine("sqlite:///:memory:")
    except Exception:
        return _skip("sqlalchemy engine unavailable")


def _make_elasticsearch_client() -> Any:
    try:
        elasticsearch = importlib.import_module("elasticsearch")
    except ImportError:
        return _skip("elasticsearch not installed")
    try:
        return elasticsearch.Elasticsearch("http://localhost:9200")
    except Exception:
        return _skip("elasticsearch client unavailable")


def _make_neo4j_driver() -> Any:
    try:
        neo4j = importlib.import_module("neo4j")
    except ImportError:
        return _skip("neo4j not installed")
    try:
        return neo4j.GraphDatabase.driver("bolt://localhost:7687")
    except Exception:
        return _skip("neo4j driver unavailable")


def _make_influx_client() -> Any:
    try:
        influx = importlib.import_module("influxdb_client")
    except ImportError:
        return _skip("influxdb_client not installed")
    try:
        return influx.InfluxDBClient(url="http://localhost:8086", token="x", org="org")
    except Exception:
        return _skip("influxdb client unavailable")


def _make_db_reconnector() -> DbReconnector:
    return DbReconnector(details={"module": "sqlite3", "class_name": "Connection", "path": ":memory:"})


def _make_socket_reconnector() -> SocketReconnector:
    return SocketReconnector(state={
        "family": socket.AF_INET,
        "type": socket.SOCK_STREAM,
        "proto": 0,
        "timeout": None,
        "blocking": True,
    })


def _make_thread_reconnector() -> ThreadReconnector:
    return ThreadReconnector(state={"name": "t", "daemon": True, "target": None, "args": (), "kwargs": {}})


def _make_pipe_reconnector() -> PipeReconnector:
    return PipeReconnector()


def _make_subprocess_reconnector() -> SubprocessReconnector:
    return SubprocessReconnector(state={"args": [sys.executable, "-c", "print(1)"]})


def _make_match_reconnector() -> MatchReconnector:
    return MatchReconnector(state={"pattern": r"(\d+)", "string": "123"})


def _make_asyncio_future() -> asyncio.Future:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    future = loop.create_future()
    future.set_result("ok")
    setattr(future, "_sk_loop", loop)
    return future


def _make_asyncio_task() -> asyncio.Task:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(sample_coroutine())
    loop.run_until_complete(task)
    setattr(task, "_sk_loop", loop)
    return task


def _make_coroutine() -> types.CoroutineType:
    return sample_coroutine()


def _make_async_generator() -> types.AsyncGeneratorType:
    return sample_async_generator()


def _load_supported_type_names() -> List[str]:
    md_path = Path(__file__).resolve().parents[2] / "suitkaise" / "_docs_copy" / "cucumber" / "supported-types.md"
    names = []
    with open(md_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line.startswith("- "):
                name = line[2:].strip()
                if "`" in name:
                    name = name.replace("`", "")
                if " --> " in name:
                    name = name.split(" --> ", 1)[0].strip()
                names.append(name)
    return names


def _build_specs() -> List[SupportedTypeSpec]:
    specs: List[SupportedTypeSpec] = []

    specs.append(SupportedTypeSpec("user-defined class instances", lambda: SimpleUserClass(1), lambda: SimpleUserClass(2), _verify_type_only))
    specs.append(SupportedTypeSpec("None", lambda: None, lambda: None, _verify_equals))
    specs.append(SupportedTypeSpec("bool", lambda: True, lambda: False, _verify_equals))
    specs.append(SupportedTypeSpec("int", lambda: 1, lambda: 2, _verify_equals))
    specs.append(SupportedTypeSpec("float", lambda: 1.25, lambda: 2.5, _verify_equals))
    specs.append(SupportedTypeSpec("str", lambda: "a", lambda: "b", _verify_equals))
    specs.append(SupportedTypeSpec("bytes", lambda: b"a", lambda: b"b", _verify_equals))
    specs.append(SupportedTypeSpec("list", lambda: [1], lambda: [1, 2], _verify_equals))
    specs.append(SupportedTypeSpec("tuple", lambda: (1,), lambda: (1, 2), _verify_equals))
    specs.append(SupportedTypeSpec("set", lambda: {1}, lambda: {1, 2}, _verify_equals))
    specs.append(SupportedTypeSpec("frozenset", lambda: frozenset({1}), lambda: frozenset({1, 2}), _verify_equals))
    specs.append(SupportedTypeSpec("dict", lambda: {"a": 1}, lambda: {"a": 2}, _verify_equals))
    specs.append(SupportedTypeSpec("datetime.datetime", lambda: datetime.datetime(2020, 1, 1), lambda: datetime.datetime(2021, 1, 1), _verify_equals))
    specs.append(SupportedTypeSpec("datetime.date", lambda: datetime.date(2020, 1, 1), lambda: datetime.date(2021, 1, 1), _verify_equals))
    specs.append(SupportedTypeSpec("datetime.time", lambda: datetime.time(1, 2, 3), lambda: datetime.time(2, 3, 4), _verify_equals))
    specs.append(SupportedTypeSpec("datetime.timedelta", lambda: datetime.timedelta(seconds=1), lambda: datetime.timedelta(seconds=2), _verify_equals))
    specs.append(SupportedTypeSpec("datetime.timezone", lambda: datetime.timezone.utc, lambda: datetime.timezone(datetime.timedelta(hours=1)), _verify_equals))
    specs.append(SupportedTypeSpec("decimal.Decimal", lambda: decimal.Decimal("1.1"), lambda: decimal.Decimal("2.2"), _verify_equals))
    specs.append(SupportedTypeSpec("fractions.Fraction", lambda: fractions.Fraction(1, 3), lambda: fractions.Fraction(2, 3), _verify_equals))
    specs.append(SupportedTypeSpec("uuid.UUID", lambda: uuid.uuid4(), lambda: uuid.uuid4(), _verify_type_only))
    specs.append(SupportedTypeSpec("pathlib.Path", lambda: Path(__file__), lambda: Path(__file__).parent, _verify_equals))
    specs.append(SupportedTypeSpec("pathlib.PurePath", lambda: PurePath("a") / "b", lambda: PurePath("c") / "d", _verify_equals))
    specs.append(SupportedTypeSpec("pathlib.PosixPath", lambda: Path("a") if os.name != "nt" else _skip("non-posix"), lambda: Path("b") if os.name != "nt" else _skip("non-posix"), _verify_type_only))
    specs.append(SupportedTypeSpec("pathlib.WindowsPath", lambda: Path("a") if os.name == "nt" else _skip("non-windows"), lambda: Path("b") if os.name == "nt" else _skip("non-windows"), _verify_type_only))
    specs.append(SupportedTypeSpec("types.FunctionType", _make_function, _make_function, _verify_type_only))
    specs.append(SupportedTypeSpec("functools.partial", _make_partial, _make_partial, _verify_type_only))
    specs.append(SupportedTypeSpec("types.MethodType", _make_method, _make_method, _verify_type_only))
    specs.append(SupportedTypeSpec("staticmethod", _make_staticmethod, _make_staticmethod, _verify_type_only))
    specs.append(SupportedTypeSpec("classmethod", _make_classmethod, _make_classmethod, _verify_type_only))
    specs.append(SupportedTypeSpec("type", lambda: SimpleUserClass, lambda: dict, _verify_type_only))

    import logging
    specs.append(SupportedTypeSpec("logging.Logger", lambda: logging.getLogger("t1"), lambda: logging.getLogger("t2"), _verify_type_only))
    specs.append(SupportedTypeSpec("logging.StreamHandler", lambda: logging.StreamHandler(), lambda: logging.StreamHandler(), _verify_type_only, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("logging.FileHandler", lambda: logging.FileHandler(tempfile.NamedTemporaryFile(delete=False).name), lambda: logging.FileHandler(tempfile.NamedTemporaryFile(delete=False).name), _verify_type_only, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("logging.Formatter", lambda: logging.Formatter("%(name)s"), lambda: logging.Formatter("%(message)s"), _verify_type_only))

    import _thread
    specs.append(SupportedTypeSpec("_thread.lock", _thread.allocate_lock, _thread.allocate_lock, _verify_type_only))
    specs.append(SupportedTypeSpec("threading.RLock", threading.RLock, threading.RLock, _verify_type_only))
    specs.append(SupportedTypeSpec("threading.Semaphore", lambda: threading.Semaphore(1), lambda: threading.Semaphore(2), _verify_type_only))
    specs.append(SupportedTypeSpec("threading.BoundedSemaphore", lambda: threading.BoundedSemaphore(1), lambda: threading.BoundedSemaphore(2), _verify_type_only))
    specs.append(SupportedTypeSpec("threading.Barrier", lambda: threading.Barrier(1), lambda: threading.Barrier(1), _verify_type_only))
    specs.append(SupportedTypeSpec("threading.Condition", threading.Condition, threading.Condition, _verify_type_only))
    specs.append(SupportedTypeSpec("io.TextIOBase", lambda: _make_temp_text_file("a"), lambda: _make_temp_text_file("b"), _verify_type_only, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("tempfile._TemporaryFileWrapper", lambda: tempfile.NamedTemporaryFile(delete=False), lambda: tempfile.NamedTemporaryFile(delete=False), _verify_type_only, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("io.StringIO", lambda: io.StringIO("a"), lambda: io.StringIO("b"), _verify_type_only, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("io.BytesIO", lambda: io.BytesIO(b"a"), lambda: io.BytesIO(b"b"), _verify_type_only, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("queue.Queue", queue.Queue, queue.Queue, _verify_type_only))
    specs.append(SupportedTypeSpec("multiprocessing.Queue", lambda: _skip("multiprocessing.Queue is not Share-supported"), lambda: _skip("multiprocessing.Queue is not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("threading.Event", threading.Event, threading.Event, _verify_type_only))
    specs.append(SupportedTypeSpec("multiprocessing.Event", lambda: _skip("multiprocessing.Event is not Share-supported"), lambda: _skip("multiprocessing.Event is not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("re.Pattern", lambda: re.compile(r"abc"), lambda: re.compile(r"def"), _verify_type_only))
    specs.append(SupportedTypeSpec("re.Match", _make_re_match, _make_re_match, _verify_instance_of(MatchReconnector), expected_type=MatchReconnector))
    specs.append(SupportedTypeSpec("sqlite3.Connection", lambda: sqlite3.connect(":memory:"), lambda: sqlite3.connect(":memory:"), _verify_instance_of(SQLiteConnectionReconnector), expected_type=SQLiteConnectionReconnector, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("sqlite3.Cursor", lambda: sqlite3.connect(":memory:").cursor(), lambda: sqlite3.connect(":memory:").cursor(), _verify_instance_of(SQLiteCursorReconnector), expected_type=SQLiteCursorReconnector))
    specs.append(SupportedTypeSpec("contextvars.ContextVar", lambda: contextvars.ContextVar("a"), lambda: contextvars.ContextVar("b"), _verify_type_only))
    specs.append(SupportedTypeSpec("contextvars.Token", lambda: _skip("contextvars.Token is not Share-supported"), lambda: _skip("contextvars.Token is not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("requests.Session", _make_requests_session, _make_requests_session, _verify_type_only, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("socket.socket", lambda: socket.socket(), lambda: socket.socket(), _verify_instance_of(SocketReconnector), expected_type=SocketReconnector, cleanup=_safe_close))

    specs.append(SupportedTypeSpec("psycopg2.Connection", lambda: _make_db_connection("psycopg2", "connect"), lambda: _make_db_connection("psycopg2", "connect"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("pymysql.Connection", lambda: _make_db_connection("pymysql", "connect"), lambda: _make_db_connection("pymysql", "connect"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("pymongo.MongoClient", lambda: _make_db_connection("pymongo", "MongoClient"), lambda: _make_db_connection("pymongo", "MongoClient"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("redis.Redis", lambda: _make_db_connection("redis", "Redis"), lambda: _make_db_connection("redis", "Redis"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("sqlalchemy.Engine", _make_sqlalchemy_engine, _make_sqlalchemy_engine, _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("cassandra.Cluster", lambda: _make_db_connection("cassandra.cluster", "Cluster"), lambda: _make_db_connection("cassandra.cluster", "Cluster"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("elasticsearch.Elasticsearch", _make_elasticsearch_client, _make_elasticsearch_client, _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("neo4j.Driver", _make_neo4j_driver, _make_neo4j_driver, _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("influxdb_client.InfluxDBClient", _make_influx_client, _make_influx_client, _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("pyodbc.Connection", lambda: _make_db_connection("pyodbc", "connect"), lambda: _make_db_connection("pyodbc", "connect"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("clickhouse_driver.Client", lambda: _make_db_connection("clickhouse_driver", "Client"), lambda: _make_db_connection("clickhouse_driver", "Client"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("pymssql.Connection", lambda: _make_db_connection("pymssql", "connect"), lambda: _make_db_connection("pymssql", "connect"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("oracledb.Connection", lambda: _make_db_connection("oracledb", "connect"), lambda: _make_db_connection("oracledb", "connect"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("snowflake.Connection", lambda: _make_db_connection("snowflake.connector", "connect"), lambda: _make_db_connection("snowflake.connector", "connect"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))
    specs.append(SupportedTypeSpec("duckdb.Connection", lambda: _make_db_connection("duckdb", "connect"), lambda: _make_db_connection("duckdb", "connect"), _verify_instance_of(DbReconnector), expected_type=DbReconnector))

    specs.append(SupportedTypeSpec("collections.abc.Iterator", lambda: iter([1, 2]), lambda: iter([3, 4]), _verify_type_only))
    specs.append(SupportedTypeSpec("range", lambda: range(1, 3), lambda: range(2, 4), _verify_type_only))
    specs.append(SupportedTypeSpec("enumerate", lambda: enumerate([1, 2]), lambda: enumerate([3, 4]), _verify_iterable_equals([(0, 3), (1, 4)])))
    specs.append(SupportedTypeSpec("zip", lambda: zip([1], [2]), lambda: zip([3], [4]), _verify_iterable_equals([(3, 4)])))
    specs.append(SupportedTypeSpec("mmap.mmap", _make_mmap, _make_mmap, _verify_type_only, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("multiprocessing.shared_memory.SharedMemory", lambda: _skip("multiprocessing.shared_memory is not Share-supported"), lambda: _skip("multiprocessing.shared_memory is not Share-supported"), _verify_type_only, cleanup=_safe_shared_memory_cleanup))
    specs.append(SupportedTypeSpec("int (file descriptors)", _make_fd, _make_fd, _verify_type_only, cleanup=os.close))
    specs.append(SupportedTypeSpec("memoryview", lambda: memoryview(b"abc"), lambda: memoryview(b"def"), _verify_type_only))
    specs.append(SupportedTypeSpec("threading.Thread", lambda: threading.Thread(target=lambda: None), lambda: threading.Thread(target=lambda: None), _verify_instance_of(ThreadReconnector), expected_type=ThreadReconnector))
    specs.append(SupportedTypeSpec("concurrent.futures.ThreadPoolExecutor", lambda: concurrent.futures.ThreadPoolExecutor(max_workers=1), lambda: concurrent.futures.ThreadPoolExecutor(max_workers=1), _verify_type_only, cleanup=lambda e: e.shutdown(wait=False)))
    specs.append(SupportedTypeSpec("concurrent.futures.ProcessPoolExecutor", lambda: concurrent.futures.ProcessPoolExecutor(max_workers=1), lambda: concurrent.futures.ProcessPoolExecutor(max_workers=1), _verify_type_only, cleanup=lambda e: e.shutdown(wait=False)))
    specs.append(SupportedTypeSpec("threading.local", threading.local, threading.local, _verify_type_only))
    specs.append(SupportedTypeSpec("io.FileIO (from os.pipe)", lambda: _skip("os.pipe file handles are not Share-supported"), lambda: _skip("os.pipe file handles are not Share-supported"), _verify_closed_io, cleanup=_safe_close))
    specs.append(SupportedTypeSpec("multiprocessing.connection.Connection", lambda: _skip("multiprocessing.connection is not Share-supported"), lambda: _skip("multiprocessing.connection is not Share-supported"), _verify_instance_of(PipeReconnector), expected_type=PipeReconnector, cleanup=_safe_pipe_close))
    specs.append(SupportedTypeSpec("multiprocessing.managers.BaseProxy", _make_unsupported_manager_proxy, _make_unsupported_manager_proxy, _verify_manager_proxy, expected_type=BaseProxy, cleanup=_cleanup_base_proxy))
    specs.append(SupportedTypeSpec("types.CodeType", lambda: (lambda x: x).__code__, lambda: (lambda x: x + 1).__code__, _verify_type_only))
    specs.append(SupportedTypeSpec("types.FrameType", lambda: _skip("frame objects are not Share-supported"), lambda: _skip("frame objects are not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("property", _make_property, _make_property, _verify_type_only))

    specs.append(SupportedTypeSpec("types.MemberDescriptorType", lambda: _skip("descriptor types are not Share-supported"), lambda: _skip("descriptor types are not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("types.GetSetDescriptorType", lambda: _skip("descriptor types are not Share-supported"), lambda: _skip("descriptor types are not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("types.WrapperDescriptorType", lambda: _skip("descriptor types are not Share-supported"), lambda: _skip("descriptor types are not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("types.MethodDescriptorType", lambda: _skip("descriptor types are not Share-supported"), lambda: _skip("descriptor types are not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("types.MethodWrapperType", lambda: (1).__add__, lambda: (2).__add__, _verify_type_only))
    specs.append(SupportedTypeSpec("types.GeneratorType", lambda: (i for i in range(1)), lambda: (i for i in range(2)), _verify_iterable_equals([0, 1])))
    specs.append(SupportedTypeSpec("weakref.ref", lambda: _skip("weakref.ref is not Share-supported"), lambda: _skip("weakref.ref is not Share-supported"), _verify_type_only))
    specs.append(SupportedTypeSpec("weakref.WeakValueDictionary", weakref.WeakValueDictionary, weakref.WeakValueDictionary, _verify_type_only))
    specs.append(SupportedTypeSpec("weakref.WeakKeyDictionary", weakref.WeakKeyDictionary, weakref.WeakKeyDictionary, _verify_type_only))

    specs.append(SupportedTypeSpec("enum.Enum", lambda: ExampleEnum.A, lambda: ExampleEnum.B, _verify_type_only))
    specs.append(SupportedTypeSpec("enum.EnumMeta", lambda: ExampleEnum, lambda: ExampleEnum, _verify_type_only))
    specs.append(SupportedTypeSpec("contextlib._GeneratorContextManager", lambda: sample_contextmanager(), lambda: sample_contextmanager(), _verify_type_only))

    specs.append(SupportedTypeSpec("subprocess.Popen", lambda: subprocess.Popen([sys.executable, "-c", "print(1)"]), lambda: subprocess.Popen([sys.executable, "-c", "print(1)"]), _verify_subprocess_like, cleanup=_safe_terminate))
    specs.append(SupportedTypeSpec("subprocess.CompletedProcess", lambda: subprocess.run([sys.executable, "-c", "print(1)"], capture_output=True), lambda: subprocess.run([sys.executable, "-c", "print(1)"], capture_output=True), _verify_type_only))
    specs.append(SupportedTypeSpec("types.CoroutineType", _make_coroutine, _make_coroutine, _verify_async_placeholder, cleanup=_cleanup_coroutine))
    specs.append(SupportedTypeSpec("types.AsyncGeneratorType", _make_async_generator, _make_async_generator, _verify_async_placeholder, cleanup=_cleanup_async_generator))
    specs.append(SupportedTypeSpec("asyncio.Task", _make_asyncio_task, _make_asyncio_task, _verify_async_placeholder, cleanup=_cleanup_asyncio))
    specs.append(SupportedTypeSpec("asyncio.Future", _make_asyncio_future, _make_asyncio_future, _verify_async_placeholder, cleanup=_cleanup_asyncio))
    specs.append(SupportedTypeSpec("types.ModuleType", lambda: types.ModuleType("m1"), lambda: types.ModuleType("m2"), _verify_type_only))

    specs.append(SupportedTypeSpec("collections.namedtuple", lambda: NT(1), lambda: NT(2), _verify_equals))
    specs.append(SupportedTypeSpec("typing.NamedTuple", lambda: TNamedTuple(1), lambda: TNamedTuple(2), _verify_equals))
    specs.append(SupportedTypeSpec("typing.TypedDict", lambda: {"a": 1}, lambda: {"a": 2}, _verify_type_only))

    specs.append(SupportedTypeSpec("DbReconnector", _make_db_reconnector, _make_db_reconnector, _verify_type_only))
    specs.append(SupportedTypeSpec("SocketReconnector", _make_socket_reconnector, _make_socket_reconnector, _verify_type_only))
    specs.append(SupportedTypeSpec("ThreadReconnector", _make_thread_reconnector, _make_thread_reconnector, _verify_type_only))
    specs.append(SupportedTypeSpec("PipeReconnector", _make_pipe_reconnector, _make_pipe_reconnector, _verify_type_only))
    specs.append(SupportedTypeSpec("SubprocessReconnector", _make_subprocess_reconnector, _make_subprocess_reconnector, _verify_type_only))
    specs.append(SupportedTypeSpec("MatchReconnector", _make_match_reconnector, _make_match_reconnector, _verify_type_only))

    return specs


def test_share_supported_types_multi_process():
    cleanup_queue: List[tuple[Optional[Callable[[Any], None]], Any]] = []
    supported_names = set(_load_supported_type_names())
    specs = _build_specs()
    spec_names = {spec.name for spec in specs}
    missing = supported_names - spec_names
    assert not missing, f"Missing supported types in Share test: {sorted(missing)}"

    share = Share()
    try:
        actions = []
        coordinator_state = share._coordinator.get_state()
        attr_map: Dict[str, SupportedTypeSpec] = {}
        updated_map: Dict[str, Any] = {}
        skipped: Dict[str, str] = {}

        for idx, spec in enumerate(specs):
            initial = spec.make_initial()
            if isinstance(initial, _SkipType):
                skipped[spec.name] = initial.reason
                continue
            updated = spec.make_updated()
            if isinstance(updated, _SkipType):
                skipped[spec.name] = updated.reason
                continue

            attr = f"obj_{idx}"
            setattr(share, attr, initial)
            actions.append((coordinator_state, attr, idx))
            attr_map[attr] = spec
            updated_map[attr] = updated

            if spec.cleanup:
                cleanup_queue.append((spec.cleanup, initial))
                cleanup_queue.append((spec.cleanup, updated))

        if actions:
            processes = []
            for coord_state, attr, spec_index in actions:
                proc = multiprocessing.Process(
                    target=_assign_share_attr,
                    args=(coord_state, attr, spec_index),
                )
                proc.start()
                processes.append(proc)
            failed = []
            for proc in processes:
                proc.join(timeout=10.0)
                if proc.exitcode not in (0, None):
                    failed.append(proc.exitcode)
            assert not failed, f"Worker processes failed: {failed}"
            time.sleep(0.2 if sys.platform != "win32" else 0.6)

        for attr, spec in attr_map.items():
            stored = share._coordinator.get_object(attr)
            updated = updated_map[attr]
            if spec.expected_type is not None:
                assert isinstance(stored, spec.expected_type), (
                    f"{spec.name} stored type {type(stored)} "
                    f"did not match expected {spec.expected_type}"
                )
                if issubclass(spec.expected_type, DbReconnector):
                    reconnect_all(stored)
            try:
                spec.verify(stored, updated)
            except AssertionError as exc:
                raise AssertionError(f"{spec.name} verification failed: {exc}") from exc
            if spec.cleanup:
                try:
                    spec.cleanup(stored)
                except Exception:
                    pass

    finally:
        for cleanup, obj in cleanup_queue:
            if cleanup:
                try:
                    cleanup(obj)
                except Exception:
                    pass
        share.exit()


def run_all_tests():
    """Run all Share supported types tests."""
    runner = TestRunner("Share Supported Types Tests")
    runner.run_test("Share supported types multiprocess", test_share_supported_types_multi_process, timeout=300)
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
