"""
AST analysis for auto-generating _shared_meta and detecting blocking calls.

This module analyzes class definitions to:
1. Generate _shared_meta by tracking attribute reads/writes in methods
2. Detect blocking calls (time.sleep, file I/O, requests, etc.)
"""

import ast
import inspect
import textwrap
from typing import Dict, List, Set, Tuple, Any, Type


# Known blocking calls that should be wrapped with to_thread()
BLOCKING_CALLS: Set[str] = {
    # time module
    'time.sleep',
    'sleep',  # if imported as `from time import sleep`
    
    # suitkaise timing
    'timing.sleep',
    'sktime.sleep',
    'suitkaise.timing.sleep',
    
    # File I/O
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
    'subprocess.Popen',
    
    # requests library
    'requests.get',
    'requests.post',
    'requests.put',
    'requests.delete',
    'requests.patch',
    'requests.head',
    'requests.options',
    'requests.request',
    
    # urllib
    'urllib.request.urlopen',
    'urlopen',
    
    # socket
    'socket.socket',
    'socket.create_connection',
    
    # Database (common patterns)
    'cursor.execute',
    'cursor.executemany',
    'cursor.fetchone',
    'cursor.fetchall',
    'cursor.fetchmany',
    'connection.commit',
    'connection.rollback',
}

# Method names that typically indicate blocking behavior
# If a call ends with one of these, it's considered blocking
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
    'acquire',  # Lock acquisition
    
    # suitkaise patterns
    'map',      # Pool.map
    'imap',     # Pool.imap
    'starmap',  # Pool.starmap
    'short',    # Circuit.short (may sleep)
    'trip',     # Circuit.trip (may sleep)
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
        # Check if this is self.something
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            attr_name = node.attr
            
            # Check context - are we reading or writing?
            if isinstance(node.ctx, ast.Store):
                self.writes.add(attr_name)
            elif isinstance(node.ctx, ast.Load):
                # Could be a read, but also check if it's target of augmented assign
                self.reads.add(attr_name)
        
        # Continue visiting children
        self.generic_visit(node)
    
    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Handle augmented assignments like self.x += 1 (both read and write)."""
        if isinstance(node.target, ast.Attribute):
            if isinstance(node.target.value, ast.Name) and node.target.value.id == 'self':
                attr_name = node.target.attr
                self.reads.add(attr_name)
                self.writes.add(attr_name)
        
        # Visit the value expression
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
            # Check if it's a known blocking call
            if call_name in BLOCKING_CALLS:
                self.blocking_calls.append(call_name)
            else:
                # Check for pattern matches (e.g., anything.sleep, anything.read)
                parts = call_name.split('.')
                if parts[-1] in BLOCKING_METHOD_PATTERNS:
                    self.blocking_calls.append(call_name)
        
        # Continue visiting children
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
        # Dedent to handle methods defined inside classes
        return textwrap.dedent(source)
    except (OSError, TypeError):
        return None


def _analyze_method(method) -> Tuple[Set[str], Set[str], List[str]]:
    """
    Analyze a single method to extract:
    - reads: set of self.attr that are read
    - writes: set of self.attr that are written
    - blocking_calls: list of blocking calls found
    
    Returns:
        Tuple of (reads, writes, blocking_calls)
    """
    source = _get_method_source(method)
    if source is None:
        return set(), set(), []
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set(), set(), []
    
    # Find attribute accesses
    attr_visitor = _AttributeVisitor()
    attr_visitor.visit(tree)
    
    # Find blocking calls
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
        # Skip dunder methods except __init__
        if name.startswith('__') and name != '__init__':
            continue
        
        # For _shared_meta: skip private methods (except __init__)
        # For blocking detection: include ALL methods (including private)
        is_private = name.startswith('_') and name != '__init__'
        
        if isinstance(member, property):
            # Analyze property getter
            if member.fget:
                reads, writes, blocks = _analyze_method(member.fget)
                if not is_private:
                    shared_meta['properties'][name] = {'reads': list(reads)}
                if blocks:
                    blocking_calls[name] = blocks
                    
        elif callable(member) and not isinstance(member, type):
            # It's a method
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
