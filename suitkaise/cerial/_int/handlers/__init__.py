"""
Cerial handlers for serializing complex object types.

Each handler knows how to extract state from a specific object type
and reconstruct it from that state.
"""

from .base_class import Handler

# Logging handlers (90% importance)
from .logging_handler import (
    LoggerHandler,
    StreamHandlerHandler,
    FileHandlerHandler,
    FormatterHandler,
)

# Lock handlers (70% importance + semaphores/barriers/conditions 12%)
from .lock_handler import (
    LockHandler,
    SemaphoreHandler,
    BarrierHandler,
    ConditionHandler,
)

# File handlers (75% + temporary files 5%)
from .file_handler import (
    FileHandleHandler,
    TemporaryFileHandler,
    StringIOHandler,
    BytesIOHandler,
)

# Queue handlers (65% + events 50%)
from .queue_handler import (
    QueueHandler,
    MultiprocessingQueueHandler,
    EventHandler,
    MultiprocessingEventHandler,
)

# Regex handler (40% importance)
from .regex_handler import RegexPatternHandler, MatchObjectHandler, MatchReconnector

# SQLite handlers (30% + cursors 15%)
from .sqlite_handler import (
    SQLiteConnectionHandler,
    SQLiteCursorHandler,
)

# Context variable handlers (2% importance)
from .contextvar_handler import (
    ContextVarHandler,
    TokenHandler,
)

# Network handlers (60% + 15% + 55%)
from .network_handler import (
    HTTPSessionHandler,
    SocketHandler,
    DatabaseConnectionHandler,
    DbReconnector,
    SocketReconnector,
)
from .reconnector import Reconnector

# Iterator handlers (10%)
from .iterator_handler import (
    IteratorHandler,
    RangeHandler,
    EnumerateHandler,
    ZipHandler,
)

# Memory handlers (9% + 3% + 3%)
from .memory_handler import (
    MMapHandler,
    SharedMemoryHandler,
    FileDescriptorHandler,
    MemoryViewHandler,
)

# Threading handlers (8% + 7% + 2%)
from .threading_handler import (
    ThreadHandler,
    ThreadPoolExecutorHandler,
    ProcessPoolExecutorHandler,
    ThreadLocalHandler,
    ThreadReconnector,
)

# Pipe handlers (6% + 4%)
from .pipe_handler import (
    OSPipeHandler,
    MultiprocessingPipeHandler,
    MultiprocessingManagerHandler,
    PipeReconnector,
)

# Advanced handlers (2% each)
from .advanced_py_handler import (
    CodeObjectHandler,
    FrameObjectHandler,
    FrameInfo,
    PropertyHandler,
    DescriptorHandler,
)

# Function handlers
from .function_handler import (
    FunctionHandler,
    LambdaHandler,
    PartialFunctionHandler,
    BoundMethodHandler,
    StaticMethodHandler,
    ClassMethodHandler,
)

# Generator handler
from .generator_handler import GeneratorHandler

# Weakref handlers
from .weakref_handler import (
    WeakrefHandler,
    WeakValueDictionaryHandler,
    WeakKeyDictionaryHandler,
)

# Enum handlers
from .enum_handler import (
    EnumHandler,
    EnumClassHandler,
)

# Context manager handlers
from .context_manager_handler import (
    ContextManagerHandler,
    ContextlibGeneratorHandler,
)

# Subprocess handlers
from .subprocess_handler import (
    PopenHandler,
    CompletedProcessHandler,
    SubprocessReconnector,
)

# Async handlers
from .async_handler import (
    CoroutineHandler,
    AsyncGeneratorHandler,
    TaskHandler,
    FutureHandler,
)

# Module handler
from .module_handler import ModuleHandler

# NamedTuple handlers
from .namedtuple_handler import (
    NamedTupleHandler,
    TypedDictHandler,
)

# Class handlers (all user-defined classes)
from .class_handler import (
    ClassInstanceHandler,
    ClassObjectHandler,
)


