#!/usr/bin/env python3

import sys
import os
import time
import threading
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from suitkaise.fdl._int.classes.progress_bar import _ProgressBar, ProgressBarError


def test_progress_bar_creation():
    """Test progress bar creation and basic properties."""
    print("🧪 Testing progress bar creation...")
    
    # Test basic creation
    progress = _ProgressBar(total=100)
    assert progress.total == 100.0
    assert progress.current == 0.0
    assert progress.percentage == 0
    assert progress.progress == 0.0
    assert not progress.is_complete
    assert not progress.is_displayed
    assert not progress.is_finished
    
    # Test with options
    progress2 = _ProgressBar(total=50, color='green', width=30, show_rate=True)
    assert progress2.total == 50.0
    assert progress2.width == 30
    assert progress2.show_rate == True
    
    # Test invalid total
    try:
        _ProgressBar(total=0)
        assert False, "Should have raised ProgressBarError"
    except ProgressBarError:
        pass
    
    try:
        _ProgressBar(total=-10)
        assert False, "Should have raised ProgressBarError"
    except ProgressBarError:
        pass
    
    print("✅ Progress bar creation tests passed")


def test_atomic_incrementation():
    """Test atomic incrementation (recommended approach)."""
    print("🧪 Testing atomic incrementation...")
    
    progress = _ProgressBar(total=100)
    
    # Test basic updates
    progress.update(25, "Step 1")
    assert progress.current == 25.0
    assert progress.percentage == 25
    
    progress.update(30, "Step 2")
    assert progress.current == 55.0
    assert progress.percentage == 55
    
    progress.update(45, "Step 3")
    assert progress.current == 100.0
    assert progress.percentage == 100
    assert progress.is_complete
    
    # Test overflow protection
    progress2 = _ProgressBar(total=50)
    progress2.update(60)  # Should cap at 50
    assert progress2.current == 50.0
    assert progress2.is_complete
    
    # Test negative/zero increments (should be ignored)
    progress3 = _ProgressBar(total=100)
    progress3.update(0)
    progress3.update(-10)
    assert progress3.current == 0.0
    
    print("✅ Atomic incrementation tests passed")


def test_direct_setting():
    """Test direct setting (special cases only)."""
    print("🧪 Testing direct setting...")
    
    progress = _ProgressBar(total=100)
    
    # Test basic setting
    progress.set_current(50, "Jumped to 50%")
    assert progress.current == 50.0
    assert progress.percentage == 50
    
    progress.set_current(75, "Jumped to 75%")
    assert progress.current == 75.0
    assert progress.percentage == 75
    
    # Test bounds protection
    progress.set_current(-10)  # Should clamp to 0
    assert progress.current == 0.0
    
    progress.set_current(150)  # Should clamp to total
    assert progress.current == 100.0
    assert progress.is_complete
    
    print("✅ Direct setting tests passed")


def test_formatting():
    """Test progress bar formatting."""
    print("🧪 Testing formatting...")
    
    progress = _ProgressBar(total=100)
    
    # Test color setting
    progress.set_color('green')
    assert progress._format_state is not None
    
    # Test format string
    progress.set_format('</red, bold>')
    assert progress._format_state is not None
    
    # Test invalid format
    try:
        progress.set_format('</invalid_command>')
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    # Test format reset
    progress.reset_format()
    assert progress._format_state is None
    
    print("✅ Formatting tests passed")


def test_multi_format_output():
    """Test multi-format output generation."""
    print("🧪 Testing multi-format output...")
    
    progress = _ProgressBar(total=100, show_rate=True)
    progress.update(50, "Processing...")
    
    # Test individual formats
    terminal_output = progress.get_output('terminal')
    assert '50%' in terminal_output
    assert 'Processing...' in terminal_output
    assert '[' in terminal_output  # Has brackets
    
    plain_output = progress.get_output('plain')
    assert '50%' in plain_output
    assert 'Processing...' in plain_output
    assert '#' in plain_output or '-' in plain_output  # ASCII chars
    
    html_output = progress.get_output('html')
    assert 'width: 50%' in html_output  # CSS width
    assert 'Processing...' in html_output
    assert '<div' in html_output
    
    # Test all formats at once
    all_outputs = progress.get_all_outputs()
    assert 'terminal' in all_outputs
    assert 'plain' in all_outputs
    assert 'html' in all_outputs
    
    # Test invalid format
    try:
        progress.get_output('invalid')
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    print("✅ Multi-format output tests passed")


def test_thread_safety():
    """Test thread safety of progress bar operations."""
    print("🧪 Testing thread safety...")
    
    progress = _ProgressBar(total=1000)
    results = []
    
    def worker(worker_id):
        """Worker function that updates progress."""
        for i in range(10):
            progress.update(1, f"Worker {worker_id} step {i}")
            results.append(progress.current)
            # Small delay removed to prevent test timeout
    
    # Start multiple threads
    threads = []
    for i in range(10):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify final result
    assert progress.current == 100.0  # 10 threads * 10 updates * 1 increment
    assert len(results) == 100  # All updates recorded
    
    print("✅ Thread safety tests passed")


