"""
AST analysis for auto-generating _shared_meta and detecting blocking calls.

This module analyzes class definitions to:
1. Generate _shared_meta by tracking attribute reads/writes in methods
2. Detect blocking calls (time.sleep, file I/O, requests, etc.)
3. Check for explicit @blocking decorator (defined in api.py)
"""

import ast
import inspect
import textwrap
from typing import Dict, List, Set, Tuple, Any, Type


# known blocking calls that should be wrapped with to_thread()
# NOTE: store lowercase entries and compare against lowercased call names.
BLOCKING_CALLS: Set[str] = {
    # time module
    'time.sleep',
    'sleep',  # if imported as `from time import sleep`
    
    # timing (suitkaise)
    'timing.sleep',
    'sktime.sleep',
    'suitkaise.timing.sleep',
    
    # file io
    'open',
    'read',
    'write',
    'readline',
    'readlines',
    'writelines',
    
    # os module
    'os.read',
    'os.write',
    'os.popen',
    'os.system',
    
    # subprocess
    'subprocess.run',
    'subprocess.call',
    'subprocess.check_call',
    'subprocess.check_output',
    'subprocess.popen',
    
    # requests
    'requests.get',
    'requests.post',
    'requests.put',
    'requests.delete',
    'requests.patch',
    'requests.head',
    'requests.options',
    'requests.request',
    
    # httpx
    'httpx.get',
    'httpx.post',
    'httpx.put',
    'httpx.delete',
    'httpx.patch',
    'httpx.head',
    'httpx.options',
    'httpx.request',
    'httpx.stream',
    
    # urllib
    'urllib.request.urlopen',
    'urlopen',
    
    # urllib3
    'urllib3.poolmanager.request',
    'urllib3.connectionpool.request',
    'urllib3.request',
    
    # socket
    'socket.socket',
    'socket.create_connection',
    
    # pathlib file helpers
    'pathlib.path.open',
    'pathlib.path.read_text',
    'pathlib.path.read_bytes',
    'pathlib.path.write_text',
    'pathlib.path.write_bytes',
    
    # shutil file ops
    'shutil.copy',
    'shutil.copy2',
    'shutil.copyfile',
    'shutil.copytree',
    'shutil.move',
    'shutil.rmtree',
    
    # database connectors (sync)
    'sqlite3.connect',
    'psycopg2.connect',
    'psycopg.connect',
    'pymysql.connect',
    'mysql.connector.connect',
    'mysqldb.connect',
    'pyodbc.connect',
    'duckdb.connect',
    'pymssql.connect',
    'oracledb.connect',
    'cx_oracle.connect',
    'snowflake.connector.connect',
    
    # redis helpers (sync)
    'redis.from_url',
    'redis.redis.from_url',
    'redis.strictredis.from_url',
    'redis.sentinel.sentinel',
    
    # pymongo client
    'pymongo.mongoclient',
    'pymongo.mongo_client.mongoclient',
    
    # boto3 client/resource factories
    'boto3.client',
    'boto3.resource',
    'boto3.session.session.client',
    'boto3.session.session.resource',
    
    # kafka-python / confluent-kafka / pika
    'kafka.kafka_producer',
    'kafka.kafkaconsumer',
    'confluent_kafka.producer',
    'confluent_kafka.consumer',
    'pika.blockingconnection',
    
    # elasticsearch/opensearch clients
    'elasticsearch.elasticsearch',
    'opensearchpy.opensearch',
    
    # database (common patterns)
    'cursor.execute',
    'cursor.executemany',
    'cursor.fetchone',
    'cursor.fetchall',
    'cursor.fetchmany',
    'connection.commit',
    'connection.rollback',
}

