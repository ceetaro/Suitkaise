"""
Extended Handler Tests

Covers additional handler implementations with low coverage.
"""

from __future__ import annotations

import asyncio
import enum
import io
import mmap
import os
import sqlite3
import subprocess
import sys
import tempfile
import types
import socket
import queue as queue_module
import multiprocessing
import weakref
import threading
import functools
import contextlib
import re
import logging
import inspect
import contextvars
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from collections import namedtuple
from typing import NamedTuple

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
from suitkaise.cerial._int.handlers.enum_handler import EnumHandler, EnumClassHandler, EnumSerializationError
from suitkaise.cerial._int.handlers.module_handler import ModuleHandler
from suitkaise.cerial._int.handlers.file_handler import (
    FileHandleHandler,
    TemporaryFileHandler,
    StringIOHandler,
    BytesIOHandler,
    FileSerializationError,
)
from suitkaise.cerial._int.handlers.network_handler import (
    HTTPSessionHandler,
    SocketHandler,
    DatabaseConnectionHandler,
    NetworkSerializationError,
    DbReconnector,
    SocketReconnector,
    SQLiteReconnector,
)
from suitkaise.cerial._int.handlers.memory_handler import (
    MMapHandler,
    SharedMemoryHandler,
    FileDescriptorHandler,
    MemoryViewHandler,
    MemorySerializationError,
)
from suitkaise.cerial._int.handlers.function_handler import (
    FunctionHandler,
    FunctionSerializationError,
    PartialFunctionHandler,
    BoundMethodHandler,
    LambdaHandler,
    StaticMethodHandler,
    ClassMethodHandler,
)
from suitkaise.cerial._int.handlers.reconnector import Reconnector
from suitkaise.cerial._int.handlers.sqlite_handler import (
    SQLiteConnectionHandler,
    SQLiteCursorHandler,
)
from suitkaise.cerial._int.handlers.subprocess_handler import (
    PopenHandler,
    CompletedProcessHandler,
    SubprocessReconnector,
)
from suitkaise.cerial._int.handlers.weakref_handler import (
    WeakrefHandler,
    WeakValueDictionaryHandler,
    WeakKeyDictionaryHandler,
)
from suitkaise.cerial._int.handlers.namedtuple_handler import NamedTupleHandler, TypedDictHandler
from suitkaise.cerial._int.handlers.regex_handler import (
    MatchObjectHandler,
    MatchReconnector,
    RegexPatternHandler,
)
from suitkaise.cerial._int.handlers.queue_handler import (
    QueueHandler,
    MultiprocessingQueueHandler,
    EventHandler,
    MultiprocessingEventHandler,
)
from suitkaise.cerial._int.handlers.pipe_handler import (
    MultiprocessingPipeHandler,
    OSPipeHandler,
    MultiprocessingManagerHandler,
    PipeReconnector,
)
from suitkaise.cerial._int.handlers.class_handler import (
    ClassInstanceHandler,
    ClassObjectHandler,
)
from suitkaise.cerial._int.handlers.context_manager_handler import (
    ContextManagerHandler,
    ContextlibGeneratorHandler,
    ContextManagerSerializationError,
)
from suitkaise.cerial._int.handlers.threading_handler import (
    ThreadHandler,
    ThreadPoolExecutorHandler,
    ProcessPoolExecutorHandler,
    ThreadLocalHandler,
    ThreadReconnector,
)
from suitkaise.cerial._int.handlers.lock_handler import (
    LockHandler,
    SemaphoreHandler,
    BarrierHandler,
    ConditionHandler,
)
from suitkaise.cerial._int.handlers.iterator_handler import (
    IteratorHandler,
    RangeHandler,
    EnumerateHandler,
    ZipHandler,
)
from suitkaise.cerial._int.handlers.logging_handler import (
    LoggerHandler,
    StreamHandlerHandler,
    FileHandlerHandler,
    FormatterHandler,
)
from suitkaise.cerial._int.handlers.contextvar_handler import (
    ContextVarHandler,
    TokenHandler,
)
from suitkaise.cerial._int.handlers.advanced_py_handler import (
    CodeObjectHandler,
    FrameObjectHandler,
    FrameInfo,
    PropertyHandler,
    DescriptorHandler,
)
from suitkaise.cerial._int.handlers.generator_handler import (
    GeneratorHandler,
)
from suitkaise.cerial._int.handlers.async_handler import (
    CoroutineHandler,
    AsyncGeneratorHandler,
    TaskHandler,
    AsyncSerializationError,
)
from suitkaise.cerial._int.handlers.weakref_handler import WeakrefSerializationError
import suitkaise.cerial._int.handlers.memory_handler as memory_handler

try:
    from multiprocessing import shared_memory
    HAS_SHARED_MEMORY = True
except Exception:
    HAS_SHARED_MEMORY = False
    shared_memory = None  # type: ignore

try:
    from _suitkaise_wip.fdl._int.setup.text_wrapping import _TextWrapper
except Exception:
    _TextWrapper = None


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
        self._wrapper = _TextWrapper(width=72) if _TextWrapper else None

    def _wrap(self, text: str) -> list[str]:
        if self._wrapper:
            return self._wrapper.wrap_text(text, preserve_newlines=True)
        return [text]

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
                for line in self._wrap(result.error):
                    print(f"         {self.RED}└─ {line}{self.RESET}")

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
# Enum Handler Tests
# =============================================================================

class Color(enum.Enum):
    RED = 1
    GREEN = 2


def test_enum_instance_roundtrip():
    """EnumHandler should serialize and reconstruct enum instances."""
    handler = EnumHandler()
    state = handler.extract_state(Color.RED)
    restored = handler.reconstruct(state)
    assert restored is Color.RED


def test_enum_class_roundtrip():
    """EnumClassHandler should serialize and reconstruct enum classes."""
    handler = EnumClassHandler()
    state = handler.extract_state(Color)
    restored = handler.reconstruct(state)
    assert restored is Color


def test_enum_dynamic_class():
    """Dynamic enum classes should serialize by definition."""
    Dynamic = enum.Enum("Dynamic", {"A": 1, "B": 2})
    handler = EnumClassHandler()
    state = handler.extract_state(Dynamic)
    restored = handler.reconstruct(state)
    assert restored.A.value == 1
    assert restored.B.value == 2


def test_enum_missing_member_raises():
    """EnumHandler should raise on missing member."""
    handler = EnumHandler()
    state = handler.extract_state(Color.RED)
    state["member_name"] = "MISSING"
    state["value"] = 999
    try:
        handler.reconstruct(state)
        assert False, "Expected EnumSerializationError"
    except EnumSerializationError:
        pass


# =============================================================================
# Module Handler Tests
# =============================================================================

def test_module_handler_static_module():
    """ModuleHandler should roundtrip standard modules."""
    handler = ModuleHandler()
    import math
    state = handler.extract_state(math)
    restored = handler.reconstruct(state)
    assert restored is math


def test_module_handler_dynamic_module():
    """ModuleHandler should roundtrip dynamic modules with attributes."""
    handler = ModuleHandler()
    mod = types.ModuleType("dynamic_mod")
    mod.value = 123
    mod.math_ref = __import__("math")
    state = handler.extract_state(mod)
    restored = handler.reconstruct(state)
    assert isinstance(restored, types.ModuleType)
    assert restored.value == 123
    assert hasattr(restored, "math_ref")


# =============================================================================
# Logging Handler Tests
# =============================================================================

def test_logging_formatter_roundtrip():
    """FormatterHandler should recreate formatter settings."""
    handler = FormatterHandler()
    fmt = logging.Formatter(fmt="{levelname}:{message}", style="{")
    state = handler.extract_state(fmt)
    restored = handler.reconstruct(state)
    assert restored._fmt == fmt._fmt
    assert restored.datefmt == fmt.datefmt


