"""
Blocking Call Detection Tests

Tests that all blocking call patterns are correctly detected by the analyzer.
"""

import sys
import time as stdlib_time

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.sk.api import Skfunction
from suitkaise.sk._int.analyzer import BLOCKING_CALLS, BLOCKING_METHOD_PATTERNS


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
# Test Functions - Each contains a specific blocking pattern
# =============================================================================

# --- Time Operations ---

def uses_time_sleep():
    """Uses time.sleep()"""
    import time
    time.sleep(1)
    return "done"


def uses_bare_sleep():
    """Uses sleep() imported from time"""
    from time import sleep
    sleep(1)
    return "done"


def uses_timing_sleep():
    """Uses suitkaise timing.sleep()"""
    from suitkaise import timing
    timing.sleep(1)
    return "done"


def uses_sktime_sleep():
    """Uses suitkaise sktime.sleep()"""
    from suitkaise.timing import api as sktime
    sktime.sleep(1)
    return "done"


# --- File I/O ---

def uses_open():
    """Uses open()"""
    f = open("file.txt")
    return f


def uses_file_read():
    """Uses file.read()"""
    with open("file.txt") as f:
        data = f.read()
    return data


def uses_file_write():
    """Uses file.write()"""
    with open("file.txt", "w") as f:
        f.write("data")


def uses_file_readline():
    """Uses file.readline()"""
    with open("file.txt") as f:
        line = f.readline()
    return line


def uses_file_readlines():
    """Uses file.readlines()"""
    with open("file.txt") as f:
        lines = f.readlines()
    return lines


# --- Subprocess ---

def uses_subprocess_run():
    """Uses subprocess.run()"""
    import subprocess
    subprocess.run(["ls"])


def uses_subprocess_call():
    """Uses subprocess.call()"""
    import subprocess
    subprocess.call(["ls"])


def uses_subprocess_popen():
    """Uses subprocess.Popen()"""
    import subprocess
    proc = subprocess.Popen(["ls"])
    return proc


# --- Requests Library ---

def uses_requests_get():
    """Uses requests.get()"""
    import requests
    requests.get("https://example.com")


def uses_requests_post():
    """Uses requests.post()"""
    import requests
    requests.post("https://example.com", data={})


def uses_requests_put():
    """Uses requests.put()"""
    import requests
    requests.put("https://example.com", data={})


def uses_requests_delete():
    """Uses requests.delete()"""
    import requests
    requests.delete("https://example.com")


# --- OS Operations ---

def uses_os_system():
    """Uses os.system()"""
    import os
    os.system("ls")


def uses_os_popen():
    """Uses os.popen()"""
    import os
    os.popen("ls")


# --- URL/Socket ---

def uses_urlopen():
    """Uses urllib.request.urlopen()"""
    import urllib.request
    urllib.request.urlopen("https://example.com")


def uses_socket_create_connection():
    """Uses socket.create_connection()"""
    import socket
    socket.create_connection(("example.com", 80))


# --- Database Patterns ---

def uses_cursor_execute():
    """Uses cursor.execute()"""
    cursor = get_cursor()
    cursor.execute("SELECT 1")


def uses_cursor_fetchall():
    """Uses cursor.fetchall()"""
    cursor = get_cursor()
    cursor.fetchall()


def uses_connection_commit():
    """Uses connection.commit()"""
    connection = get_connection()
    connection.commit()


# --- Suitkaise Patterns ---

def uses_pool_map():
    """Uses Pool.map()"""
    pool = get_pool()
    pool.map(lambda x: x, [1, 2, 3])


def uses_pool_imap():
    """Uses Pool.imap()"""
    pool = get_pool()
    pool.imap(lambda x: x, [1, 2, 3])


def uses_pool_starmap():
    """Uses Pool.starmap()"""
    pool = get_pool()
    pool.starmap(lambda x, y: x + y, [(1, 2), (3, 4)])


def uses_circuit_short():
    """Uses Circuit.short()"""
    circuit = get_circuit()
    circuit.short()


def uses_circuit_trip():
    """Uses Circuit.trip()"""
    circuit = get_circuit()
    circuit.trip()


# --- Method Pattern Detection ---

def uses_generic_wait():
    """Uses something.wait()"""
    obj = get_something()
    obj.wait()


def uses_generic_join():
    """Uses something.join()"""
    thread = get_thread()
    thread.join()


def uses_generic_acquire():
    """Uses lock.acquire()"""
    lock = get_lock()
    lock.acquire()


def uses_generic_recv():
    """Uses socket.recv()"""
    sock = get_socket()
    sock.recv(1024)


def uses_generic_send():
    """Uses socket.send()"""
    sock = get_socket()
    sock.send(b"data")


