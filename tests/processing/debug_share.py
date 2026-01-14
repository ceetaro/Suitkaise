#!/usr/bin/env python3
"""
Debug Share - Diagnostic script to identify where Share hangs.

Run this outside the sandbox to diagnose timeout issues.
"""

import sys
import time
import multiprocessing

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')


def test_manager_creation():
    """Test if Manager can be created."""
    print("Testing Manager creation...", end=" ", flush=True)
    start = time.time()
    
    try:
        from multiprocessing import Manager
        manager = Manager()
        print(f"OK ({time.time() - start:.2f}s)")
        return manager
    except Exception as e:
        print(f"FAILED: {e}")
        return None


def test_manager_dict(manager):
    """Test if Manager dict works."""
    print("Testing Manager dict...", end=" ", flush=True)
    start = time.time()
    
    try:
        d = manager.dict()
        d['test'] = 'value'
        assert d['test'] == 'value'
        print(f"OK ({time.time() - start:.2f}s)")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def test_manager_queue(manager):
    """Test if Manager Queue works."""
    print("Testing Manager Queue...", end=" ", flush=True)
    start = time.time()
    
    try:
        q = manager.Queue()
        q.put("test")
        result = q.get(timeout=1.0)
        assert result == "test"
        print(f"OK ({time.time() - start:.2f}s)")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def test_coordinator_creation():
    """Test if Coordinator can be created."""
    print("Testing Coordinator creation...", end=" ", flush=True)
    start = time.time()
    
    try:
        from suitkaise.processing._int.share.coordinator import _Coordinator
        coord = _Coordinator()
        print(f"OK ({time.time() - start:.2f}s)")
        return coord
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_coordinator_start(coord):
    """Test if Coordinator can be started."""
    print("Testing Coordinator start...", end=" ", flush=True)
    start = time.time()
    
    try:
        coord.start()
        time.sleep(0.1)  # Give it time to start
        if coord.is_alive:
            print(f"OK ({time.time() - start:.2f}s)")
            return True
        else:
            print("FAILED: Process not alive")
            return False
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coordinator_stop(coord):
    """Test if Coordinator can be stopped."""
    print("Testing Coordinator stop...", end=" ", flush=True)
    start = time.time()
    
    try:
        result = coord.stop(timeout=5.0)
        if result:
            print(f"OK ({time.time() - start:.2f}s)")
            return True
        else:
            print(f"FAILED: Timeout ({time.time() - start:.2f}s)")
            coord.kill()
            return False
    except Exception as e:
        print(f"FAILED: {e}")
        coord.kill()
        return False


def test_share_creation():
    """Test if Share can be created."""
    print("Testing Share creation...", end=" ", flush=True)
    start = time.time()
    
    try:
        from suitkaise.processing import Share
        share = Share()
        print(f"OK ({time.time() - start:.2f}s)")
        return share
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_share_start(share):
    """Test if Share can be started."""
    print("Testing Share start...", end=" ", flush=True)
    start = time.time()
    
    try:
        share.start()
        time.sleep(0.1)
        if share.is_running:
            print(f"OK ({time.time() - start:.2f}s)")
            return True
        else:
            print("FAILED: Not running")
            return False
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_share_set_object(share):
    """Test if Share can accept objects."""
    print("Testing Share.timer = Sktimer()...", end=" ", flush=True)
    start = time.time()
    
    try:
        from suitkaise.timing import Sktimer
        share.timer = Sktimer()
        print(f"OK ({time.time() - start:.2f}s)")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_share_get_object(share):
    """Test if Share can retrieve objects."""
    print("Testing share.timer access...", end=" ", flush=True)
    start = time.time()
    
    try:
        timer = share.timer
        print(f"OK ({time.time() - start:.2f}s)")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_share_stop(share):
    """Test if Share can be stopped."""
    print("Testing Share stop...", end=" ", flush=True)
    start = time.time()
    
    try:
        result = share.stop(timeout=5.0)
        if result:
            print(f"OK ({time.time() - start:.2f}s)")
            return True
        else:
            print(f"TIMEOUT ({time.time() - start:.2f}s)")
            return False
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def main():
    print("\n" + "="*60)
    print(" SHARE DEBUG DIAGNOSTIC ".center(60, "="))
    print("="*60 + "\n")
    
    print(f"Python version: {sys.version}")
    print(f"Multiprocessing start method: {multiprocessing.get_start_method()}")
    print()
    
    # Test low-level components first
    print("-" * 40)
    print("LOW-LEVEL MULTIPROCESSING TESTS")
    print("-" * 40)
    
    manager = test_manager_creation()
    if not manager:
        print("\nFailed at Manager creation. Cannot proceed.")
        return
    
    test_manager_dict(manager)
    test_manager_queue(manager)
    
    # Test Coordinator
    print()
    print("-" * 40)
    print("COORDINATOR TESTS")
    print("-" * 40)
    
    coord = test_coordinator_creation()
    if coord:
        started = test_coordinator_start(coord)
        if started:
            test_coordinator_stop(coord)
    
    # Test Share
    print()
    print("-" * 40)
    print("SHARE TESTS")
    print("-" * 40)
    
    share = test_share_creation()
    if share:
        started = test_share_start(share)
        if started:
            test_share_set_object(share)
            test_share_get_object(share)
            test_share_stop(share)
    
    print()
    print("="*60)
    print(" DIAGNOSTIC COMPLETE ".center(60, "="))
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