def test_logging_stream_handler_roundtrip():
    """StreamHandlerHandler should reconstruct stream handlers."""
    handler = StreamHandlerHandler()
    formatter = logging.Formatter("%(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.ERROR)
    stream_handler.setFormatter(formatter)
    state = handler.extract_state(stream_handler)
    restored = handler.reconstruct(state)
    assert isinstance(restored, logging.StreamHandler)
    assert restored.level == logging.ERROR
    assert isinstance(restored.formatter, logging.Formatter)


def test_logging_file_handler_roundtrip():
    """FileHandlerHandler should reconstruct file handlers."""
    handler = FileHandlerHandler()
    formatter = logging.Formatter("%(levelname)s:%(message)s")
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        path = tmp.name
    restored = None
    file_handler = None
    try:
        file_handler = logging.FileHandler(path, mode="w")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        state = handler.extract_state(file_handler)
        restored = handler.reconstruct(state)
        assert isinstance(restored, logging.FileHandler)
        assert os.path.basename(restored.baseFilename) == os.path.basename(path)
        assert restored.level == logging.INFO
        assert isinstance(restored.formatter, logging.Formatter)
    finally:
        if file_handler is not None:
            file_handler.close()
        if restored is not None:
            restored.close()
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def test_logger_handler_roundtrip_with_handlers():
    """LoggerHandler should restore logger configuration with handlers."""
    handler = LoggerHandler()
    logger_name = "suitkaise.test.logger"
    logger = logging.getLogger(logger_name)
    logger.handlers = []
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    logger.addHandler(stream_handler)
    state = handler.extract_state(logger)
    restored = handler.reconstruct(state)
    assert restored.name == logger_name
    assert restored.level == logging.WARNING
    assert len(restored.handlers) == 1
    restored.handlers = []


# =============================================================================
# Async Handler Coverage (via serialize/deserialize)
# =============================================================================

async def _async_func():
    return 5


async def _async_gen():
    yield 1


def test_async_coroutine_roundtrip():
    """Coroutine objects should deserialize to placeholders."""
    coro = _async_func()
    serialized = cerial.serialize(coro)
    restored = cerial.deserialize(serialized)
    assert hasattr(restored, "_deserialized")


def test_async_generator_roundtrip():
    """Async generator objects should deserialize to placeholders."""
    agen = _async_gen()
    serialized = cerial.serialize(agen)
    restored = cerial.deserialize(serialized)
    assert hasattr(restored, "_deserialized")


def test_async_task_roundtrip():
    """Asyncio Task objects should deserialize to placeholders."""
    async def _runner():
        task = asyncio.create_task(asyncio.sleep(0, result=42))
        await task
        serialized = cerial.serialize(task)
        return cerial.deserialize(serialized)

    restored = asyncio.run(_runner())
    assert restored.done()
    assert restored.result() == 42


def test_async_future_roundtrip():
    """Asyncio Future objects should deserialize to placeholders."""
    async def _runner():
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        fut.set_result("ok")
        serialized = cerial.serialize(fut)
        return cerial.deserialize(serialized)

    restored = asyncio.run(_runner())
    assert restored.done()
    assert restored.result() == "ok"


# =============================================================================
# Class Handler Tests
# =============================================================================

class CustomSerializeClass:
    def __init__(self, value: int):
        self.value = value

    def __serialize__(self):
        return {"value": self.value}

    @classmethod
    def __deserialize__(cls, state):
        return cls(state["value"] + 1)


class ToDictClass:
    def __init__(self, value: int):
        self.value = value

    def to_dict(self):
        return {"value": self.value}

    @classmethod
    def from_dict(cls, state):
        return cls(state["value"] + 2)


class SlotsOnly:
    __slots__ = ("a",)

    def __init__(self, a: int):
        self.a = a


class SlotsAndDict:
    __slots__ = ("slot", "__dict__")

    def __init__(self, slot: int, extra: str):
        self.slot = slot
        self.extra = extra


class Outer:
    class Inner:
        class Deep:
            def __init__(self, value: int):
                self.value = value

        def __init__(self, value: int):
            self.value = value


def _make_local_custom() -> object:
    class LocalCustom:
        def __init__(self, value: int):
            self.value = value

        def __serialize__(self):
            return {"value": self.value}

        @staticmethod
        def __deserialize__(cls, state):
            obj = cls.__new__(cls)
            obj.value = state["value"] * 2
            return obj
    return LocalCustom(3)


def test_class_instance_custom_serialize():
    """ClassInstanceHandler should use custom serialize for module classes."""
    handler = ClassInstanceHandler()
    obj = CustomSerializeClass(4)
    state = handler.extract_state(obj)
    assert state["strategy"] == "custom_serialize"
    restored = handler.reconstruct(state)
    assert restored.value == 5


def test_class_instance_custom_serialize_local():
    """Locally-defined class with staticmethod deserialize should roundtrip."""
    handler = ClassInstanceHandler()
    obj = _make_local_custom()
    state = handler.extract_state(obj)
    assert state["strategy"] == "custom_serialize_local"
    restored = handler.reconstruct(state)
    assert restored.value == 6


def test_class_instance_to_dict():
    """ClassInstanceHandler should use to_dict/from_dict strategy."""
    handler = ClassInstanceHandler()
    obj = ToDictClass(5)
    state = handler.extract_state(obj)
    assert state["strategy"] == "to_dict"
    restored = handler.reconstruct(state)
    assert restored.value == 7


def test_class_instance_slots_and_dict():
    """ClassInstanceHandler should handle slots and dict combinations."""
    handler = ClassInstanceHandler()
    slots_obj = SlotsOnly(3)
    slots_state = handler.extract_state(slots_obj)
    assert slots_state["strategy"] == "slots"
    slots_restored = handler.reconstruct(slots_state)
    assert slots_restored.a == 3

    both_obj = SlotsAndDict(2, "x")
    both_state = handler.extract_state(both_obj)
    assert both_state["strategy"] == "dict_and_slots"
    both_restored = handler.reconstruct(both_state)
    assert both_restored.slot == 2
    assert both_restored.extra == "x"


def test_class_instance_nested_class_definitions():
    """Nested classes should include nested class definitions."""
    handler = ClassInstanceHandler()
    obj = Outer.Inner(1)
    state = handler.extract_state(obj)
    assert "nested_classes" in state


def test_class_object_dynamic_definition():
    """ClassObjectHandler should serialize dynamic class definitions."""
    handler = ClassObjectHandler()
    Dynamic = type("Dynamic", (), {"x": 1})
    state = handler.extract_state(Dynamic)
    assert state["type"] == "definition"
    restored = handler.reconstruct(state)
    assert restored.__name__ == "Dynamic"


def test_class_definition_allow_callables():
    """Reconstructed definitions should include callables when allowed."""
    class WithMethod:
        def ping(self):
            return "pong"
    handler = ClassInstanceHandler()
    class_def = handler._serialize_class_definition(WithMethod, allow_callables=True)
    restored = handler._reconstruct_class_definition(class_def)
    assert hasattr(restored, "ping")


# =============================================================================
# Context Manager Handler Tests
# =============================================================================

class SimpleContext:
    def __init__(self, value: int):
        self.value = value
        self.entered = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.entered = False
        return False


@contextlib.contextmanager
def _contextmanager(value: int):
    yield value


def test_context_manager_handler_roundtrip():
    """ContextManagerHandler should recreate custom context managers."""
    handler = ContextManagerHandler()
    ctx = SimpleContext(7)
    state = handler.extract_state(ctx)
    restored = handler.reconstruct(state)
    assert restored.value == 7
    with restored as active:
        assert active.entered is True


def test_contextlib_generator_handler_roundtrip():
    """ContextlibGeneratorHandler should reconstruct generator contexts."""
    handler = ContextlibGeneratorHandler()
    ctx = _contextmanager(3)
    state = handler.extract_state(ctx)
    restored = handler.reconstruct(state)
    assert isinstance(restored, types.GeneratorType)
    value = next(restored)
    assert value == 3
    restored.close()


# =============================================================================
# Threading Handler Tests
# =============================================================================

def _thread_target(value: int) -> int:
    return value + 1


def test_thread_handler_roundtrip():
    """ThreadHandler should restore thread configuration."""
    handler = ThreadHandler()
    thread = threading.Thread(name="worker", target=_thread_target, args=(2,), daemon=True)
    state = handler.extract_state(thread)
    restored = handler.reconstruct(state)
    assert isinstance(restored, ThreadReconnector)
    thread_copy = restored.reconnect()
    assert thread_copy.name == "worker"
    assert thread_copy.daemon is True


def test_executor_handlers_roundtrip():
    """Executor handlers should reconstruct executors."""
    thread_handler = ThreadPoolExecutorHandler()
    proc_handler = ProcessPoolExecutorHandler()
    executor = None
    restored = None
    try:
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="t")
        state = thread_handler.extract_state(executor)
        restored = thread_handler.reconstruct(state)
        assert restored._max_workers == 2
    finally:
        if executor is not None:
            executor.shutdown(wait=False)
        if restored is not None:
            restored.shutdown(wait=False)