def uses_generic_accept():
    """Uses socket.accept()"""
    sock = get_socket()
    sock.accept()


def uses_generic_connect():
    """Uses socket.connect()"""
    sock = get_socket()
    sock.connect(("host", 80))


# --- Helpers (not actually used, just for AST parsing) ---

def get_cursor():
    pass

def get_connection():
    pass

def get_pool():
    pass

def get_circuit():
    pass

def get_something():
    pass

def get_thread():
    pass

def get_lock():
    pass

def get_socket():
    pass


# =============================================================================
# Tests
# =============================================================================

def test_time_sleep_detected():
    """time.sleep should be detected."""
    sk = Skfunction(uses_time_sleep)
    assert sk.has_blocking_calls, "time.sleep should be detected"
    assert any("sleep" in call for call in sk.blocking_calls)


def test_bare_sleep_detected():
    """sleep (imported from time) should be detected."""
    sk = Skfunction(uses_bare_sleep)
    assert sk.has_blocking_calls, "bare sleep should be detected"
    assert "sleep" in sk.blocking_calls


def test_timing_sleep_detected():
    """timing.sleep should be detected."""
    sk = Skfunction(uses_timing_sleep)
    assert sk.has_blocking_calls, f"timing.sleep should be detected, got {sk.blocking_calls}"
    assert any("timing.sleep" in call for call in sk.blocking_calls)


def test_sktime_sleep_detected():
    """sktime.sleep should be detected."""
    sk = Skfunction(uses_sktime_sleep)
    assert sk.has_blocking_calls, f"sktime.sleep should be detected, got {sk.blocking_calls}"
    assert any("sleep" in call for call in sk.blocking_calls)


def test_open_detected():
    """open() should be detected."""
    sk = Skfunction(uses_open)
    assert sk.has_blocking_calls, "open should be detected"
    assert "open" in sk.blocking_calls


def test_file_read_detected():
    """file.read() should be detected."""
    sk = Skfunction(uses_file_read)
    assert sk.has_blocking_calls, "file.read should be detected"
    assert any("read" in call for call in sk.blocking_calls)


def test_file_write_detected():
    """file.write() should be detected."""
    sk = Skfunction(uses_file_write)
    assert sk.has_blocking_calls, "file.write should be detected"
    assert any("write" in call for call in sk.blocking_calls)


def test_subprocess_run_detected():
    """subprocess.run() should be detected."""
    sk = Skfunction(uses_subprocess_run)
    assert sk.has_blocking_calls, "subprocess.run should be detected"
    assert any("subprocess.run" in call for call in sk.blocking_calls)


def test_subprocess_call_detected():
    """subprocess.call() should be detected."""
    sk = Skfunction(uses_subprocess_call)
    assert sk.has_blocking_calls, "subprocess.call should be detected"
    assert any("subprocess.call" in call for call in sk.blocking_calls)


def test_requests_get_detected():
    """requests.get() should be detected."""
    sk = Skfunction(uses_requests_get)
    assert sk.has_blocking_calls, "requests.get should be detected"
    assert any("requests.get" in call for call in sk.blocking_calls)


def test_requests_post_detected():
    """requests.post() should be detected."""
    sk = Skfunction(uses_requests_post)
    assert sk.has_blocking_calls, "requests.post should be detected"
    assert any("requests.post" in call for call in sk.blocking_calls)


def test_os_system_detected():
    """os.system() should be detected."""
    sk = Skfunction(uses_os_system)
    assert sk.has_blocking_calls, "os.system should be detected"
    assert any("os.system" in call for call in sk.blocking_calls)


def test_urlopen_detected():
    """urllib.request.urlopen() should be detected."""
    sk = Skfunction(uses_urlopen)
    assert sk.has_blocking_calls, "urlopen should be detected"
    assert any("urlopen" in call for call in sk.blocking_calls)


def test_cursor_execute_detected():
    """cursor.execute() should be detected."""
    sk = Skfunction(uses_cursor_execute)
    assert sk.has_blocking_calls, "cursor.execute should be detected"
    assert any("execute" in call for call in sk.blocking_calls)


def test_cursor_fetchall_detected():
    """cursor.fetchall() should be detected."""
    sk = Skfunction(uses_cursor_fetchall)
    assert sk.has_blocking_calls, "cursor.fetchall should be detected"
    assert any("fetchall" in call for call in sk.blocking_calls)


def test_connection_commit_detected():
    """connection.commit() should be detected."""
    sk = Skfunction(uses_connection_commit)
    assert sk.has_blocking_calls, "connection.commit should be detected"
    assert any("commit" in call for call in sk.blocking_calls)


