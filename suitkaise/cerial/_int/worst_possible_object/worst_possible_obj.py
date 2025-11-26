# there will be 3 levels of nested classes.

# each level will have all cerial-supported objects (primitives and complex objects that handlers can handle) as attributes
# outside of collections

# each level will also generate a random nested collection for every collection type
# - random depth
# - adds random objects (primitives and complex objects) to the collection at each level
# - if the depth is != to random depth generated, adds a random collection to the current level and repeats process

# this randomness from each WorstPossibleObject instance shows that cerial can actually handle everything.

import random
import threading
import logging
import queue
import re
import sqlite3
import tempfile
import io
import mmap
import weakref
import contextvars
import subprocess
import socket
import sys
import uuid
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from fractions import Fraction
from collections import defaultdict, OrderedDict, Counter, deque, ChainMap
from functools import partial
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

# - tuple
# - list
# - set
# - frozenset
# - dict
# - range objects
# - slice objects

COLLECTION_TYPES = [tuple, list, set, frozenset, dict, range, slice]

BASE_PICKLE_SUPPORTED_TYPES = [None, True, False, int, float, complex, str, bytes, bytearray, type, Ellipsis, NotImplemented]

# From concept.md - all complex types cerial handlers can handle
COMPLEX_TYPES_THAT_CERIAL_CAN_HANDLE = [
    'function',
    'logger', 
    'partial_function',
    'bound_method',
    'file_handle',
    'lock',
    'rlock',
    'queue',
    'lifo_queue',
    'priority_queue',
    'event',
    'semaphore',
    'bounded_semaphore',
    'condition',
    'barrier',
    'sqlite_connection',
    'sqlite_cursor',
    'generator',
    'regex_pattern',
    'weak_reference',
    'memory_mapped_file',
    'thread_local',
    'context_var',
    'iterator',
    'string_io',
    'bytes_io',
]

# sktime
# skpath
from suitkaise.skpath import *
from suitkaise.sktime import *

# dont worry about these for now.
SUITKAISE_SPECIFIC_TYPES = [
    # skpath
    SKPath, AnyPath, ForceRoot,
    # do i need to import functions to test if they are serializable? 
    # or are they handled by cerial function handler

    # sktime
    Yawn, Timer, TimeThis
    # same thing: do i need to test the functions and/or decorators?
]  # add them here as modules are completed