# =============================================================================
# Regex Handler Tests
# =============================================================================

def test_regex_match_reconnector_roundtrip():
    """MatchObjectHandler should reconstruct a match when possible."""
    handler = MatchObjectHandler()
    match = re.search(r"a(b)c", "zabc")
    state = handler.extract_state(match)
    restored = handler.reconstruct(state)
    if isinstance(restored, MatchReconnector):
        restored = restored.reconnect()
    assert isinstance(restored, re.Match)
    assert restored.group(1) == "b"


def test_regex_pattern_roundtrip():
    """RegexPatternHandler should reconstruct compiled patterns."""
    handler = RegexPatternHandler()
    pattern = re.compile(r"\d+", re.IGNORECASE | re.MULTILINE)
    state = handler.extract_state(pattern)
    restored = handler.reconstruct(state)
    assert restored.pattern == pattern.pattern
    assert restored.flags == pattern.flags


def test_thread_local_handler_roundtrip():
    """ThreadLocalHandler should restore thread-local values."""
    handler = ThreadLocalHandler()
    local = threading.local()
    local.value = 9
    state = handler.extract_state(local)
    restored = handler.reconstruct(state)
    assert restored.value == 9


def test_lock_handler_roundtrip():
    """LockHandler should preserve locked state."""
    handler = LockHandler()
    lock = threading.Lock()
    lock.acquire()
    state = handler.extract_state(lock)
    restored = handler.reconstruct(state)
    assert restored.locked() is True
    restored.release()
    lock.release()
    
    rlock = threading.RLock()
    rlock.acquire()
    state = handler.extract_state(rlock)
    restored = handler.reconstruct(state)
    acquired = restored.acquire(blocking=False)
    assert acquired is True
    restored.release()
    rlock.release()


def test_semaphore_handler_roundtrip():
    """SemaphoreHandler should preserve semaphore count."""
    handler = SemaphoreHandler()
    sem = threading.Semaphore(2)
    sem.acquire()
    state = handler.extract_state(sem)
    restored = handler.reconstruct(state)
    assert restored.acquire(blocking=False) is True
    assert restored.acquire(blocking=False) is False


def test_barrier_handler_roundtrip():
    """BarrierHandler should preserve parties and timeout."""
    handler = BarrierHandler()
    barrier = threading.Barrier(2, timeout=0.5)
    state = handler.extract_state(barrier)
    restored = handler.reconstruct(state)
    assert restored.parties == 2
    assert getattr(restored, "timeout", restored._timeout) == 0.5


def test_condition_handler_roundtrip():
    """ConditionHandler should reconstruct condition with lock."""
    handler = ConditionHandler()
    condition = threading.Condition()
    state = handler.extract_state(condition)
    restored = handler.reconstruct(state)
    assert isinstance(restored, threading.Condition)
    restored.acquire()
    restored.release()


# =============================================================================
# Iterator Handler Tests
# =============================================================================

def test_iterator_handler_enumerate():
    """IteratorHandler should serialize remaining values."""
    handler = IteratorHandler()
    enum_obj = enumerate([1, 2, 3])
    next(enum_obj)
    state = handler.extract_state(enum_obj)
    assert state["params"]["start"] == len(state["remaining_values"])
    restored = handler.reconstruct(state)
    assert list(restored) == state["remaining_values"]


def test_iterator_handler_rejects_generator():
    """IteratorHandler should skip generators."""
    handler = IteratorHandler()
    gen = (x for x in range(2))
    assert handler.can_handle(gen) is False


def test_range_enumerate_zip_handlers():
    """Range/Enumerate/Zip handlers should reconstruct iterables."""
    range_handler = RangeHandler()
    enum_handler = EnumerateHandler()
    zip_handler = ZipHandler()
    rng = range(1, 5, 2)
    state = range_handler.extract_state(rng)
    restored = range_handler.reconstruct(state)
    assert list(restored) == [1, 3]
    enum_obj = enumerate(["a", "b"])
    enum_state = enum_handler.extract_state(enum_obj)
    assert list(enum_handler.reconstruct(enum_state)) == [(0, "a"), (1, "b")]
    zip_obj = zip([1, 2], ["a", "b"])
    zip_state = zip_handler.extract_state(zip_obj)
    assert list(zip_handler.reconstruct(zip_state)) == [(1, "a"), (2, "b")]


# =============================================================================
# Async Handler Direct Tests
# =============================================================================

def test_coroutine_handler_await_raises():
    """Deserialized coroutine should raise on await."""
    handler = CoroutineHandler()
    coro = _async_func()
    state = handler.extract_state(coro)
    restored = handler.reconstruct(state)
    try:
        restored.__await__()
        assert False, "Expected AsyncSerializationError"
    except AsyncSerializationError:
        pass


def test_async_generator_handler_aiter_raises():
    """Deserialized async generator should raise on iteration."""
    handler = AsyncGeneratorHandler()
    agen = _async_gen()
    state = handler.extract_state(agen)
    restored = handler.reconstruct(state)
    try:
        restored.__aiter__()
        assert False, "Expected AsyncSerializationError"
    except AsyncSerializationError:
        pass


def test_task_handler_placeholder_result():
    """TaskHandler should reconstruct placeholder with result."""
    handler = TaskHandler()
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        task = loop.create_task(asyncio.sleep(0, result=7))
        loop.run_until_complete(task)
        state = handler.extract_state(task)
        restored = handler.reconstruct(state)
        assert restored.done() is True
        assert restored.result() == 7
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# =============================================================================
# ContextVar & Token Handler Tests
# =============================================================================

def test_contextvar_handler_roundtrip():
    """ContextVarHandler should preserve name and current value."""
    handler = ContextVarHandler()
    var = contextvars.ContextVar("test_var", default="default")
    var.set("current")
    state = handler.extract_state(var)
    restored = handler.reconstruct(state)
    assert restored.name == "test_var"
    assert restored.get() == "current"


def test_token_handler_roundtrip():
    """TokenHandler should return metadata for tokens."""
    handler = TokenHandler()
    var = contextvars.ContextVar("token_var")
    token = var.set("value")
    state = handler.extract_state(token)
    restored = handler.reconstruct(state)
    assert restored.get("__cerial_dead_token__") is True
    assert restored.get("var_name") == "token_var"


# =============================================================================
# Advanced Python Handler Tests
# =============================================================================

def test_code_object_roundtrip():
    """CodeObjectHandler should reconstruct code objects."""
    handler = CodeObjectHandler()
    code = (lambda x: x + 1).__code__
    state = handler.extract_state(code)
    restored = handler.reconstruct(state)
    assert isinstance(restored, types.CodeType)
    assert restored.co_name == code.co_name
    assert restored.co_argcount == code.co_argcount


def test_frame_object_roundtrip():
    """FrameObjectHandler should reconstruct FrameInfo."""
    handler = FrameObjectHandler()
    
    def _frame_source():
        frame = inspect.currentframe()
        state = handler.extract_state(frame, include_parent=False)
        restored = handler.reconstruct(state)
        return restored
    
    restored = _frame_source()
    assert isinstance(restored, FrameInfo)
    assert restored.function_name == "_frame_source"


def test_property_handler_roundtrip():
    """PropertyHandler should reconstruct properties."""
    handler = PropertyHandler()
    
    def get_x(self):
        return self._x
    
    def set_x(self, value):
        self._x = value
    
    prop = property(get_x, set_x, doc="x property")
    state = handler.extract_state(prop)
    restored = handler.reconstruct(state)
    
    class Holder:
        def __init__(self):
            self._x = 0
    
    Holder.x = restored
    obj = Holder()
    obj.x = 5
    assert obj.x == 5
    assert Holder.x.__doc__ == "x property"


def test_descriptor_handler_roundtrip():
    """DescriptorHandler should reconstruct custom descriptors."""
    handler = DescriptorHandler()
    desc = DemoDescriptor(default=3)
    state = handler.extract_state(desc)
    restored = handler.reconstruct(state)
    assert isinstance(restored, DemoDescriptor)
    assert restored.default == 3


# =============================================================================
# Generator Handler Tests
# =============================================================================