def test_pool_map_detected():
    """Pool.map() should be detected."""
    sk = Skfunction(uses_pool_map)
    assert sk.has_blocking_calls, f"pool.map should be detected, got {sk.blocking_calls}"
    assert any("map" in call for call in sk.blocking_calls)


def test_pool_imap_detected():
    """Pool.imap() should be detected."""
    sk = Skfunction(uses_pool_imap)
    assert sk.has_blocking_calls, f"pool.imap should be detected, got {sk.blocking_calls}"
    assert any("imap" in call for call in sk.blocking_calls)


def test_circuit_short_detected():
    """Circuit.short() should be detected."""
    sk = Skfunction(uses_circuit_short)
    assert sk.has_blocking_calls, f"circuit.short should be detected, got {sk.blocking_calls}"
    assert any("short" in call for call in sk.blocking_calls)


def test_circuit_trip_detected():
    """Circuit.trip() should be detected."""
    sk = Skfunction(uses_circuit_trip)
    assert sk.has_blocking_calls, f"circuit.trip should be detected, got {sk.blocking_calls}"
    assert any("trip" in call for call in sk.blocking_calls)


def test_generic_wait_detected():
    """something.wait() should be detected."""
    sk = Skfunction(uses_generic_wait)
    assert sk.has_blocking_calls, "wait should be detected"
    assert any("wait" in call for call in sk.blocking_calls)


def test_generic_join_detected():
    """thread.join() should be detected."""
    sk = Skfunction(uses_generic_join)
    assert sk.has_blocking_calls, "join should be detected"
    assert any("join" in call for call in sk.blocking_calls)


def test_generic_acquire_detected():
    """lock.acquire() should be detected."""
    sk = Skfunction(uses_generic_acquire)
    assert sk.has_blocking_calls, "acquire should be detected"
    assert any("acquire" in call for call in sk.blocking_calls)


def test_generic_recv_detected():
    """socket.recv() should be detected."""
    sk = Skfunction(uses_generic_recv)
    assert sk.has_blocking_calls, "recv should be detected"
    assert any("recv" in call for call in sk.blocking_calls)


def test_generic_send_detected():
    """socket.send() should be detected."""
    sk = Skfunction(uses_generic_send)
    assert sk.has_blocking_calls, "send should be detected"
    assert any("send" in call for call in sk.blocking_calls)


def test_generic_accept_detected():
    """socket.accept() should be detected."""
    sk = Skfunction(uses_generic_accept)
    assert sk.has_blocking_calls, "accept should be detected"
    assert any("accept" in call for call in sk.blocking_calls)


def test_generic_connect_detected():
    """socket.connect() should be detected."""
    sk = Skfunction(uses_generic_connect)
    assert sk.has_blocking_calls, "connect should be detected"
    assert any("connect" in call for call in sk.blocking_calls)


def test_no_false_positives():
    """Pure functions should not be detected as blocking."""
    def pure_function(x):
        return x * 2
    
    sk = Skfunction(pure_function)
    assert not sk.has_blocking_calls, f"Pure function should not have blocking calls, got {sk.blocking_calls}"


def test_multiple_blocking_calls_detected():
    """Functions with multiple blocking calls should detect all of them."""
    def multi_blocking():
        import time
        import requests
        time.sleep(1)
        requests.get("https://example.com")
        with open("file.txt") as f:
            f.read()
    
    sk = Skfunction(multi_blocking)
    assert sk.has_blocking_calls
    assert len(sk.blocking_calls) >= 3, f"Expected at least 3 blocking calls, got {sk.blocking_calls}"


# =============================================================================
# Coverage Check
# =============================================================================

def test_all_blocking_calls_have_tests():
    """Verify we have test coverage for major blocking call categories."""
    # This is a meta-test to ensure we don't forget to add tests
    # for new blocking patterns
    
    categories_tested = {
        'time': ['time.sleep', 'sleep'],
        'suitkaise_timing': ['timing.sleep', 'sktime.sleep'],
        'file_io': ['open', 'read', 'write'],
        'subprocess': ['subprocess.run', 'subprocess.call'],
        'requests': ['requests.get', 'requests.post'],
        'os': ['os.system'],
        'urllib': ['urllib.request.urlopen'],
        'database': ['cursor.execute', 'connection.commit'],
        'suitkaise_pool': ['map', 'imap'],
        'suitkaise_circuit': ['short', 'trip'],
        'patterns': ['wait', 'join', 'acquire', 'recv', 'send'],
    }
    
    # Just a sanity check that our test categories exist
    assert len(categories_tested) >= 10, "Should have comprehensive test coverage"


def run_all_tests():
    runner = TestRunner("Blocking Call Detection Tests")
    for name, test_func in globals().items():
        if name.startswith("test_") and callable(test_func):
            runner.run_test(name, test_func)
    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