class WorstPossibleObject:

    def __init__(self, verbose=False, debug_log_file=None, skip_types=None):
        """
        Initialize the worst possible object.
        
        Args:
            verbose: If True, print detailed initialization progress
            debug_log_file: Optional file path to write debug logs
            skip_types: Optional set of type categories to skip for isolated testing
                       e.g., {'functions', 'locks', 'queues'}
        """
        self.verbose = verbose
        self.debug_log_file = debug_log_file
        self.skip_types = skip_types or set()
        
        # Store verification data before any modifications
        self._verification_checksums = {}
        
        # Track what was actually initialized
        self._initialized_types = {
            'primitives': [],
            'complex': [],
            'collections': [],
            'edge_cases': [],
            'circular_refs': []
        }
        
        # Setup debug logging
        if debug_log_file:
            self._debug_file = open(debug_log_file, 'w')
        else:
            self._debug_file = None
        
        self._log("=" * 70)
        self._log("INITIALIZING WORST POSSIBLE OBJECT")
        self._log("=" * 70 + "\n")
        
        self.init_all_base_pickle_supported_objects()
        self.init_all_complex_types_in_random_order()
        self.init_edge_cases_and_extreme_states()

        copy = COLLECTION_TYPES.copy()
        random.shuffle(copy)

        for collection_type in copy:
            self.generate_random_nested_collection(collection_type)
        
        # Add circular references and cross-references AFTER everything is initialized
        self.create_circular_references()
        
        # Compute verification checksums
        self.compute_verification_data()
        
        self._log("\nINITIALIZATION COMPLETE")
        self._log(f"Total verification checksums: {len(self._verification_checksums)}")
        self._log("="*70 + "\n")
    
    def _log(self, message):
        """Log a debug message."""
        if self.verbose:
            print(message)
        if self._debug_file:
            self._debug_file.write(message + "\n")
            self._debug_file.flush()
    
    def _track_init(self, category, name, obj=None):
        """Track that an object was initialized."""
        self._initialized_types[category].append(name)
        self._log(f"  ✓ {name}: {type(obj).__name__ if obj else 'initialized'}")


    def init_all_base_pickle_supported_objects(self):
        """Initialize all objects that base pickle can handle natively."""
        if 'primitives' in self.skip_types:
            self._log("\n[SKIPPED] Base pickle primitives")
            return
        
        self._log("\n[INIT] Base pickle primitives")
        
        self.none_value = None
        self._track_init('primitives', 'none_value', self.none_value)
        
        self.bool_true = True
        self.bool_false = False
        self._track_init('primitives', 'bool_true/false', self.bool_true)
        
        # random ints between -2147483648 and 2147483647
        self.int_value = random.randint(-2147483648, 2147483647)
        # random very large ints between -10^30 and 10^30
        self.large_int = random.randint(-10**30, 10**30)
        self._track_init('primitives', 'int_value/large', self.int_value)
        
        self.float_value = random.uniform(-10**30, 10**30)
        self._track_init('primitives', 'float_value', self.float_value)
        
        self.complex_value = complex(2, 3)
        self.complex_negative = complex(-1, -1)
        self._track_init('primitives', 'complex_value/negative', self.complex_value)
        
        self.str_value = "test string"
        self.str_unicode = "unicode: 你好世界 🌍"
        self.str_empty = ""
        self._track_init('primitives', 'str_value/unicode/empty', self.str_value)
        
        self.bytes_value = b"raw bytes data"
        self.bytes_empty = b""
        self._track_init('primitives', 'bytes_value/empty', self.bytes_value)
        
        self.bytearray_value = bytearray(b"mutable bytes")
        self._track_init('primitives', 'bytearray_value', self.bytearray_value)
        
        self.type_int = int
        self.type_str = str
        self.type_list = list
        self._track_init('primitives', 'type_int/str/list', self.type_int)
        
        self.ellipsis_value = Ellipsis
        self._track_init('primitives', 'ellipsis_value', self.ellipsis_value)
        
        self.notimplemented_value = NotImplemented
        self._track_init('primitives', 'notimplemented_value', self.notimplemented_value)
        
        self.range_value = range(10)
        self.range_step = range(0, 100, 5)
        self._track_init('primitives', 'range_value/step', self.range_value)
        
        self.slice_value = slice(10)
        self.slice_full = slice(10, 50, 2)
        self._track_init('primitives', 'slice_value/full', self.slice_value)
        
        # Additional pickle-native types (datetime, Decimal, etc.)
        self._log("\n[INIT] Additional pickle-native types")
        
        self.datetime_value = datetime(2023, 5, 15, 10, 30, 45)
        self.datetime_now = datetime.now()
        self._track_init('primitives', 'datetime_value/now', self.datetime_value)
        
        self.date_value = date(2023, 5, 15)
        self.date_today = date.today()
        self._track_init('primitives', 'date_value/today', self.date_value)
        
        self.time_value = time(10, 30, 45)
        self.time_with_micro = time(10, 30, 45, 123456)
        self._track_init('primitives', 'time_value/micro', self.time_value)
        
        self.timedelta_value = timedelta(days=5, hours=3, minutes=30)
        self.timedelta_negative = timedelta(days=-10)
        self._track_init('primitives', 'timedelta_value/negative', self.timedelta_value)
        
        self.decimal_value = Decimal('123.456')
        self.decimal_precision = Decimal('1.123456789012345678901234567890')
        self._track_init('primitives', 'decimal_value/precision', self.decimal_value)
        
        self.fraction_value = Fraction(3, 4)
        self.fraction_from_float = Fraction(0.5)
        self._track_init('primitives', 'fraction_value/from_float', self.fraction_value)
        
        self.uuid_value = uuid.uuid4()
        self.uuid_fixed = uuid.UUID('12345678-1234-5678-1234-567812345678')
        self._track_init('primitives', 'uuid_value/fixed', self.uuid_value)
        
        # Collections with primitives
        self._log("\n[INIT] Base collections")
        
        self.tuple_value = (1, 2, 3)
        self.tuple_mixed = (1, "two", 3.0, None)
        self.tuple_empty = ()
        self._track_init('collections', 'tuple_value/mixed/empty', self.tuple_value)
        
        self.list_value = [1, 2, 3, 4, 5]
        self.list_mixed = [1, "two", 3.0, None, True]
        self.list_empty = []
        self._track_init('collections', 'list_value/mixed/empty', self.list_value)
        
        self.set_value = {1, 2, 3, 4, 5}
        self.set_strings = {"a", "b", "c"}
        self.set_empty = set()
        self._track_init('collections', 'set_value/strings/empty', self.set_value)
        
        self.frozenset_value = frozenset([1, 2, 3, 4])
        self.frozenset_empty = frozenset()
        self._track_init('collections', 'frozenset_value/empty', self.frozenset_value)
        
        self.dict_value = {"key1": "value1", "key2": "value2"}
        self.dict_mixed = {1: "int key", "str": 2, (1, 2): "tuple key"}
        self.dict_empty = {}
        self._track_init('collections', 'dict_value/mixed/empty', self.dict_value)
        
        # Advanced collections (pickle-native)
        self._log("\n[INIT] Advanced collections (collections module)")
        
        self.defaultdict_value = defaultdict(list)
        self.defaultdict_value['key1'].append(1)
        self.defaultdict_value['key1'].append(2)
        self.defaultdict_value['key2'].append(3)
        self._track_init('collections', 'defaultdict_value (list factory)', self.defaultdict_value)
        
        self.defaultdict_int = defaultdict(int)
        self.defaultdict_int['count'] += 5
        self._track_init('collections', 'defaultdict_int (int factory)', self.defaultdict_int)
        
        self.ordereddict_value = OrderedDict([('first', 1), ('second', 2), ('third', 3)])
        self._track_init('collections', 'ordereddict_value', self.ordereddict_value)
        
        self.counter_value = Counter(['apple', 'banana', 'apple', 'orange', 'apple', 'banana'])
        self._track_init('collections', 'counter_value', self.counter_value)
        
        self.counter_from_dict = Counter({'red': 4, 'blue': 2})
        self._track_init('collections', 'counter_from_dict', self.counter_from_dict)
        
        self.deque_value = deque([1, 2, 3, 4, 5], maxlen=10)
        self.deque_value.append(6)
        self.deque_value.appendleft(0)
        self._track_init('collections', 'deque_value (maxlen=10)', self.deque_value)
        
        self.deque_unlimited = deque(['a', 'b', 'c'])
        self._track_init('collections', 'deque_unlimited', self.deque_unlimited)
        
        dict1 = {'one': 1, 'two': 2}
        dict2 = {'three': 3, 'four': 4}
        dict3 = {'five': 5}
        self.chainmap_value = ChainMap(dict1, dict2, dict3)
        self._track_init('collections', 'chainmap_value (3 dicts)', self.chainmap_value)
        
        # pathlib.Path objects (pickle-native)
        self._log("\n[INIT] pathlib.Path objects")
        
        self.path_current = Path('.')
        self.path_home = Path.home()
        self.path_absolute = Path(__file__).absolute()
        self.path_parent = Path(__file__).parent
        self._track_init('primitives', 'path objects (current/home/absolute/parent)', self.path_current)

    def init_all_complex_types_in_random_order(self):
        """Initialize all complex, unpickleable objects that cerial handlers must handle."""
        
        # Create list of all complex types to initialize
        complex_init_funcs = [
            self._init_functions,
            self._init_loggers,
            self._init_locks,
            self._init_queues,
            self._init_events,
            self._init_file_handles,
            self._init_regex,
            self._init_sqlite,
            self._init_generators,
            self._init_weak_references,
            self._init_memory_mapped_files,
            self._init_context_vars,
            self._init_iterators,
        ]
        
        # Shuffle for random order initialization
        random.shuffle(complex_init_funcs)
        
        # Initialize all in random order
        for init_func in complex_init_funcs:
            init_func()
    
    def _init_functions(self):
        """Initialize function-related objects."""
        if 'functions' in self.skip_types:
            self._log("  [SKIPPED] Functions")
            return
        
        self._log("  [INIT] Functions")
        
        def test_function(x, y=10):
            """A test function with defaults."""
            return x + y
        
        def test_function_no_defaults(a, b):
            """Function without defaults."""
            return a * b
        
        self.function = test_function
        self._track_init('complex', 'function', self.function)
        
        self.function_no_defaults = test_function_no_defaults
        self._track_init('complex', 'function_no_defaults', self.function_no_defaults)
        
        self.lambda_function = lambda x: x * 2
        self._track_init('complex', 'lambda_function', self.lambda_function)
        
        self.partial_function = partial(test_function, 5)
        self._track_init('complex', 'partial_function', self.partial_function)
        
        self.partial_with_kwargs = partial(test_function, y=20)
        self._track_init('complex', 'partial_with_kwargs', self.partial_with_kwargs)
        
        self.bound_method = self.list_value.append
        self._track_init('complex', 'bound_method', self.bound_method)
    
    def _init_loggers(self):
        """Initialize logging objects."""
        if 'loggers' in self.skip_types:
            self._log("  [SKIPPED] Loggers")
            return
        
        self._log("  [INIT] Loggers")
        
        self.logger = logging.getLogger(f"test_logger_{id(self)}")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self._track_init('complex', 'logger', self.logger)
        
        self.logger_warning = logging.getLogger(f"warning_logger_{id(self)}")
        self.logger_warning.setLevel(logging.WARNING)
        self._track_init('complex', 'logger_warning', self.logger_warning)
    
    def _init_locks(self):
        """Initialize threading lock objects."""
        if 'locks' in self.skip_types:
            self._log("  [SKIPPED] Locks")
            return
        
        self._log("  [INIT] Locks")
        
        self.lock = threading.Lock()
        self._track_init('complex', 'lock', self.lock)
        
        self.lock_acquired = threading.Lock()
        self.lock_acquired.acquire()  # Test locked state
        self._track_init('complex', 'lock_acquired (locked)', self.lock_acquired)
        
        self.rlock = threading.RLock()
        self._track_init('complex', 'rlock', self.rlock)
        
        self.rlock_acquired = threading.RLock()
        self.rlock_acquired.acquire()
        self._track_init('complex', 'rlock_acquired', self.rlock_acquired)
        
        self.condition = threading.Condition()
        self._track_init('complex', 'condition', self.condition)
        
        self.barrier = threading.Barrier(3)
        self._track_init('complex', 'barrier', self.barrier)
        
        self.thread_local = threading.local()
        self.thread_local.value = "thread local data"
        self.thread_local.number = 42
        self._track_init('complex', 'thread_local', self.thread_local)
    
    def _init_queues(self):
        """Initialize queue objects."""
        if 'queues' in self.skip_types:
            self._log("  [SKIPPED] Queues")
            return
        
        self._log("  [INIT] Queues")
        
        self.queue = queue.Queue(maxsize=10)
        self.queue.put("item1")
        self.queue.put("item2")
        self.queue.put(42)
        self._track_init('complex', 'queue (size=3)', self.queue)
        
        self.queue_empty = queue.Queue()
        self._track_init('complex', 'queue_empty', self.queue_empty)
        
        self.lifo_queue = queue.LifoQueue(maxsize=5)
        self.lifo_queue.put("first")
        self.lifo_queue.put("second")
        self._track_init('complex', 'lifo_queue (size=2)', self.lifo_queue)
        
        self.priority_queue = queue.PriorityQueue()
        self.priority_queue.put((1, "high priority"))
        self.priority_queue.put((10, "low priority"))
        self._track_init('complex', 'priority_queue (size=2)', self.priority_queue)
    
    def _init_events(self):
        """Initialize event objects."""
        if 'events' in self.skip_types:
            self._log("  [SKIPPED] Events")
            return
        
        self._log("  [INIT] Events")
        
        self.event = threading.Event()
        self._track_init('complex', 'event (unset)', self.event)
        
        self.event_set = threading.Event()
        self.event_set.set()  # Test set state
        self._track_init('complex', 'event_set (set)', self.event_set)
        
        self.semaphore = threading.Semaphore(5)
        self.semaphore.acquire()
        self.semaphore.acquire()
        self._track_init('complex', 'semaphore (value=3)', self.semaphore)
        
        self.bounded_semaphore = threading.BoundedSemaphore(3)
        self.bounded_semaphore.acquire()
        self._track_init('complex', 'bounded_semaphore (value=2)', self.bounded_semaphore)
    
    def _init_file_handles(self):
        """Initialize file handle objects."""
        if 'files' in self.skip_types:
            self._log("  [SKIPPED] File handles")
            return
        
        self._log("  [INIT] File handles")
        
        self.temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
        self.temp_file.write("temporary file content line 1\n")
        self.temp_file.write("temporary file content line 2\n")
        self.temp_file.flush()
        self.temp_file.seek(0)
        self._track_init('complex', f'temp_file ({self.temp_file.name})', self.temp_file)
        
        self.temp_file_binary = tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.bin')
        self.temp_file_binary.write(b"binary content")
        self.temp_file_binary.flush()
        self._track_init('complex', 'temp_file_binary', self.temp_file_binary)
        
        self.string_io = io.StringIO("StringIO content here")
        self._track_init('complex', 'string_io', self.string_io)
        
        self.bytes_io = io.BytesIO(b"BytesIO binary content")
        self._track_init('complex', 'bytes_io', self.bytes_io)
    
    def _init_regex(self):
        """Initialize regex pattern objects."""
        if 'regex' in self.skip_types:
            self._log("  [SKIPPED] Regex")
            return
        
        self._log("  [INIT] Regex")
        
        self.regex_pattern = re.compile(r'\d+\.\d+', re.IGNORECASE | re.MULTILINE)
        self._track_init('complex', 'regex_pattern', self.regex_pattern)
        
        self.regex_simple = re.compile(r'\w+')
        self._track_init('complex', 'regex_simple', self.regex_simple)
        
        self.regex_complex = re.compile(
            r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})',
            re.VERBOSE
        )
        self._track_init('complex', 'regex_complex (with groups)', self.regex_complex)
        
        self.regex_match = self.regex_pattern.search("version 3.14 found")
        self._track_init('complex', 'regex_match', self.regex_match)
    
    def _init_sqlite(self):
        """Initialize SQLite database objects."""
        if 'sqlite' in self.skip_types:
            self._log("  [SKIPPED] SQLite")
            return
        
        self._log("  [INIT] SQLite")
        
        self.sqlite_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.sqlite_conn = sqlite3.connect(self.sqlite_file.name)
        self._track_init('complex', 'sqlite_conn', self.sqlite_conn)
        
        self.sqlite_cursor = self.sqlite_conn.cursor()
        self._track_init('complex', 'sqlite_cursor', self.sqlite_cursor)
        
        self.sqlite_cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT, value REAL)")
        self.sqlite_cursor.execute("INSERT INTO test VALUES (1, 'row1', 1.5)")
        self.sqlite_cursor.execute("INSERT INTO test VALUES (2, 'row2', 2.5)")
        self.sqlite_conn.commit()
        self._log(f"    - Created table 'test' with 2 rows")
    
    def _init_generators(self):
        """Initialize generator objects with state."""
        if 'generators' in self.skip_types:
            self._log("  [SKIPPED] Generators")
            return
        
        self._log("  [INIT] Generators")
        
        def test_generator():
            for i in range(10):
                yield i * 2
        
        def test_generator_complex():
            for i in range(5):
                yield {"index": i, "value": i ** 2}
        
        self.generator = test_generator()
        next(self.generator)  # Advance to test state
        next(self.generator)
        self._track_init('complex', 'generator (advanced 2 steps)', self.generator)
        
        self.generator_fresh = test_generator()
        self._track_init('complex', 'generator_fresh', self.generator_fresh)
        
        self.generator_complex = test_generator_complex()
        next(self.generator_complex)
        self._track_init('complex', 'generator_complex (advanced 1)', self.generator_complex)
    
    def _init_weak_references(self):
        """Initialize weak reference objects."""
        if 'weakrefs' in self.skip_types:
            self._log("  [SKIPPED] Weak references")
            return
        
        self._log("  [INIT] Weak references")
        
        class WeakRefTarget:
            def __init__(self, name):
                self.name = name
                self.data = [1, 2, 3]
        
        self.weakref_target = WeakRefTarget("target")
        self.weak_reference = weakref.ref(self.weakref_target)
        self._track_init('complex', 'weak_reference', self.weak_reference)
        
        self.weakref_target2 = WeakRefTarget("target2")
        self.weak_reference2 = weakref.ref(self.weakref_target2)
        self._track_init('complex', 'weak_reference2', self.weak_reference2)
    
    def _init_memory_mapped_files(self):
        """Initialize memory-mapped file objects."""
        if 'mmap' in self.skip_types:
            self._log("  [SKIPPED] Memory-mapped files")
            return
        
        self._log("  [INIT] Memory-mapped files")
        
        self.mmap_file = tempfile.NamedTemporaryFile(delete=False)
        self.mmap_file.write(b"0" * 1000)
        self.mmap_file.flush()
        self.mmap = mmap.mmap(self.mmap_file.fileno(), 1000)
        self.mmap[0:10] = b"TEST_DATA_"
        self._track_init('complex', 'mmap (1000 bytes)', self.mmap)
    
    def _init_context_vars(self):
        """Initialize context variable objects."""
        if 'contextvars' in self.skip_types:
            self._log("  [SKIPPED] Context variables")
            return
        
        self._log("  [INIT] Context variables")
        
        self.context_var = contextvars.ContextVar('test_var', default='default_value')
        self.context_var.set('custom_value')
        self._track_init('complex', 'context_var', self.context_var)
        
        self.context_var_int = contextvars.ContextVar('int_var', default=0)
        self.context_var_int.set(42)
        self._track_init('complex', 'context_var_int', self.context_var_int)
    
    def _init_iterators(self):
        """Initialize iterator objects with state."""
        if 'iterators' in self.skip_types:
            self._log("  [SKIPPED] Iterators")
            return
        
        self._log("  [INIT] Iterators")
        
        self.iterator = iter([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        next(self.iterator)  # Advance state
        next(self.iterator)
        self._track_init('complex', 'iterator (advanced 2)', self.iterator)
        
        self.iterator_fresh = iter(["a", "b", "c", "d"])
        self._track_init('complex', 'iterator_fresh', self.iterator_fresh)
        
        self.iterator_dict = iter({"key1": "val1", "key2": "val2"}.items())
        next(self.iterator_dict)
        self._track_init('complex', 'iterator_dict (advanced 1)', self.iterator_dict)

    def generate_random_nested_collection(self, collection_type):
        """Generate a random nested collection of primitives, collections, and complex objects."""
        max_depth = random.randint(2, 5)
        
        # Get all available objects for random selection
        all_primitives = [
            self.none_value, self.bool_true, self.bool_false,
            self.int_value, self.float_value, self.str_value,
            self.bytes_value
        ]
        
        all_complex = [
            self.lock, self.event, self.logger, self.queue,
            self.regex_pattern, self.function, self.partial_function,
            self.string_io, self.weak_reference
        ]
        
        # Generate and store the collection
        result = self._generate_nested(collection_type, max_depth, 0, all_primitives, all_complex)
        
        # Store with a descriptive attribute name
        if collection_type == tuple:
            setattr(self, f'random_tuple_{id(result)}', result)
        elif collection_type == list:
            setattr(self, f'random_list_{id(result)}', result)
        elif collection_type == set:
            setattr(self, f'random_set_{id(result)}', result)
        elif collection_type == frozenset:
            setattr(self, f'random_frozenset_{id(result)}', result)
        elif collection_type == dict:
            setattr(self, f'random_dict_{id(result)}', result)
        elif collection_type == range:
            # range objects are immutable and predefined
            setattr(self, f'random_range_{id(result)}', range(random.randint(5, 20)))
        elif collection_type == slice:
            # slice objects are immutable and predefined
            setattr(self, f'random_slice_{id(result)}', slice(random.randint(0, 5), random.randint(10, 20)))
        
        return result
    
    def _generate_nested(self, coll_type, max_depth, current_depth, primitives, complex_objs):
        """Recursively generate nested collection structure."""
        # Base case: reached max depth, return random primitive
        if current_depth >= max_depth:
            return random.choice(primitives)
        
        # Build nested collection
        if coll_type == tuple:
            items = []
            for _ in range(random.randint(2, 4)):
                if random.random() < 0.3:  # 30% chance of nesting another collection
                    next_type = random.choice([list, tuple, dict])
                    items.append(self._generate_nested(next_type, max_depth, current_depth + 1, primitives, complex_objs))
                elif random.random() < 0.6:  # 60% primitives
                    items.append(random.choice(primitives))
                else:  # 10% complex objects
                    items.append(random.choice(complex_objs))
            return tuple(items)
        
        elif coll_type == list:
            items = []
            for _ in range(random.randint(2, 4)):
                if random.random() < 0.3:
                    next_type = random.choice([list, tuple, dict])
                    items.append(self._generate_nested(next_type, max_depth, current_depth + 1, primitives, complex_objs))
                elif random.random() < 0.6:
                    items.append(random.choice(primitives))
                else:
                    items.append(random.choice(complex_objs))
            return items
        
        elif coll_type == dict:
            items = {}
            for i in range(random.randint(2, 4)):
                key = f"key_{current_depth}_{i}"
                if random.random() < 0.3:
                    next_type = random.choice([list, tuple, dict])
                    items[key] = self._generate_nested(next_type, max_depth, current_depth + 1, primitives, complex_objs)
                elif random.random() < 0.6:
                    items[key] = random.choice(primitives)
                else:
                    items[key] = random.choice(complex_objs)
            return items
        
        elif coll_type == set:
            # Sets can only contain hashable items
            hashable_primitives = [p for p in primitives if isinstance(p, (type(None), bool, int, float, str, bytes))]
            return set(random.sample(hashable_primitives, min(3, len(hashable_primitives))))
        
        elif coll_type == frozenset:
            hashable_primitives = [p for p in primitives if isinstance(p, (type(None), bool, int, float, str, bytes))]
            return frozenset(random.sample(hashable_primitives, min(3, len(hashable_primitives))))
        
        else:
            # Fallback for range, slice, etc.
            return random.choice(primitives)
    
    def init_edge_cases_and_extreme_states(self):
        """Initialize extreme edge cases and worst-case scenarios."""
        if 'edge_cases' in self.skip_types:
            self._log("\n[SKIPPED] Edge cases and extreme states")
            return
        
        self._log("\n[INIT] Edge cases and extreme states")
        
        # Custom serialization classes
        class CustomSerializeClass:
            """Class with custom __serialize__ / __deserialize__ methods."""
            def __init__(self, data):
                self.data = data
                self.internal_state = {"key": "value"}
            
            def __serialize__(self):
                return {"data": self.data, "internal_state": self.internal_state}
            
            @classmethod
            def __deserialize__(cls, state):
                obj = cls.__new__(cls)
                obj.data = state["data"]
                obj.internal_state = state["internal_state"]
                return obj
        
        self.custom_serialize_obj = CustomSerializeClass("test data")
        self._track_init('edge_cases', 'custom_serialize_obj', self.custom_serialize_obj)
        
        # to_dict/from_dict pattern
        class ToDictClass:
            """Class with to_dict/from_dict pattern."""
            def __init__(self, x, y):
                self.x = x
                self.y = y
            
            def to_dict(self):
                return {"x": self.x, "y": self.y}
            
            @classmethod
            def from_dict(cls, data):
                return cls(**data)
        
        self.to_dict_obj = ToDictClass(10, 20)
        
        # Nested class defined inside __init__ (dynamic class)
        class DynamicNestedClass:
            def __init__(self, value):
                self.value = value
                self.nested_data = [1, 2, 3]
        
        self.dynamic_class_instance = DynamicNestedClass(42)
        
        # Full queue (at maxsize)
        self.queue_full = queue.Queue(maxsize=3)
        self.queue_full.put(1)
        self.queue_full.put(2)
        self.queue_full.put(3)
        # Now full - can't add more without blocking
        
        # Deeply acquired RLock (reentrant lock acquired multiple times)
        self.rlock_deep = threading.RLock()
        for _ in range(5):
            self.rlock_deep.acquire()
        
        # Multiple items in various queues
        self.priority_queue_full = queue.PriorityQueue(maxsize=5)
        for i in range(5):
            self.priority_queue_full.put((i, f"item_{i}"))
        
        # Iterator at different positions
        self.iterator_exhausted = iter([1, 2, 3])
        for _ in [1, 2, 3]:
            try:
                next(self.iterator_exhausted)
            except StopIteration:
                pass
        
        # Generator in middle of execution
        def complex_generator():
            for i in range(100):
                yield {"index": i, "data": [i] * i}
        
        self.generator_advanced = complex_generator()
        for _ in range(50):  # Advance halfway
            next(self.generator_advanced)
        
        # Regex with captured groups
        self.regex_with_groups = re.compile(
            r'(?P<protocol>https?)://(?P<domain>[^/]+)(?P<path>/.*)?'
        )
        self.regex_match_with_groups = self.regex_with_groups.match(
            'https://example.com/path/to/resource'
        )
        
        # File at specific position (not at start)
        self.temp_file_mid_position = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        self.temp_file_mid_position.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
        self.temp_file_mid_position.flush()
        self.temp_file_mid_position.seek(14)  # Middle of file
        
        # StringIO with position
        self.string_io_positioned = io.StringIO("0123456789" * 10)
        self.string_io_positioned.seek(50)
        
        # Multiple loggers with different configurations
        self.logger_with_multiple_handlers = logging.getLogger(f"complex_logger_{id(self)}")
        self.logger_with_multiple_handlers.setLevel(logging.INFO)
        
        handler1 = logging.StreamHandler()
        handler1.setLevel(logging.WARNING)
        handler1.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        handler2 = logging.StreamHandler()
        handler2.setLevel(logging.ERROR)
        handler2.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        
        self.logger_with_multiple_handlers.addHandler(handler1)
        self.logger_with_multiple_handlers.addHandler(handler2)
        
        # SQLite with more complex schema
        self.sqlite_file_complex = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.sqlite_conn_complex = sqlite3.connect(self.sqlite_file_complex.name)
        self.sqlite_cursor_complex = self.sqlite_conn_complex.cursor()
        self.sqlite_cursor_complex.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                age INTEGER
            )
        ''')
        self.sqlite_cursor_complex.execute('''
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                content TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        self.sqlite_cursor_complex.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com', 30)")
        self.sqlite_cursor_complex.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@example.com', 25)")
        self.sqlite_cursor_complex.execute("INSERT INTO posts VALUES (1, 1, 'Post by Alice')")
        self.sqlite_cursor_complex.execute("INSERT INTO posts VALUES (2, 1, 'Another post by Alice')")
        self.sqlite_cursor_complex.execute("INSERT INTO posts VALUES (3, 2, 'Post by Bob')")
        self.sqlite_conn_complex.commit()
        
        # Weak reference to object that also exists strongly
        class ComplexWeakRefTarget:
            def __init__(self):
                self.data = {"nested": [1, 2, 3], "value": 42}
                self.lock = threading.Lock()
        
        self.complex_weakref_target = ComplexWeakRefTarget()
        self.complex_weak_reference = weakref.ref(self.complex_weakref_target)
        
        # Lambda with closure
        captured_value = 100
        self.lambda_with_closure = lambda x: x + captured_value
        
        # Partial with multiple arguments bound
        def multi_arg_function(a, b, c, d=10, e=20):
            return a + b + c + d + e
        
        self.partial_complex = partial(multi_arg_function, 1, 2, d=30)
        
        # Context var with token
        self.context_var_with_token = contextvars.ContextVar('token_var')
        self.context_token = self.context_var_with_token.set('token_value')
    
    def create_circular_references(self):
        """Create circular references and cross-references between objects."""
        if 'circular' in self.skip_types:
            self._log("\n[SKIPPED] Circular references")
            return
        
        self._log("\n[INIT] Circular references")
        
        # Self-referencing dict
        self.circular_dict = {"name": "circular", "data": [1, 2, 3]}
        self.circular_dict["self"] = self.circular_dict
        self.circular_dict["also_self"] = self.circular_dict
        
        # Self-referencing list
        self.circular_list = [1, 2, 3, "placeholder"]
        self.circular_list[3] = self.circular_list
        
        # Two objects referencing each other
        self.ref_a = {"name": "A", "data": [1, 2, 3]}
        self.ref_b = {"name": "B", "data": [4, 5, 6]}
        self.ref_a["points_to_b"] = self.ref_b
        self.ref_b["points_to_a"] = self.ref_a
        
        # Complex circular structure with multiple objects
        self.circular_complex = {
            "level": 0,
            "objects": [self.lock, self.logger, self.queue],
            "nested": {
                "data": "test",
                "back_ref": None
            }
        }
        self.circular_complex["nested"]["back_ref"] = self.circular_complex
        
        # List with circular reference at multiple levels
        self.circular_nested = [
            {"a": 1},
            [2, 3, None],
            {"b": None}
        ]
        self.circular_nested[1][2] = self.circular_nested
        self.circular_nested[2]["b"] = self.circular_nested[0]
        self.circular_nested[0]["ref"] = self.circular_nested[1]
    
    def compute_verification_data(self):
        """Compute checksums and verification data for all fields."""
        self._verification_checksums = {
            # Primitives
            'int_value': self.int_value,
            'large_int': self.large_int,
            'float_value': self.float_value,
            'str_value': self.str_value,
            'str_unicode': self.str_unicode,
            'bytes_value': self.bytes_value,
            'complex_value': self.complex_value,
            
            # Pickle-native types (datetime, Decimal, etc.)
            'datetime_value': self.datetime_value,
            'date_value': self.date_value,
            'time_value': self.time_value,
            'timedelta_value': self.timedelta_value,
            'decimal_value': self.decimal_value,
            'fraction_value': self.fraction_value,
            'uuid_value': self.uuid_value,
            'uuid_fixed': self.uuid_fixed,
            
            # Collections
            'tuple_value': self.tuple_value,
            'list_value': self.list_value,
            'set_value': self.set_value,
            'frozenset_value': self.frozenset_value,
            'dict_value': self.dict_value,
            'range_value': tuple(self.range_value),  # Convert to comparable
            'slice_value': (self.slice_value.start, self.slice_value.stop, self.slice_value.step),
            
            # Advanced collections
            'defaultdict_value_keys': sorted(self.defaultdict_value.keys()),
            'defaultdict_int_count': self.defaultdict_int['count'],
            'ordereddict_value_keys': list(self.ordereddict_value.keys()),
            'counter_value_most_common': self.counter_value.most_common(1)[0] if self.counter_value else None,
            'deque_value_len': len(self.deque_value),
            'deque_value_maxlen': self.deque_value.maxlen,
            'chainmap_value_keys': sorted(self.chainmap_value.keys()),
            
            # pathlib.Path
            'path_current_str': str(self.path_current),
            'path_absolute_name': self.path_absolute.name,
            
            # Threading states
            'lock_acquired_locked': self.lock_acquired.locked(),
            # Note: RLock doesn't have .locked() method, check via acquire
            'rlock_acquired_locked': not self.rlock_acquired.acquire(blocking=False) or (self.rlock_acquired.release() or False),
            'event_is_set': self.event.is_set(),
            'event_set_is_set': self.event_set.is_set(),
            'semaphore_value': self.semaphore._value,
            'bounded_semaphore_value': self.bounded_semaphore._value,
            'thread_local_value': getattr(self.thread_local, 'value', None),
            'thread_local_number': getattr(self.thread_local, 'number', None),
            
            # Queue contents
            'queue_size': self.queue.qsize(),
            'queue_empty_size': self.queue_empty.qsize(),
            'lifo_queue_size': self.lifo_queue.qsize(),
            'priority_queue_size': self.priority_queue.qsize(),
            'queue_full_size': self.queue_full.qsize(),
            
            # Logger config
            'logger_name': self.logger.name,
            'logger_level': self.logger.level,
            'logger_warning_level': self.logger_warning.level,
            'logger_handlers_count': len(self.logger_with_multiple_handlers.handlers),
            
            # File states
            'temp_file_name': self.temp_file.name,
            'temp_file_position': self.temp_file.tell(),
            'temp_file_binary_name': self.temp_file_binary.name,
            'string_io_value': self.string_io.getvalue(),
            'bytes_io_value': self.bytes_io.getvalue(),
            'temp_file_mid_position_pos': self.temp_file_mid_position.tell(),
            'string_io_positioned_pos': self.string_io_positioned.tell(),
            
            # Regex patterns
            'regex_pattern_pattern': self.regex_pattern.pattern,
            'regex_pattern_flags': self.regex_pattern.flags,
            'regex_simple_pattern': self.regex_simple.pattern,
            'regex_complex_pattern': self.regex_complex.pattern,
            'regex_with_groups_groups': self.regex_with_groups.groups,
            
            # SQLite
            'sqlite_table_count': len(self.sqlite_cursor.execute("SELECT * FROM test").fetchall()),
            'sqlite_complex_users_count': len(self.sqlite_cursor_complex.execute("SELECT * FROM users").fetchall()),
            'sqlite_complex_posts_count': len(self.sqlite_cursor_complex.execute("SELECT * FROM posts").fetchall()),
            
            # Custom objects
            'custom_serialize_obj_data': self.custom_serialize_obj.data,
            'to_dict_obj_x': self.to_dict_obj.x,
            'to_dict_obj_y': self.to_dict_obj.y,
            'dynamic_class_instance_value': self.dynamic_class_instance.value,
            
            # Weak references (check if alive)
            'weak_reference_alive': self.weak_reference() is not None,
            'weak_reference2_alive': self.weak_reference2() is not None,
            'complex_weak_reference_alive': self.complex_weak_reference() is not None,
            
            # Circular references (check identity)
            'circular_dict_is_circular': self.circular_dict["self"] is self.circular_dict,
            'circular_list_is_circular': self.circular_list[3] is self.circular_list,
            'ref_a_points_to_b': self.ref_a["points_to_b"] is self.ref_b,
            'ref_b_points_to_a': self.ref_b["points_to_a"] is self.ref_a,
            
            # Function callability
            'function_callable': callable(self.function),
            'lambda_callable': callable(self.lambda_function),
            'partial_callable': callable(self.partial_function),
            'bound_method_callable': callable(self.bound_method),
        }
        
        return self._verification_checksums
    
    def verify(self, other):
        """
        Verify that another WorstPossibleObject matches this one.
        
        Returns:
            (all_passed: bool, failures: list of str)
        """
        failures = []
        
        # Check all verification checksums
        for key, expected_value in self._verification_checksums.items():
            try:
                if key == 'weak_reference_alive':
                    actual_value = other.weak_reference() is not None
                elif key == 'weak_reference2_alive':
                    actual_value = other.weak_reference2() is not None
                elif key == 'complex_weak_reference_alive':
                    actual_value = other.complex_weak_reference() is not None
                elif key == 'circular_dict_is_circular':
                    actual_value = other.circular_dict["self"] is other.circular_dict
                elif key == 'circular_list_is_circular':
                    actual_value = other.circular_list[3] is other.circular_list
                elif key == 'ref_a_points_to_b':
                    actual_value = other.ref_a["points_to_b"] is other.ref_b
                elif key == 'ref_b_points_to_a':
                    actual_value = other.ref_b["points_to_a"] is other.ref_a
                elif key == 'function_callable':
                    actual_value = callable(other.function)
                elif key == 'lambda_callable':
                    actual_value = callable(other.lambda_function)
                elif key == 'partial_callable':
                    actual_value = callable(other.partial_function)
                elif key == 'bound_method_callable':
                    actual_value = callable(other.bound_method)
                elif key == 'thread_local_value':
                    actual_value = getattr(other.thread_local, 'value', None)
                elif key == 'thread_local_number':
                    actual_value = getattr(other.thread_local, 'number', None)
                elif key.endswith('_name') and 'file' in key:
                    # For file names, just check they exist (paths may differ)
                    actual_value = getattr(other, key.replace('_name', '')).name
                    if actual_value:
                        continue  # Don't compare paths directly
                elif key == 'sqlite_table_count':
                    actual_value = len(other.sqlite_cursor.execute("SELECT * FROM test").fetchall())
                elif key == 'sqlite_complex_users_count':
                    actual_value = len(other.sqlite_cursor_complex.execute("SELECT * FROM users").fetchall())
                elif key == 'sqlite_complex_posts_count':
                    actual_value = len(other.sqlite_cursor_complex.execute("SELECT * FROM posts").fetchall())
                else:
                    # General attribute access
                    actual_value = other._verification_checksums.get(key)
                
                if actual_value != expected_value:
                    failures.append(f"{key}: expected {expected_value!r}, got {actual_value!r}")
            except Exception as e:
                failures.append(f"{key}: error during verification - {e}")
        
        # Test that functions actually work
        try:
            if other.function(5, 10) != 15:
                failures.append("function: does not compute correctly")
        except Exception as e:
            failures.append(f"function: error calling - {e}")
        
        try:
            if other.lambda_function(10) != 20:
                failures.append("lambda_function: does not compute correctly")
        except Exception as e:
            failures.append(f"lambda_function: error calling - {e}")
        
        try:
            if other.partial_function(y=5) != 15:  # partial(test_function, 5) called with y=5
                failures.append("partial_function: does not compute correctly")
        except Exception as e:
            failures.append(f"partial_function: error calling - {e}")
        
        # Test regex works
        try:
            match = other.regex_pattern.search("version 2.71 test")
            if not match:
                failures.append("regex_pattern: does not match correctly")
        except Exception as e:
            failures.append(f"regex_pattern: error matching - {e}")
        
        # Test circular references maintain identity
        if not (other.circular_dict["self"] is other.circular_dict and 
                other.circular_dict["also_self"] is other.circular_dict):
            failures.append("circular_dict: multiple references don't point to same object")
        
        if not (other.circular_nested[1][2] is other.circular_nested):
            failures.append("circular_nested: nested circular reference broken")
        
        if not (other.circular_nested[2]["b"] is other.circular_nested[0]):
            failures.append("circular_nested: cross-reference broken")
        
        return (len(failures) == 0, failures)
    
    def cleanup(self):
        """Clean up any resources (files, connections, etc.)."""
        self._log("\n[CLEANUP] Cleaning up resources...")
        
        resources_to_cleanup = [
            ('temp_file', lambda: (self.temp_file.close(), Path(self.temp_file.name).unlink(missing_ok=True))),
            ('temp_file_binary', lambda: (self.temp_file_binary.close(), Path(self.temp_file_binary.name).unlink(missing_ok=True))),
            ('temp_file_mid_position', lambda: (self.temp_file_mid_position.close(), Path(self.temp_file_mid_position.name).unlink(missing_ok=True))),
            ('mmap', lambda: (self.mmap.close(), self.mmap_file.close(), Path(self.mmap_file.name).unlink(missing_ok=True))),
            ('sqlite_conn', lambda: (self.sqlite_conn.close(), Path(self.sqlite_file.name).unlink(missing_ok=True))),
            ('sqlite_conn_complex', lambda: (self.sqlite_conn_complex.close(), Path(self.sqlite_file_complex.name).unlink(missing_ok=True))),
        ]
        
        for attr_name, cleanup_func in resources_to_cleanup:
            try:
                cleanup_func()
                self._log(f"  ✓ Cleaned up {attr_name}")
            except Exception as e:
                self._log(f"  ⚠ Failed to clean up {attr_name}: {e}")
        
        if self._debug_file:
            self._debug_file.close()
            self._debug_file = None
    
    def get_initialization_report(self) -> str:
        """Generate a detailed report of what was initialized."""
        report = []
        report.append("="*70)
        report.append("WORST POSSIBLE OBJECT - INITIALIZATION REPORT")
        report.append("="*70)
        report.append(f"\nSkipped types: {self.skip_types or 'None'}")
        report.append(f"\nTotal verification checksums: {len(self._verification_checksums)}")
        
        for category, items in self._initialized_types.items():
            if items:
                report.append(f"\n[{category.upper()}] - {len(items)} items:")
                for item in items:
                    report.append(f"  - {item}")
        
        report.append("\n" + "="*70)
        return "\n".join(report)
    
    def list_all_attributes(self) -> Dict[str, List[str]]:
        """List all attributes grouped by type."""
        attrs = {
            'primitives': [],
            'collections': [],
            'functions': [],
            'locks': [],
            'queues': [],
            'events': [],
            'files': [],
            'regex': [],
            'sqlite': [],
            'generators': [],
            'iterators': [],
            'weakrefs': [],
            'other': []
        }
        
        for name in dir(self):
            if name.startswith('_') or name in ['cleanup', 'verify', 'compute_verification_data']:
                continue
            
            try:
                obj = getattr(self, name)
                obj_type = type(obj).__name__
                
                if callable(obj) and not isinstance(obj, type):
                    attrs['functions'].append(f"{name} ({obj_type})")
                elif isinstance(obj, threading.Lock):
                    attrs['locks'].append(f"{name} (Lock)")
                elif isinstance(obj, (queue.Queue, queue.LifoQueue, queue.PriorityQueue)):
                    attrs['queues'].append(f"{name} ({obj_type}, size={obj.qsize()})")
                elif isinstance(obj, (threading.Event, threading.Semaphore, threading.BoundedSemaphore)):
                    attrs['events'].append(f"{name} ({obj_type})")
                elif hasattr(obj, 'read') or hasattr(obj, 'write'):
                    attrs['files'].append(f"{name} ({obj_type})")
                elif isinstance(obj, type(re.compile(''))):
                    attrs['regex'].append(f"{name} (pattern={obj.pattern[:30]}...)")
                elif isinstance(obj, (sqlite3.Connection, sqlite3.Cursor)):
                    attrs['sqlite'].append(f"{name} ({obj_type})")
                elif obj_type == 'generator':
                    attrs['generators'].append(f"{name} (generator)")
                elif isinstance(obj, (dict, list, tuple, set, frozenset)):
                    attrs['collections'].append(f"{name} ({obj_type}, len={len(obj)})")
                elif isinstance(obj, (int, float, str, bytes, bool, type(None))):
                    attrs['primitives'].append(f"{name} ({obj_type})")
                else:
                    attrs['other'].append(f"{name} ({obj_type})")
            except Exception as e:
                attrs['other'].append(f"{name} (error: {e})")
        
        return attrs
    
    def inspect_object(self, attr_name: str) -> str:
        """Get detailed information about a specific attribute."""
        if not hasattr(self, attr_name):
            return f"❌ Attribute '{attr_name}' not found"
        
        obj = getattr(self, attr_name)
        lines = []
        lines.append(f"\n{'='*70}")
        lines.append(f"INSPECTING: {attr_name}")
        lines.append(f"{'='*70}")
        lines.append(f"Type: {type(obj)}")
        lines.append(f"Type name: {type(obj).__name__}")
        lines.append(f"Module: {type(obj).__module__}")
        
        if callable(obj):
            lines.append(f"Callable: Yes")
            if hasattr(obj, '__name__'):
                lines.append(f"Function name: {obj.__name__}")
        
        if isinstance(obj, (dict, list, tuple, set, frozenset)):
            lines.append(f"Length: {len(obj)}")
            if len(obj) <= 10:
                lines.append(f"Contents: {obj}")
            else:
                lines.append(f"Contents (first 10): {list(obj)[:10] if not isinstance(obj, dict) else list(obj.items())[:10]}")
        
        if hasattr(obj, '__dict__'):
            lines.append(f"Attributes: {list(obj.__dict__.keys())}")
        
        # Type-specific info
        try:
            if isinstance(obj, threading.Lock):
                lines.append(f"Locked: {obj.locked()}")
            elif isinstance(obj, threading.Event):
                lines.append(f"Is set: {obj.is_set()}")
            elif isinstance(obj, (queue.Queue, queue.LifoQueue, queue.PriorityQueue)):
                lines.append(f"Queue size: {obj.qsize()}")
                lines.append(f"Max size: {obj.maxsize}")
            
            # Check for file-like tell() method
            try:
                if callable(getattr(obj, 'tell', None)):
                    lines.append(f"File position: {obj.tell()}")  # type: ignore
            except:
                pass
        except Exception as e:
            lines.append(f"Error getting type-specific info: {e}")
        
        lines.append(f"{'='*70}\n")
        return "\n".join(lines)
    
    def test_serialization_by_type(self, type_category: str) -> Dict[str, Tuple[bool, str]]:
        """
        Test which specific objects in a category can/can't be pickled.
        
        Args:
            type_category: 'functions', 'locks', 'queues', etc.
        
        Returns:
            Dict mapping attr_name to (success, error_msg)
        """
        import pickle
        
        attrs = self.list_all_attributes()
        if type_category not in attrs:
            return {"error": (False, f"Unknown category: {type_category}")}
        
        results = {}
        for attr_desc in attrs[type_category]:
            attr_name = attr_desc.split()[0]
            obj = getattr(self, attr_name)
            
            try:
                pickled = pickle.dumps(obj)
                unpickled = pickle.loads(pickled)
                results[attr_name] = (True, "Success")
            except Exception as e:
                results[attr_name] = (False, str(e))
        
        return results
    
    def generate_debug_report(self, test_serialization=False) -> str:
        """Generate comprehensive debug report."""
        lines = []
        lines.append("\n" + "="*70)
        lines.append("WORST POSSIBLE OBJECT - DEBUG REPORT")
        lines.append("="*70)
        
        # Basic info
        lines.append(f"\nVerbose mode: {self.verbose}")
        lines.append(f"Skipped types: {self.skip_types or 'None'}")
        lines.append(f"Verification checksums: {len(self._verification_checksums)}")
        
        # Initialization summary
        lines.append("\n[INITIALIZATION SUMMARY]")
        for category, items in self._initialized_types.items():
            lines.append(f"  {category}: {len(items)} items")
        
        # Attribute counts by type
        attrs = self.list_all_attributes()
        lines.append("\n[ATTRIBUTE COUNTS BY TYPE]")
        for category, items in attrs.items():
            if items:
                lines.append(f"  {category}: {len(items)}")
        
        # Test basic pickle if requested
        if test_serialization:
            lines.append("\n[PICKLE TEST RESULTS]")
            import pickle
            
            for category in ['primitives', 'collections', 'functions', 'locks', 'queues']:
                if category in attrs and attrs[category]:
                    results = self.test_serialization_by_type(category)
                    successes = sum(1 for success, _ in results.values() if success)
                    failures = len(results) - successes
                    lines.append(f"  {category}: {successes} passed, {failures} failed")
                    
                    if failures > 0:
                        lines.append(f"    Failed:")
                        for name, (success, msg) in results.items():
                            if not success:
                                lines.append(f"      - {name}: {msg[:60]}")
        
        lines.append("\n" + "="*70)
        return "\n".join(lines)

    class Nested1:

        def __init__(self):
            super().__init__()

    
        class Nested2:

            def __init__(self):
                super().__init__()


        
        class Nested3:

            def __init__(self):
                super().__init__()


                class Nested4:

                    def __init__(self):
                        super().__init__()
                        
                        