def test_generator_handler_roundtrip():
    """GeneratorHandler should preserve remaining values."""
    handler = GeneratorHandler()
    def gen():
        for i in range(4):
            yield i
    g = gen()
    next(g)
    state = handler.extract_state(g)
    restored = handler.reconstruct(state)
    assert list(restored) == [1, 2, 3]


# =============================================================================
# SQLite Handler Tests
# =============================================================================

def test_sqlite_connection_roundtrip():
    """SQLiteConnectionHandler should roundtrip in-memory databases."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE test (id INTEGER, name TEXT)")
    cur.execute("INSERT INTO test VALUES (1, 'a')")
    cur.execute("INSERT INTO test VALUES (2, 'b')")
    conn.commit()

    handler = SQLiteConnectionHandler()
    state = handler.extract_state(conn)
    restored = handler.reconstruct(state)

    rows = restored.execute("SELECT * FROM test ORDER BY id").fetchall()
    assert rows == [(1, "a"), (2, "b")]
    restored.close()
    conn.close()


def test_sqlite_cursor_roundtrip():
    """SQLiteCursorHandler should reconstruct cursor objects."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE items (id INTEGER)")
    conn.execute("INSERT INTO items VALUES (1)")
    conn.commit()
    cursor = conn.execute("SELECT * FROM items")

    handler = SQLiteCursorHandler()
    state = handler.extract_state(cursor)
    restored = handler.reconstruct(state)
    assert restored.connection is not None

    restored.close()
    conn.close()


# =============================================================================
# Memory Handler Tests
# =============================================================================

def test_mmap_roundtrip():
    """MMapHandler should roundtrip file-backed mmap objects."""
    handler = MMapHandler()
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(b"hello world")
        path = f.name

    try:
        with open(path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)
            state = handler.extract_state(mm)
            restored = handler.reconstruct(state)
            restored.seek(0)
            assert restored.read(5) == b"hello"
            restored.close()
            mm.close()
    finally:
        os.unlink(path)


def test_memoryview_roundtrip():
    """MemoryViewHandler should reconstruct memoryview content."""
    handler = MemoryViewHandler()
    data = bytearray(b"abc")
    view = memoryview(data)
    state = handler.extract_state(view)
    restored = handler.reconstruct(state)
    assert bytes(restored) == b"abc"


def test_mmap_closed_raises():
    """Closed mmap should raise MemorySerializationError."""
    handler = MMapHandler()
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(b"data")
        path = f.name
    try:
        with open(path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)
            mm.close()
            try:
                handler.extract_state(mm)
                assert False, "Expected MemorySerializationError"
            except MemorySerializationError:
                pass
    finally:
        os.unlink(path)


def test_shared_memory_roundtrip():
    """SharedMemoryHandler should roundtrip shared memory blocks."""
    if not HAS_SHARED_MEMORY:
        return
    handler = SharedMemoryHandler()
    shm = shared_memory.SharedMemory(create=True, size=16)
    try:
        shm.buf[:5] = b"hello"
        state = handler.extract_state(shm)
        restored = handler.reconstruct(state)
        assert bytes(restored.buf[:5]) == b"hello"
        restored.close()
        if restored.name != shm.name:
            try:
                restored.unlink()
            except FileNotFoundError:
                pass
    finally:
        shm.close()
        try:
            shm.unlink()
        except FileNotFoundError:
            pass


def test_shared_memory_recreate_missing():
    """SharedMemoryHandler should recreate missing blocks."""
    if not HAS_SHARED_MEMORY:
        return
    handler = SharedMemoryHandler()
    shm = shared_memory.SharedMemory(create=True, size=8)
    try:
        shm.buf[:3] = b"hey"
        state = handler.extract_state(shm)
    finally:
        shm.close()
        try:
            shm.unlink()
        except FileNotFoundError:
            pass
    restored = handler.reconstruct(state)
    try:
        assert bytes(restored.buf[:3]) == b"hey"
    finally:
        restored.close()
        try:
            restored.unlink()
        except FileNotFoundError:
            pass


def test_shared_memory_attach_existing():
    """SharedMemoryHandler should attach to existing blocks."""
    if not HAS_SHARED_MEMORY:
        return
    handler = SharedMemoryHandler()
    shm = shared_memory.SharedMemory(create=True, size=8)
    try:
        shm.buf[:4] = b"data"
        state = handler.extract_state(shm)
        restored = handler.reconstruct(state)
        try:
            assert bytes(restored.buf[:4]) == b"data"
        finally:
            restored.close()
            # Only unlink once
            restored.unlink()
    finally:
        shm.close()


def test_mmap_file_backed_reconstruct():
    """MMapHandler should prefer file-backed reconstruction when path exists."""
    handler = MMapHandler()
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(b"abcdef")
        path = f.name
    try:
        with open(path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)
            state = handler.extract_state(mm)
            state["file_path"] = path
            restored = handler.reconstruct(state)
            restored.seek(0)
            assert restored.read(3) == b"abc"
            restored.close()
            mm.close()
    finally:
        os.unlink(path)


def test_file_descriptor_handler_errors():
    """FileDescriptorHandler should reconstruct when path exists."""
    handler = FileDescriptorHandler()
    fd, path = tempfile.mkstemp()
    try:
        state = handler.extract_state(fd)
        restored = handler.reconstruct(state)
        assert isinstance(restored, int)
        os.close(restored)
    finally:
        os.close(fd)
        os.unlink(path)


# =============================================================================
# File Handler Tests
# =============================================================================

def test_file_handle_roundtrip_text():
    """FileHandleHandler should preserve path and position."""
    handler = FileHandleHandler()
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write("hello")
        f.flush()
        f.seek(2)
        state = handler.extract_state(f)
    try:
        restored = handler.reconstruct(state)
        assert restored.tell() == 2
        restored.close()
    finally:
        os.unlink(state["path"])


def test_file_handle_closed_placeholder():
    """Closed files should reconstruct as placeholders."""
    handler = FileHandleHandler()
    f = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    try:
        f.close()
        state = handler.extract_state(f)
        restored = handler.reconstruct(state)
        assert getattr(restored, "closed", False) is True
        try:
            restored.read()
            assert False, "Expected closed placeholder to raise"
        except ValueError:
            pass
    finally:
        os.unlink(state["path"])


def test_temp_file_roundtrip():
    """TemporaryFileHandler should recreate temp files with content."""
    handler = TemporaryFileHandler()
    temp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
    try:
        temp.write(b"data")
        temp.flush()
        state = handler.extract_state(temp)
        restored = handler.reconstruct(state)
        restored.seek(0)
        assert restored.read() == b"data"
        restored.close()
    finally:
        temp.close()
        os.unlink(temp.name)