# method names that typically indicate blocking behavior
# if a call ends with one of these, it's considered blocking
BLOCKING_METHOD_PATTERNS: Set[str] = {
    'sleep',
    'wait',
    'wait_for',
    'join',
    'recv',
    'recvfrom',
    'send',
    'sendto',
    'sendall',
    'accept',
    'connect',
    'listen',
    'read',
    'readline',
    'readlines',
    'write',
    'writelines',
    'fetch',
    'fetchone',
    'fetchall',
    'fetchmany',
    'execute',
    'executemany',
    'commit',
    'rollback',
    'acquire',  # lock acquisition
    
    # pathlib helpers (instance methods)
    'open',
    'read_text',
    'read_bytes',
    'write_text',
    'write_bytes',
    
    # boto3/s3 (common object ops)
    'get_object',
    'put_object',
    'head_object',
    'list_objects',
    'list_objects_v2',
    'delete_object',
    'copy_object',
    'upload_file',
    'upload_fileobj',
    'download_file',
    'download_fileobj',
    'list_buckets',
    'create_bucket',
    'delete_bucket',
    
    # boto3/dynamodb
    'get_item',
    'put_item',
    'update_item',
    'delete_item',
    'batch_get_item',
    'batch_write_item',
    'query',
    'scan',
    
    # boto3/sqs + sns
    'send_message',
    'receive_message',
    'delete_message',
    'publish',
    'subscribe',
    
    # pymongo
    'find',
    'find_one',
    'insert_one',
    'insert_many',
    'update_one',
    'update_many',
    'replace_one',
    'delete_one',
    'delete_many',
    'aggregate',
    'count_documents',
    'distinct',
    'bulk_write',
    
    # redis (blocking variants + streams)
    'blpop',
    'brpop',
    'brpoplpush',
    'bzpopmin',
    'bzpopmax',
    'xread',
    'xreadgroup',
    'get_message',
    
    # elasticsearch/opensearch
    'search',
    'index',
    'bulk',
    'msearch',
    'delete_by_query',
    'update_by_query',
    
    # kafka / rabbitmq
    'produce',
    'send',
    'poll',
    'flush',
    'basic_publish',
    'basic_consume',
    'basic_get',
    
    # cassandra / neo4j / clickhouse / influxdb
    'execute',
    'run',
    'query',
    'write_points',
    'write_api',
    
    # suitkaise patterns
    'map',      # Pool.map
    'imap',     # Pool.imap
    'starmap',  # Pool.starmap
    'short',    # Circuit.short (may sleep)
    'trip',     # Circuit.trip (may sleep)
}

# broad heuristics: only apply when the call name suggests IO context.
BROAD_BLOCKING_METHOD_PATTERNS: Set[str] = {
    'get',
    'set',
    'find',
    'insert',
    'update',
    'delete',
    'query',
    'scan',
    'request',
    'send',
    'recv',
    'read',
    'write',
    'execute',
    'commit',
    'rollback',
}

IO_CONTEXT_PARTS: Set[str] = {
    # databases
    'db',
    'database',
    'cursor',
    'conn',
    'connection',
    'engine',
    'session',
    'pool',
    'psycopg',
    'postgres',
    'mysql',
    'sqlite',
    'mongo',
    'pymongo',
    'redis',
    'sqlalchemy',
    'odbc',
    'duckdb',
    # cloud clients
    'boto3',
    'botocore',
    's3',
    'sqs',
    'sns',
    'dynamodb',
    'kinesis',
    'lambda',
    # messaging/search
    'kafka',
    'rabbitmq',
    'amqp',
    'pika',
    'elasticsearch',
    'opensearch',
    'search',
    # data stores
    'cassandra',
    'neo4j',
    'influx',
    'influxdb',
    'clickhouse',
    # networking
    'http',
    'https',
    'request',
    'requests',
    'httpx',
    'urllib',
    'socket',
    'sock',
    'client',
    'channel',
}


class _AttributeVisitor(ast.NodeVisitor):
    """
    AST visitor that tracks attribute reads and writes within a method.
    """
    
    def __init__(self):
        self.reads: Set[str] = set()
        self.writes: Set[str] = set()
        self._in_store_context = False
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Track self.attr access."""
        # check if this is self.something
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            attr_name = node.attr
            
            # check context - are we reading or writing?
            if isinstance(node.ctx, ast.Store):
                self.writes.add(attr_name)
            elif isinstance(node.ctx, ast.Load):
                # could be a read, but also check if it's target of augmented assign
                self.reads.add(attr_name)
        
        # continue visiting children
        self.generic_visit(node)
    
    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Handle augmented assignments like self.x += 1 (both read and write)."""
        if isinstance(node.target, ast.Attribute):
            if isinstance(node.target.value, ast.Name) and node.target.value.id == 'self':
                attr_name = node.target.attr
                self.reads.add(attr_name)
                self.writes.add(attr_name)
        
        # visit the value expression
        self.visit(node.value)