__all__ = [
    # Base
    'Handler',
    
    # Logging
    'LoggerHandler',
    'StreamHandlerHandler',
    'FileHandlerHandler',
    'FormatterHandler',
    
    # Locks and synchronization
    'LockHandler',
    'SemaphoreHandler',
    'BarrierHandler',
    'ConditionHandler',
    
    # Files
    'FileHandleHandler',
    'TemporaryFileHandler',
    'StringIOHandler',
    'BytesIOHandler',
    
    # Queues and events
    'QueueHandler',
    'MultiprocessingQueueHandler',
    'EventHandler',
    'MultiprocessingEventHandler',
    
    # Regex
    'RegexPatternHandler',
    'MatchReconnector',
    
    # SQLite
    'SQLiteConnectionHandler',
    'SQLiteCursorHandler',
    
    # Network
    'HTTPSessionHandler',
    'SocketHandler',
    'DatabaseConnectionHandler',
    'DbReconnector',
    'SocketReconnector',
    'Reconnector',
    
    # Iterators
    'IteratorHandler',
    'RangeHandler',
    'EnumerateHandler',
    'ZipHandler',
    
    # Memory
    'MMapHandler',
    'SharedMemoryHandler',
    'FileDescriptorHandler',
    'MemoryViewHandler',
    
    # Threading
    'ThreadHandler',
    'ThreadPoolExecutorHandler',
    'ProcessPoolExecutorHandler',
    'ThreadLocalHandler',
    'ThreadReconnector',
    
    # Pipes
    'OSPipeHandler',
    'MultiprocessingPipeHandler',
    'MultiprocessingManagerHandler',
    'PipeReconnector',
    
    # Advanced
    'CodeObjectHandler',
    'FrameObjectHandler',
    'FrameInfo',
    'PropertyHandler',
    'DescriptorHandler',
    'ContextVarHandler',
    
    # Functions
    'FunctionHandler',
    'LambdaHandler',
    'PartialFunctionHandler',
    'BoundMethodHandler',
    'StaticMethodHandler',
    'ClassMethodHandler',
    
    # Generators
    'GeneratorHandler',
    
    # Weakrefs
    'WeakrefHandler',
    'WeakValueDictionaryHandler',
    'WeakKeyDictionaryHandler',
    
    # Enums
    'EnumHandler',
    'EnumClassHandler',
    
    # Context managers
    'ContextManagerHandler',
    'ContextlibGeneratorHandler',
    
    # Subprocess
    'PopenHandler',
    'CompletedProcessHandler',
    'SubprocessReconnector',
    
    # Async
    'CoroutineHandler',
    'AsyncGeneratorHandler',
    'TaskHandler',
    'FutureHandler',
    
    # Modules
    'ModuleHandler',
    
    # NamedTuple
    'NamedTupleHandler',
    'TypedDictHandler',
    
    # Classes
    'ClassInstanceHandler',
    'ClassObjectHandler',
]


# Registry of all available handlers
# The central serializer will use this to find the right handler for each object
# Ordered by specificity and frequency for performance
ALL_HANDLERS = [
    # Functions - check early since they're common
    FunctionHandler(),
    LambdaHandler(),  # Must come after FunctionHandler checks have_lambda check
    
    # Logging (90%)
    LoggerHandler(),
    StreamHandlerHandler(),
    FileHandlerHandler(),
    FormatterHandler(),
    
    # Partial functions
    PartialFunctionHandler(),
    
    # Bound methods
    BoundMethodHandler(),
    
    # File handles
    FileHandleHandler(),
    TemporaryFileHandler(),
    StringIOHandler(),
    BytesIOHandler(),
    
    # Locks
    LockHandler(),
    
    # Queues
    QueueHandler(),
    MultiprocessingQueueHandler(),
    
    # HTTP Sessions
    HTTPSessionHandler(),
    
    # Events
    EventHandler(),
    MultiprocessingEventHandler(),
    
    # Generators (check before general iterators)
    GeneratorHandler(),
    
    # Regex
    RegexPatternHandler(),
    MatchObjectHandler(),
    
    # SQLite
    SQLiteConnectionHandler(),
    SQLiteCursorHandler(),
    
    # Context variables
    ContextVarHandler(),
    TokenHandler(),
    
    # Socket connections
    SocketHandler(),
    
    # Semaphores/Barriers/Conditions
    SemaphoreHandler(),
    BarrierHandler(),
    ConditionHandler(),
    
    # Weakrefs
    WeakrefHandler(),
    WeakValueDictionaryHandler(),
    WeakKeyDictionaryHandler(),
    
    # Iterators
    IteratorHandler(),
    RangeHandler(),
    EnumerateHandler(),
    ZipHandler(),
    
    # Memory-mapped files
    MMapHandler(),
    
    # Thread objects
    ThreadHandler(),
    
    # Executors
    ThreadPoolExecutorHandler(),
    ProcessPoolExecutorHandler(),
    
    # Pipes
    OSPipeHandler(),
    MultiprocessingPipeHandler(),
    
    # Manager/proxy objects
    MultiprocessingManagerHandler(),
    
    # Shared memory
    SharedMemoryHandler(),
    MemoryViewHandler(),
    
    # File descriptors
    FileDescriptorHandler(),
    
    # Advanced objects
    CodeObjectHandler(),
    FrameObjectHandler(),
    PropertyHandler(),
    DescriptorHandler(),
    ThreadLocalHandler(),
    StaticMethodHandler(),
    ClassMethodHandler(),
    
    # Enums (check before general class handlers)
    EnumHandler(),
    EnumClassHandler(),
    
    # NamedTuples (check before general class/tuple handlers)
    NamedTupleHandler(),
    TypedDictHandler(),
    
    # Context managers (check before general class handlers)
    ContextManagerHandler(),
    ContextlibGeneratorHandler(),
    
    # Subprocess objects
    PopenHandler(),
    CompletedProcessHandler(),
    
    # Async objects
    CoroutineHandler(),
    AsyncGeneratorHandler(),
    TaskHandler(),
    FutureHandler(),
    
    # Modules
    ModuleHandler(),
    
    # Database connections (generic, after specific handlers)
    DatabaseConnectionHandler(),
    
    # Class objects (classes themselves)
    ClassObjectHandler(),
    
    # Class instances (LAST - catch-all for user-defined classes)
    # This must be last so specialized handlers get first chance
    # Now supports __slots__, __dict__, custom serialize, and to_dict patterns
    ClassInstanceHandler(),
]