def test_memory_management():
    """Test memory management and release functionality."""
    print("🧪 Testing memory management...")
    
    progress = _ProgressBar(total=100)
    progress.update(50, "Before release")
    
    # Test release
    progress.release()
    
    # Test that methods raise errors after release
    methods_to_test = [
        lambda: progress.update(10),
        lambda: progress.set_current(75),
        lambda: progress.set_color('red'),
        lambda: progress.set_format('</bold>'),
        lambda: progress.display(),
        lambda: progress.finish(),
        lambda: progress.get_output(),
        lambda: progress.copy(),
        lambda: progress.reset()
    ]
    
    for method in methods_to_test:
        try:
            method()
            assert False, f"Method should have raised RuntimeError after release"
        except RuntimeError as e:
            assert "released" in str(e).lower()
    
    # Test double release (should be safe)
    progress.release()  # Should not raise error
    
    print("✅ Memory management tests passed")


def test_context_manager():
    """Test context manager functionality."""
    print("🧪 Testing context manager...")
    
    # Test successful completion
    with _ProgressBar(total=50) as progress:
        assert progress.is_displayed
        progress.update(25, "Step 1")
        progress.update(25, "Step 2")
        assert progress.is_complete
    
    # Progress should be finished and released after context
    try:
        progress.update(10)
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass
    
    # Test with exception
    try:
        with _ProgressBar(total=100) as progress2:
            progress2.update(50)
            raise ValueError("Test exception")
    except ValueError:
        pass
    
    # Should still be released even with exception
    try:
        progress2.update(10)
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass
    
    print("✅ Context manager tests passed")


def test_utility_methods():
    """Test utility methods like copy, reset, etc."""
    print("🧪 Testing utility methods...")
    
    # Test copy
    original = _ProgressBar(total=100, width=50)
    original.update(30, "Original message")
    original.set_format('</green>')
    
    copy = original.copy()
    assert copy.total == original.total
    assert copy.current == original.current
    assert copy.width == original.width
    assert copy._message == original._message
    
    # Copies should be independent
    copy.update(20)
    assert copy.current == 50.0
    assert original.current == 30.0
    
    # Test reset
    progress = _ProgressBar(total=100)
    progress.update(50, "Before reset")
    progress.set_format('</red>')
    
    progress.reset()
    assert progress.current == 0.0
    assert progress._message == ""
    assert not progress.is_finished
    
    # Test string representations
    progress = _ProgressBar(total=100)
    progress.update(25)
    
    str_repr = str(progress)
    assert "25.0/100" in str_repr
    assert "25%" in str_repr
    
    detailed_repr = repr(progress)
    assert "_ProgressBar" in detailed_repr
    assert "current=25.0" in detailed_repr
    
    print("✅ Utility methods tests passed")


def visual_demo():
    """Visual demonstration of progress bar functionality."""
    print("\n" + "="*60)
    print("🎬 VISUAL PROGRESS BAR DEMONSTRATION")
    print("="*60)
    
    print("\n1️⃣ Basic Progress Bar:")
    progress1 = _ProgressBar(total=100, color='green')
    progress1.display()
    
    for i in range(5):
        time.sleep(0.3)
        progress1.update(20, f"Step {i+1} complete")
    
    progress1.finish("Basic demo complete!")
    time.sleep(0.5)
    
    print("\n2️⃣ Formatted Progress Bar with Rate:")
    progress2 = _ProgressBar(total=50, show_rate=True)
    progress2.set_format('</cyan, bold>')
    progress2.display()
    
    for i in range(10):
        time.sleep(0.2)
        progress2.update(5, f"Processing item {i+1}/10")
    
    progress2.finish("Formatted demo complete!")
    time.sleep(0.5)
    
    print("\n3️⃣ Context Manager Demo:")
    with _ProgressBar(total=30, color='yellow', width=40) as progress3:
        for i in range(6):
            time.sleep(0.25)
            progress3.update(5, f"Context step {i+1}")
    
    print("Context demo complete!")
    
    print("\n4️⃣ Multi-Format Output Demo:")
    progress4 = _ProgressBar(total=100)
    progress4.update(75, "Generating outputs...")
    
    outputs = progress4.get_all_outputs()
    print(f"Terminal: {outputs['terminal']}")
    print(f"Plain:    {outputs['plain']}")
    print(f"HTML:     {outputs['html'][:80]}...")
    
    progress4.release()
    
    print("\n" + "="*60)
    print("🎉 VISUAL DEMONSTRATION COMPLETE!")
    print("="*60)


def run_tests():
    """Run all progress bar tests."""
    print("🚀 Starting Progress Bar Tests")
    print("="*50)
    
    try:
        test_progress_bar_creation()
        test_atomic_incrementation()
        test_direct_setting()
        test_formatting()
        test_multi_format_output()
        test_thread_safety()
        test_memory_management()
        test_context_manager()
        test_utility_methods()
        
        print("\n" + "="*50)
        print("✅ ALL PROGRESS BAR TESTS PASSED!")
        print("="*50)
        
        # Skip visual demo in automated tests (causes timeout)
        # Run visual demo manually with: python3 test_progress_bar.py --visual
        if len(sys.argv) > 1 and '--visual' in sys.argv:
            visual_demo()
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)