class _BlockingCallVisitor(ast.NodeVisitor):
    """
    AST visitor that detects blocking calls within a method.
    """
    
    def __init__(self):
        self.blocking_calls: List[str] = []
    
    def visit_Call(self, node: ast.Call) -> None:
        """Detect blocking function/method calls."""
        call_name = self._get_call_name(node)
        
        if call_name:
            call_name_lower = call_name.lower()
            parts = call_name_lower.split('.')
            tail = parts[-1]
            
            # check if it's a known blocking call
            if call_name_lower in BLOCKING_CALLS:
                self.blocking_calls.append(call_name)
            else:
                # check for specific blocking method names
                if tail in BLOCKING_METHOD_PATTERNS:
                    self.blocking_calls.append(call_name)
                # broad heuristics: only when context suggests I/O
                elif tail in BROAD_BLOCKING_METHOD_PATTERNS:
                    has_io_context = any(
                        any(context in part for context in IO_CONTEXT_PARTS)
                        for part in parts
                    )
                    if has_io_context:
                        self.blocking_calls.append(call_name)
        
        # continue visiting children
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> str | None:
        """Extract the full name of a call (e.g., 'time.sleep', 'obj.method')."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            
            if isinstance(current, ast.Name):
                parts.append(current.id)
            
            parts.reverse()
            return '.'.join(parts)
        
        return None


def _get_method_source(method) -> str | None:
    """Get the source code of a method, handling indentation."""
    try:
        source = inspect.getsource(method)
        # dedent to handle methods defined inside classes
        return textwrap.dedent(source)
    except (OSError, TypeError):
        return None


def _analyze_method(method) -> Tuple[Set[str], Set[str], List[str]]:
    """
    Analyze a single method to extract:
    - reads: set of self.attr that are read
    - writes: set of self.attr that are written
    - blocking_calls: list of blocking calls found
    
    Checks for @blocking decorator first - if present, skips AST analysis
    for blocking detection (performance optimization).
    
    Returns:
        Tuple of (reads, writes, blocking_calls)
    """
    # check for explicit @blocking decorator FIRST
    # if found, we can skip AST analysis for blocking detection
    has_blocking_decorator = getattr(method, '_sk_blocking', False)
    if has_blocking_decorator:
        # still need to analyze for attribute access (_shared_meta)
        source = _get_method_source(method)
        if source is None:
            return set(), set(), ['@blocking']
        
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return set(), set(), ['@blocking']
        
        # only analyze attributes, skip blocking call detection
        attr_visitor = _AttributeVisitor()
        attr_visitor.visit(tree)
        return attr_visitor.reads, attr_visitor.writes, ['@blocking']
    
    # no @blocking decorator - do full AST analysis
    source = _get_method_source(method)
    if source is None:
        return set(), set(), []
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set(), set(), []
    
    # find attribute accesses
    attr_visitor = _AttributeVisitor()
    attr_visitor.visit(tree)
    
    # find blocking calls via AST analysis
    blocking_visitor = _BlockingCallVisitor()
    blocking_visitor.visit(tree)
    
    return attr_visitor.reads, attr_visitor.writes, blocking_visitor.blocking_calls


def analyze_class(cls: Type) -> Tuple[Dict[str, Any], Dict[str, List[str]]]:
    """
    Analyze a class to generate _shared_meta and detect blocking calls.
    
    Args:
        cls: The class to analyze
        
    Returns:
        Tuple of (_shared_meta dict, blocking_calls dict mapping method names to calls)
    """
    shared_meta: Dict[str, Any] = {
        'methods': {},
        'properties': {},
    }
    blocking_calls: Dict[str, List[str]] = {}
    
    for name, member in inspect.getmembers(cls):
        # skip dunder methods except __init__
        if name.startswith('__') and name != '__init__':
            continue
        
        # for _shared_meta: skip private methods (except __init__)
        # for blocking detection: include ALL methods (including private)
        is_private = name.startswith('_') and name != '__init__'
        
        if isinstance(member, property):
            # analyze property getter
            if member.fget:
                reads, writes, blocks = _analyze_method(member.fget)
                if not is_private:
                    shared_meta['properties'][name] = {'reads': list(reads)}
                if blocks:
                    blocking_calls[name] = blocks
                    
        elif callable(member) and not isinstance(member, type):
            # it's a method
            reads, writes, blocks = _analyze_method(member)
            if not is_private:
                shared_meta['methods'][name] = {'writes': list(writes)}
            if blocks:
                blocking_calls[name] = blocks
    
    return shared_meta, blocking_calls


def has_blocking_calls(cls: Type) -> bool:
    """Check if a class has any blocking calls."""
    _, blocking = analyze_class(cls)
    return len(blocking) > 0


def get_blocking_methods(cls: Type) -> Dict[str, List[str]]:
    """Get dict of method names to their blocking calls."""
    _, blocking = analyze_class(cls)
    return blocking