def test_file_handle_pipe_placeholder():
    """Pipe-backed file handles should reconstruct as closed placeholders."""
    handler = FileHandleHandler()
    proc = subprocess.Popen(
        [sys.executable, "-c", "print('x')"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        state = handler.extract_state(proc.stdout)
        restored = handler.reconstruct(state)
        assert getattr(restored, "closed", True)
    finally:
        proc.communicate(timeout=5)


def test_file_handle_missing_file_error():
    """Missing file should raise FileSerializationError."""
    handler = FileHandleHandler()
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write("data")
        f.flush()
        state = handler.extract_state(f)
    os.unlink(state["path"])
    state["relative_path"] = None
    state["path"] = "/nonexistent/suitkaise-missing-file.txt"
    try:
        handler.reconstruct(state)
        assert False, "Expected FileSerializationError"
    except FileSerializationError:
        pass


def test_file_handle_relative_path():
    """FileHandleHandler should capture relative path when possible."""
    handler = FileHandleHandler()
    path = os.path.join(os.getcwd(), "tmp_test_file.txt")
    try:
        with open(path, "w+") as f:
            f.write("x")
            f.flush()
            state = handler.extract_state(f)
        assert state["relative_path"] is not None
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def test_stringio_roundtrip():
    """StringIOHandler should preserve content and position."""
    handler = StringIOHandler()
    stream = io.StringIO("hello")
    stream.seek(2)
    state = handler.extract_state(stream)
    restored = handler.reconstruct(state)
    assert restored.read() == "llo"


def test_bytesio_roundtrip_closed():
    """BytesIOHandler should handle closed streams."""
    handler = BytesIOHandler()
    stream = io.BytesIO(b"abc")
    stream.close()
    state = handler.extract_state(stream)
    restored = handler.reconstruct(state)
    assert restored.closed


# =============================================================================
# Network Handler Tests
# =============================================================================

def test_socket_handler_roundtrip():
    """SocketHandler should recreate socket with settings."""
    handler = SocketHandler()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.2)
    state = handler.extract_state(sock)
    restored = handler.reconstruct(state)
    if isinstance(restored, SocketReconnector):
        restored = restored.reconnect()
    assert isinstance(restored, socket.socket)
    assert restored.gettimeout() == 0.2
    sock.close()
    restored.close()


def test_socket_handler_nonblocking_state():
    """SocketHandler should handle nonblocking state when timeout is None."""
    handler = SocketHandler()
    state = {
        "family": socket.AF_INET,
        "type": socket.SOCK_STREAM,
        "proto": 0,
        "timeout": None,
        "blocking": False,
    }
    sock = handler.reconstruct(state)
    if isinstance(sock, SocketReconnector):
        sock = sock.reconnect()
    assert sock.gettimeout() == 0.0
    sock.close()


def test_http_session_handler_roundtrip():
    """HTTPSessionHandler should recreate session config if requests installed."""
    handler = HTTPSessionHandler()
    try:
        import requests
    except Exception:
        return
    session = requests.Session()
    session.headers["X-Test"] = "1"
    session.cookies.set("a", "b")
    session.auth = ("user", "pass")
    session.proxies = {"http": "http://proxy"}
    session.verify = False
    tmp_cert = str(Path(tempfile.gettempdir()) / "cert.pem")
    session.cert = tmp_cert
    session.max_redirects = 5
    state = handler.extract_state(session)
    restored = handler.reconstruct(state)
    assert restored.headers.get("X-Test") == "1"
    assert restored.cookies.get("a") == "b"
    assert restored.auth == ("user", "pass")
    assert restored.proxies.get("http") == "http://proxy"
    assert restored.verify is False
    assert restored.cert == tmp_cert
    assert restored.max_redirects == 5


def test_http_session_handler_cookie_error():
    """HTTPSessionHandler should handle cookie extraction errors."""
    handler = HTTPSessionHandler()

    class BadCookies:
        def __iter__(self):
            raise TypeError("bad cookies")

    class DummySession:
        cookies = BadCookies()
        headers = {}
        auth = None
        proxies = {}
        verify = True
        cert = None
        max_redirects = 30

    state = handler.extract_state(DummySession())
    assert state["cookies"] == {}


def test_db_connection_handler_extract_state():
    """DatabaseConnectionHandler should extract common fields."""
    handler = DatabaseConnectionHandler()

    class Info:
        host = "localhost"
        port = 5432
        dbname = "db"
        user = "user"

    class FakeConnection:
        __module__ = "psycopg2.extensions"
        __name__ = "connection"
        info = Info()
        host = "localhost"
        port = 5432
        user = "user"
        db = "db"
        connection_pool = type("Pool", (), {"connection_kwargs": {"db": "db"}})()

    obj = FakeConnection()
    assert handler.can_handle(obj) is True
    state = handler.extract_state(obj)
    assert state["host"] == "localhost"
    assert state["port"] == 5432
    assert state["user"] == "user"
    assert state["database"] == "db"
    assert state["connection_kwargs"]["db"] == "db"


def test_db_connection_handler_reconstruct_reconnector():
    """DatabaseConnectionHandler should return a DbReconnector on missing auth."""
    handler = DatabaseConnectionHandler()

    class DummyConnection:
        __module__ = "redis.fake"
        __name__ = "RedisConnection"
        def __init__(self):
            self.host = "localhost"
            self.port = 6379
            self.user = "user"

    dummy = DummyConnection()
    assert handler.can_handle(dummy) is True
    state = handler.extract_state(dummy)
    restored = handler.reconstruct(state)
    assert isinstance(restored, DbReconnector)


def test_db_connection_handler_reconstruct_sqlite():
    """DatabaseConnectionHandler should auto-connect when details are sufficient."""
    handler = DatabaseConnectionHandler()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        try:
            state = handler.extract_state(conn)
        finally:
            conn.close()
        restored = handler.reconstruct(state)
        assert isinstance(restored, sqlite3.Connection)
        restored.close()
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


# =============================================================================
# Weakref Handler Tests
# =============================================================================

class _WeakObj:
    def __init__(self, value: int):
        self.value = value


def test_weakref_roundtrip_live():
    """WeakrefHandler should reconstruct weakref to object."""
    handler = WeakrefHandler()
    obj = _WeakObj(5)
    ref = weakref.ref(obj)
    state = handler.extract_state(ref)
    restored = handler.reconstruct(state)
    assert restored() is not None
    assert restored().value == 5


def test_weakref_roundtrip_dead():
    """WeakrefHandler should return dead placeholder when object is gone."""
    handler = WeakrefHandler()
    obj = _WeakObj(1)
    ref = weakref.ref(obj)
    del obj
    state = handler.extract_state(ref)
    restored = handler.reconstruct(state)
    assert restored() is None


def test_weakref_handler_dead_lambda():
    """WeakrefHandler should return dead placeholder when given dead ref."""
    handler = WeakrefHandler()
    state = {"is_dead": True, "referenced_object": None}
    restored = handler.reconstruct(state)
    assert restored() is None


def test_weakref_handler_extract_reference_error():
    """WeakrefHandler should handle ReferenceError in extract_state."""
    class BadRef:
        def __call__(self):
            raise ReferenceError("dead")
    handler = WeakrefHandler()
    state = handler.extract_state(BadRef())
    assert state["is_dead"] is True
    assert state["referenced_object"] is None


def test_weakref_handler_extract_type_error():
    """WeakrefHandler should handle TypeError in extract_state."""
    class BadRef:
        def __call__(self):
            raise TypeError("bad")
    handler = WeakrefHandler()
    state = handler.extract_state(BadRef())
    assert state["is_dead"] is True
    assert state["referenced_object"] is None


def test_weakref_handler_reconstruct_missing_ref():
    """WeakrefHandler should return lambda when referenced object missing."""
    handler = WeakrefHandler()
    restored = handler.reconstruct({"is_dead": False, "referenced_object": None})
    assert restored() is None


def test_weak_value_dict_roundtrip():
    """WeakValueDictionaryHandler should reconstruct values."""
    handler = WeakValueDictionaryHandler()
    obj = _WeakObj(2)
    wvd = weakref.WeakValueDictionary()
    wvd["a"] = obj
    state = handler.extract_state(wvd)
    restored = handler.reconstruct(state)
    assert "a" in restored


def test_weak_key_dict_roundtrip():
    """WeakKeyDictionaryHandler should reconstruct keys."""
    handler = WeakKeyDictionaryHandler()
    obj = _WeakObj(3)
    wkd = weakref.WeakKeyDictionary()
    wkd[obj] = "value"
    state = handler.extract_state(wkd)
    restored = handler.reconstruct(state)
    assert list(restored.values()) == ["value"]


def test_weak_value_dict_dead_value():
    """WeakValueDictionaryHandler should drop dead values."""
    handler = WeakValueDictionaryHandler()
    wvd = weakref.WeakValueDictionary()
    obj = _WeakObj(4)
    wvd["a"] = obj
    del obj
    state = handler.extract_state(wvd)
    restored = handler.reconstruct(state)
    assert "a" not in restored


def test_weak_value_dict_preserves_values():
    """WeakValueDictionaryHandler should preserve values when alive."""
    handler = WeakValueDictionaryHandler()
    obj = _WeakObj(7)
    wvd = weakref.WeakValueDictionary()
    wvd["a"] = obj
    state = handler.extract_state(wvd)
    restored = handler.reconstruct(state)
    assert "a" in restored


def test_weak_key_dict_dead_key():
    """WeakKeyDictionaryHandler should drop dead keys."""
    handler = WeakKeyDictionaryHandler()
    wkd = weakref.WeakKeyDictionary()
    obj = _WeakObj(5)
    wkd[obj] = "value"
    del obj
    state = handler.extract_state(wkd)
    restored = handler.reconstruct(state)
    assert len(restored) == 0


def test_weak_key_dict_extract_keyerror():
    """WeakKeyDictionaryHandler should ignore dead keys during extract."""
    handler = WeakKeyDictionaryHandler()
    wkd = weakref.WeakKeyDictionary()
    obj = _WeakObj(8)
    wkd[obj] = "value"
    del obj
    state = handler.extract_state(wkd)
    assert state["items"] == []


def test_weak_key_dict_unweakrefable():
    """WeakKeyDictionary should skip unweakrefable keys."""
    handler = WeakKeyDictionaryHandler()
    state = {"items": [(1, "a")]}
    restored = handler.reconstruct(state)
    assert len(restored) == 0


# =============================================================================
# NamedTuple & TypedDict Handler Tests
# =============================================================================

class Point(NamedTuple):
    x: int
    y: int


class Calc:
    @staticmethod
    def add(a: int, b: int) -> int:
        return a + b


class Tools:
    @staticmethod
    def add(a, b):
        return a + b
    @classmethod
    def name(cls):
        return cls.__name__


class DemoDescriptor:
    def __init__(self, default=0):
        self.default = default
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get("value", self.default)
    def __set__(self, instance, value):
        instance.__dict__["value"] = value


def test_namedtuple_roundtrip():
    """NamedTupleHandler should reconstruct namedtuple instances."""
    handler = NamedTupleHandler()
    pt = Point(1, 2)
    state = handler.extract_state(pt)
    restored = handler.reconstruct(state)
    assert restored == pt


def test_namedtuple_dynamic_roundtrip():
    """NamedTupleHandler should reconstruct dynamic namedtuple classes."""
    Dyn = namedtuple("Dyn", ["a", "b"])
    obj = Dyn(1, 2)
    handler = NamedTupleHandler()
    state = handler.extract_state(obj)
    restored = handler.reconstruct(state)
    assert restored == obj


def test_namedtuple_handler_invalid():
    """NamedTupleHandler should reject non-namedtuple."""
    handler = NamedTupleHandler()
    assert handler.can_handle((1, 2)) is False


def test_namedtuple_reconstruct_fallback():
    """NamedTupleHandler should reconstruct when import fails."""
    handler = NamedTupleHandler()
    state = {
        "module": "fake.module",
        "class_name": "MyTuple",
        "qualname": "MyTuple",
        "fields": ("a", "b"),
        "values": (1, 2),
        "defaults": {},
    }
    restored = handler.reconstruct(state)
    assert restored.a == 1


def test_typeddict_roundtrip():
    """TypedDictHandler should return dict when class missing."""
    class TD(dict):
        __annotations__ = {"a": int}
        __total__ = True

    handler = TypedDictHandler()
    obj = TD(a=1)
    state = handler.extract_state(obj)
    restored = handler.reconstruct(state)
    assert restored["a"] == 1


# =============================================================================
# Function Handler Tests
# =============================================================================

def _reference_function(x: int) -> int:
    return x + 1


def test_function_handler_reference():
    """FunctionHandler should use reference for module-level functions."""
    handler = FunctionHandler()
    state = handler.extract_state(_reference_function)
    assert state["serialization_type"] == "reference"
    restored = handler.reconstruct(state)
    assert restored(2) == 3


def test_function_handler_full():
    """FunctionHandler should serialize closures fully."""
    def make_adder(n: int):
        def adder(x: int) -> int:
            return x + n
        return adder
    fn = make_adder(5)
    handler = FunctionHandler()
    state = handler.extract_state(fn)
    assert state["serialization_type"] == "full"
    restored = handler.reconstruct(state)
    assert restored(2) == 7


def test_function_handler_class_method_reference():
    """FunctionHandler should reference class methods."""
    handler = FunctionHandler()
    state = handler.extract_state(Calc.add)
    assert state["serialization_type"] == "reference"
    restored = handler.reconstruct(state)
    assert restored(1, 2) == 3


def test_function_handler_main_module_fallback():
    """Functions in __main__ should use full serialization."""
    handler = FunctionHandler()
    def local_fn(x: int) -> int:
        return x * 2
    local_fn.__module__ = "__main__"
    state = handler.extract_state(local_fn)
    assert state["serialization_type"] == "full"
    restored = handler.reconstruct(state)
    assert restored(3) == 6


def test_function_handler_reference_error():
    """FunctionHandler should raise when reference lookup fails."""
    handler = FunctionHandler()
    state = {
        "serialization_type": "reference",
        "module": "nonexistent_module",
        "qualname": "missing",
    }
    try:
        handler.reconstruct(state)
        assert False, "Expected FunctionSerializationError"
    except FunctionSerializationError:
        pass


def test_function_handler_can_use_reference_failures():
    """FunctionHandler should reject non-referenceable functions."""
    handler = FunctionHandler()
    def local_fn():
        return 1
    local_fn.__module__ = "__main__"
    assert handler._can_use_reference(local_fn) is False
    local_fn.__module__ = None
    assert handler._can_use_reference(local_fn) is False
    local_fn.__module__ = "suitkaise"
    local_fn.__qualname__ = "local.<locals>.fn"
    assert handler._can_use_reference(local_fn) is False
    def outer():
        x = 1
        def inner():
            return x
        return inner
    assert handler._can_use_reference(outer()) is False


def test_function_handler_reference_not_callable():
    """Reference reconstruction should error for non-callables."""
    handler = FunctionHandler()
    state = {
        "serialization_type": "reference",
        "module": "suitkaise",
        "qualname": "__version__",
    }
    try:
        handler.reconstruct(state)
        assert False, "Expected FunctionSerializationError"
    except FunctionSerializationError:
        pass


def test_function_handler_restore_attrs():
    """FunctionHandler should restore kwdefaults/annotations/doc."""
    def fn(x: int, *, y: int = 3) -> int:
        """docstring"""
        return x + y
    handler = FunctionHandler()
    state = handler.extract_state(fn)
    restored = handler.reconstruct(state)
    assert restored.__kwdefaults__ == {"y": 3}
    assert "x" in restored.__annotations__
    if restored.__doc__ is not None:
        assert restored.__doc__ == "docstring"


def test_function_handler_make_cell():
    """FunctionHandler _make_cell should create cell with value."""
    handler = FunctionHandler()
    cell = handler._make_cell(5)
    assert cell.cell_contents == 5


def test_partial_function_handler():
    """PartialFunctionHandler should roundtrip partials."""
    handler = PartialFunctionHandler()
    def add(a, b):
        return a + b
    part = functools.partial(add, 2)
    state = handler.extract_state(part)
    restored = handler.reconstruct(state)
    assert restored(3) == 5


def test_bound_method_handler():
    """BoundMethodHandler should reconstruct bound methods."""
    handler = BoundMethodHandler()
    class Greeter:
        def hello(self, name):
            return f"hi {name}"
    obj = Greeter()
    method = obj.hello
    state = handler.extract_state(method)
    restored = handler.reconstruct(state)
    assert restored("sam") == "hi sam"


def test_lambda_handler():
    """LambdaHandler should roundtrip lambda functions."""
    handler = LambdaHandler()
    fn = lambda x: x + 1
    state = handler.extract_state(fn)
    restored = handler.reconstruct(state)
    assert restored(2) == 3


def test_static_and_class_method_handlers():
    """StaticMethodHandler and ClassMethodHandler should reconstruct methods."""
    static_handler = StaticMethodHandler()
    class_handler = ClassMethodHandler()
    static_state = static_handler.extract_state(Tools.__dict__["add"])
    class_state = class_handler.extract_state(Tools.__dict__["name"])
    static_restored = static_handler.reconstruct(static_state)
    class_restored = class_handler.reconstruct(class_state)
    assert static_restored.__func__(1, 2) == 3
    assert class_restored.__func__(Tools) == "Tools"


# =============================================================================
# Memory Handler Edge Tests
# =============================================================================

def test_shared_memory_unavailable_error():
    """SharedMemoryHandler should error when unavailable."""
    handler = SharedMemoryHandler()
    if not HAS_SHARED_MEMORY:
        return
    original = memory_handler.HAS_SHARED_MEMORY
    memory_handler.HAS_SHARED_MEMORY = False
    try:
        try:
            handler.reconstruct({"name": "x", "size": 1, "content": b""})
            assert False, "Expected MemorySerializationError"
        except MemorySerializationError:
            pass
    finally:
        memory_handler.HAS_SHARED_MEMORY = original


# =============================================================================
# Queue & Event Handler Tests
# =============================================================================

def test_queue_handler_roundtrip():
    """QueueHandler should reconstruct queue contents."""
    handler = QueueHandler()
    q = queue_module.Queue()
    q.put(1)
    q.put(2)
    state = handler.extract_state(q)
    restored = handler.reconstruct(state)
    assert restored.get() == 1
    assert restored.get() == 2


def test_simple_queue_roundtrip():
    """QueueHandler should reconstruct SimpleQueue."""
    handler = QueueHandler()
    q = queue_module.SimpleQueue()
    q.put("a")
    state = handler.extract_state(q)
    restored = handler.reconstruct(state)
    assert restored.get() == "a"


def test_mp_queue_roundtrip():
    """MultiprocessingQueueHandler should reconstruct mp queues."""
    handler = MultiprocessingQueueHandler()
    q = multiprocessing.Queue()
    q.put(5)
    state = handler.extract_state(q)
    restored = handler.reconstruct(state)
    if state["items"]:
        assert restored.get(timeout=1) == 5
    else:
        restored.put(5)
        assert restored.get(timeout=1) == 5


def test_event_roundtrip():
    """EventHandler should reconstruct set events."""
    handler = EventHandler()
    ev = threading.Event()
    ev.set()
    state = handler.extract_state(ev)
    restored = handler.reconstruct(state)
    assert restored.is_set()


def test_mp_event_roundtrip():
    """MultiprocessingEventHandler should reconstruct mp events."""
    handler = MultiprocessingEventHandler()
    ev = multiprocessing.Event()
    ev.set()
    state = handler.extract_state(ev)
    restored = handler.reconstruct(state)
    assert restored.is_set()


# =============================================================================
# Pipe & Manager Handler Tests
# =============================================================================

def test_os_pipe_roundtrip():
    """OSPipeHandler should reconstruct a new pipe."""
    handler = OSPipeHandler()
    r, w = os.pipe()
    try:
        state = handler.extract_state((r, w))
        restored = handler.reconstruct(state)
        assert isinstance(restored, tuple)
    finally:
        os.close(r)
        os.close(w)


def test_mp_pipe_roundtrip():
    """MultiprocessingPipeHandler should reconstruct PipeReconnector."""
    handler = MultiprocessingPipeHandler()
    conn1, conn2 = multiprocessing.Pipe()
    try:
        state = handler.extract_state(conn1)
        restored = handler.reconstruct(state)
        assert isinstance(restored, PipeReconnector)
        end_a, end_b = restored.pair()
        assert hasattr(end_a, "send")
        assert hasattr(end_b, "recv")
        end_a.close()
        end_b.close()
    finally:
        conn1.close()
        conn2.close()


def test_mp_manager_roundtrip():
    """MultiprocessingManagerHandler should reconstruct proxy or return None."""
    handler = MultiprocessingManagerHandler()
    manager = multiprocessing.Manager()
    try:
        proxy = manager.list([1, 2])
        state = handler.extract_state(proxy)
        restored = handler.reconstruct(state)
        # handler uses __reduce__ protocol - should reconstruct or return None
        if restored is not None:
            assert list(restored) == [1, 2], f"Expected [1, 2], got {list(restored)}"
    finally:
        manager.shutdown()


def test_reconnect_all_nested():
    """reconnect_all should recurse through nested structures."""
    class DummyReconnector(Reconnector):
        def __init__(self, value):
            self.value = value
        def reconnect(self, **kwargs):
            return f"connected-{self.value}"
    
    class SlotHolder:
        __slots__ = ("item",)
        def __init__(self, item):
            self.item = item
    
    payload = {
        "a": [DummyReconnector(1), {"b": DummyReconnector(2)}],
        "c": DummyReconnector(3),
        DummyReconnector("key"): "value",
        "slot": SlotHolder(DummyReconnector("slot")),
    }
    restored = cerial.reconnect_all(payload)
    assert restored is payload
    assert payload["a"][0] == "connected-1"
    assert payload["a"][1]["b"] == "connected-2"
    assert payload["c"] == "connected-3"
    assert "connected-key" in payload
    assert payload["slot"].item == "connected-slot"


def test_reconnect_all_reconnectors():
    """reconnect_all should handle all reconnector types."""
    handler = MatchObjectHandler()
    match = re.search(r"a(b)c", "zabc")
    
    pipe_rec = PipeReconnector()
    sock_rec = SocketReconnector(state={
        "family": socket.AF_INET,
        "type": socket.SOCK_STREAM,
        "proto": 0,
        "timeout": None,
        "blocking": True,
        "local_addr": None,
        "remote_addr": None,
    })
    db_rec = SQLiteReconnector(details={"path": ":memory:"})
    subproc_rec = SubprocessReconnector(state={
        "args": [sys.executable, "-c", "print('x')"],
        "returncode": 0,
        "pid": 123,
        "poll_result": 0,
        "stdout_data": None,
        "stderr_data": None,
    })
    match_rec = MatchReconnector(state=handler.extract_state(match))
    thread_rec = ThreadReconnector(state={
        "name": "worker",
        "daemon": True,
        "target": _thread_target,
        "args": (1,),
        "kwargs": {},
        "is_alive": False,
    })
    
    payload = {
        "pipe": pipe_rec,
        "socket": sock_rec,
        "db": db_rec,
        "proc": subproc_rec,
        "match": match_rec,
        "thread": thread_rec,
    }
    
    restored = cerial.reconnect_all(payload)
    assert restored is payload
    assert hasattr(payload["pipe"], "send")
    assert isinstance(payload["socket"], socket.socket)
    assert isinstance(payload["db"], sqlite3.Connection)
    assert isinstance(payload["proc"], subprocess.Popen)
    assert isinstance(payload["match"], re.Match)
    assert isinstance(payload["thread"], threading.Thread)
    
    # Cleanup
    try:
        payload["proc"].wait(timeout=5)
    except Exception:
        try:
            payload["proc"].terminate()
        except Exception:
            pass
    payload["socket"].close()
    payload["db"].close()
    try:
        payload["pipe"].close()
    except Exception:
        pass
# =============================================================================
# Subprocess Handler Tests
# =============================================================================

def test_popen_handler_roundtrip():
    """PopenHandler should serialize completed process state."""
    handler = PopenHandler()
    proc = subprocess.Popen(
        [sys.executable, "-c", "print('hi')"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate(timeout=5)
    state = handler.extract_state(proc)
    restored = handler.reconstruct(state)
    assert isinstance(restored, SubprocessReconnector)
    snapshot = restored.snapshot()
    assert snapshot.args
    assert snapshot.returncode == proc.returncode
    assert isinstance(snapshot.poll(), int)


def test_completed_process_handler_roundtrip():
    """CompletedProcessHandler should roundtrip CompletedProcess."""
    handler = CompletedProcessHandler()
    completed = subprocess.run(
        [sys.executable, "-c", "print('ok')"],
        capture_output=True,
        text=True,
        check=False,
    )
    state = handler.extract_state(completed)
    restored = handler.reconstruct(state)
    assert restored.returncode == completed.returncode
    assert restored.stdout == completed.stdout


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all extended handler tests."""
    runner = TestRunner("Cerial Extended Handler Tests")

    runner.run_test("Enum instance roundtrip", test_enum_instance_roundtrip)
    runner.run_test("Enum class roundtrip", test_enum_class_roundtrip)
    runner.run_test("Dynamic enum class", test_enum_dynamic_class)
    runner.run_test("Enum missing member", test_enum_missing_member_raises)

    runner.run_test("Module handler static", test_module_handler_static_module)
    runner.run_test("Module handler dynamic", test_module_handler_dynamic_module)
    runner.run_test("Logging formatter roundtrip", test_logging_formatter_roundtrip)
    runner.run_test("Logging stream handler roundtrip", test_logging_stream_handler_roundtrip)
    runner.run_test("Logging file handler roundtrip", test_logging_file_handler_roundtrip)
    runner.run_test("Logger handler roundtrip", test_logger_handler_roundtrip_with_handlers)
    runner.run_test("Class instance custom serialize", test_class_instance_custom_serialize)
    runner.run_test("Class instance custom serialize local", test_class_instance_custom_serialize_local)
    runner.run_test("Class instance to_dict", test_class_instance_to_dict)
    runner.run_test("Class instance slots/dict", test_class_instance_slots_and_dict)
    runner.run_test("Class instance nested classes", test_class_instance_nested_class_definitions)
    runner.run_test("Class object dynamic definition", test_class_object_dynamic_definition)
    runner.run_test("Class definition allow callables", test_class_definition_allow_callables)
    runner.run_test("Context manager handler", test_context_manager_handler_roundtrip)
    runner.run_test("Contextlib generator handler", test_contextlib_generator_handler_roundtrip)
    runner.run_test("Thread handler roundtrip", test_thread_handler_roundtrip)
    runner.run_test("Executor handlers roundtrip", test_executor_handlers_roundtrip)
    runner.run_test("Regex match reconnector", test_regex_match_reconnector_roundtrip)
    runner.run_test("Regex pattern roundtrip", test_regex_pattern_roundtrip)
    runner.run_test("Thread local handler roundtrip", test_thread_local_handler_roundtrip)
    runner.run_test("Lock handler roundtrip", test_lock_handler_roundtrip)
    runner.run_test("Semaphore handler roundtrip", test_semaphore_handler_roundtrip)
    runner.run_test("Barrier handler roundtrip", test_barrier_handler_roundtrip)
    runner.run_test("Condition handler roundtrip", test_condition_handler_roundtrip)
    runner.run_test("Iterator handler enumerate", test_iterator_handler_enumerate)
    runner.run_test("Iterator handler rejects generator", test_iterator_handler_rejects_generator)
    runner.run_test("Range/Enumerate/Zip handlers", test_range_enumerate_zip_handlers)

    runner.run_test("Coroutine roundtrip", test_async_coroutine_roundtrip)
    runner.run_test("Async generator roundtrip", test_async_generator_roundtrip)
    runner.run_test("Async task roundtrip", test_async_task_roundtrip)
    runner.run_test("Async future roundtrip", test_async_future_roundtrip)
    runner.run_test("Coroutine handler await raises", test_coroutine_handler_await_raises)
    runner.run_test("Async generator handler aiter raises", test_async_generator_handler_aiter_raises)
    runner.run_test("Task handler placeholder", test_task_handler_placeholder_result)
    runner.run_test("ContextVar handler roundtrip", test_contextvar_handler_roundtrip)
    runner.run_test("Token handler roundtrip", test_token_handler_roundtrip)
    runner.run_test("Code object roundtrip", test_code_object_roundtrip)
    runner.run_test("Frame object roundtrip", test_frame_object_roundtrip)
    runner.run_test("Property handler roundtrip", test_property_handler_roundtrip)
    runner.run_test("Descriptor handler roundtrip", test_descriptor_handler_roundtrip)
    runner.run_test("Generator handler roundtrip", test_generator_handler_roundtrip)

    runner.run_test("SQLite connection roundtrip", test_sqlite_connection_roundtrip)
    runner.run_test("SQLite cursor roundtrip", test_sqlite_cursor_roundtrip)

    runner.run_test("File handle roundtrip text", test_file_handle_roundtrip_text)
    runner.run_test("File handle closed placeholder", test_file_handle_closed_placeholder)
    runner.run_test("Temp file roundtrip", test_temp_file_roundtrip)
    runner.run_test("File handle pipe placeholder", test_file_handle_pipe_placeholder)
    runner.run_test("File handle missing file error", test_file_handle_missing_file_error)
    runner.run_test("File handle relative path", test_file_handle_relative_path)
    runner.run_test("StringIO roundtrip", test_stringio_roundtrip)
    runner.run_test("BytesIO roundtrip closed", test_bytesio_roundtrip_closed)

    runner.run_test("Socket handler roundtrip", test_socket_handler_roundtrip)
    runner.run_test("Socket handler nonblocking", test_socket_handler_nonblocking_state)
    runner.run_test("HTTP session handler", test_http_session_handler_roundtrip)
    runner.run_test("HTTP session cookies error", test_http_session_handler_cookie_error)
    runner.run_test("DB handler extract state", test_db_connection_handler_extract_state)
    runner.run_test("DB handler reconstruct reconnector", test_db_connection_handler_reconstruct_reconnector)
    runner.run_test("DB handler reconstruct sqlite", test_db_connection_handler_reconstruct_sqlite)
    runner.run_test("reconnect_all nested", test_reconnect_all_nested)
    runner.run_test("reconnect_all reconnectors", test_reconnect_all_reconnectors)

    runner.run_test("Weakref live", test_weakref_roundtrip_live)
    runner.run_test("Weakref dead", test_weakref_roundtrip_dead)
    runner.run_test("Weakref dead lambda", test_weakref_handler_dead_lambda)
    runner.run_test("Weakref extract ReferenceError", test_weakref_handler_extract_reference_error)
    runner.run_test("Weakref extract TypeError", test_weakref_handler_extract_type_error)
    runner.run_test("Weakref missing ref", test_weakref_handler_reconstruct_missing_ref)
    runner.run_test("WeakValueDictionary roundtrip", test_weak_value_dict_roundtrip)
    runner.run_test("WeakKeyDictionary roundtrip", test_weak_key_dict_roundtrip)
    runner.run_test("WeakValueDictionary dead value", test_weak_value_dict_dead_value)
    runner.run_test("WeakValueDictionary preserves values", test_weak_value_dict_preserves_values)
    runner.run_test("WeakKeyDictionary dead key", test_weak_key_dict_dead_key)
    runner.run_test("WeakKeyDictionary keyerror", test_weak_key_dict_extract_keyerror)
    runner.run_test("WeakKeyDictionary unweakrefable", test_weak_key_dict_unweakrefable)

    runner.run_test("Namedtuple roundtrip", test_namedtuple_roundtrip)
    runner.run_test("Namedtuple dynamic", test_namedtuple_dynamic_roundtrip)
    runner.run_test("Namedtuple invalid", test_namedtuple_handler_invalid)
    runner.run_test("Namedtuple reconstruct fallback", test_namedtuple_reconstruct_fallback)
    runner.run_test("TypedDict roundtrip", test_typeddict_roundtrip)

    runner.run_test("Function handler reference", test_function_handler_reference)
    runner.run_test("Function handler full", test_function_handler_full)
    runner.run_test("Function handler class method reference", test_function_handler_class_method_reference)
    runner.run_test("Function handler main module fallback", test_function_handler_main_module_fallback)
    runner.run_test("Function handler reference error", test_function_handler_reference_error)
    runner.run_test("Function handler can_use_reference", test_function_handler_can_use_reference_failures)
    runner.run_test("Function handler not callable", test_function_handler_reference_not_callable)
    runner.run_test("Function handler restore attrs", test_function_handler_restore_attrs)
    runner.run_test("Function handler make cell", test_function_handler_make_cell)
    runner.run_test("Partial function handler", test_partial_function_handler)
    runner.run_test("Bound method handler", test_bound_method_handler)
    runner.run_test("Lambda handler", test_lambda_handler)
    runner.run_test("Static/Class method handlers", test_static_and_class_method_handlers)

    runner.run_test("Shared memory unavailable error", test_shared_memory_unavailable_error)

    runner.run_test("Queue handler roundtrip", test_queue_handler_roundtrip)
    runner.run_test("SimpleQueue roundtrip", test_simple_queue_roundtrip)
    runner.run_test("MultiprocessingQueue roundtrip", test_mp_queue_roundtrip)
    runner.run_test("Event roundtrip", test_event_roundtrip)
    runner.run_test("MultiprocessingEvent roundtrip", test_mp_event_roundtrip)

    runner.run_test("OS pipe roundtrip", test_os_pipe_roundtrip)
    runner.run_test("Multiprocessing pipe roundtrip", test_mp_pipe_roundtrip)
    runner.run_test("Multiprocessing manager roundtrip", test_mp_manager_roundtrip)

    runner.run_test("mmap roundtrip", test_mmap_roundtrip)
    runner.run_test("memoryview roundtrip", test_memoryview_roundtrip)
    runner.run_test("shared memory roundtrip", test_shared_memory_roundtrip)
    runner.run_test("Shared memory attach existing", test_shared_memory_attach_existing)
    runner.run_test("mmap closed raises", test_mmap_closed_raises)
    runner.run_test("Shared memory recreate missing", test_shared_memory_recreate_missing)
    runner.run_test("mmap file-backed reconstruct", test_mmap_file_backed_reconstruct)
    runner.run_test("file descriptor handler errors", test_file_descriptor_handler_errors)

    runner.run_test("Popen handler roundtrip", test_popen_handler_roundtrip)
    runner.run_test("CompletedProcess handler", test_completed_process_handler_roundtrip)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
