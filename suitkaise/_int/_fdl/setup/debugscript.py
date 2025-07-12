"""
Test script to verify that terminal detection and unicode support are properly cached
and not causing performance issues in your setup.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Import your terminal detection and unicode support
try:
    from suitkaise._int._fdl.setup.terminal import _terminal, _refresh_terminal_info
    from suitkaise._int._fdl.setup.unicode import _get_unicode_support, _get_capabilities
    MODULES_AVAILABLE = True
except ImportError:
    print("Could not import suitkaise modules - they may not be on the path yet")
    MODULES_AVAILABLE = False

def test_terminal_caching():
    """Test that terminal detection is properly cached."""
    print("Testing Terminal Detection Caching...")
    print("=" * 50)
    
    if not MODULES_AVAILABLE:
        print("❌ Cannot test - modules not available")
        return
    
    # Test multiple accesses to terminal properties
    iterations = 100
    
    # Time repeated access to terminal properties
    start_time = time.time()
    for _ in range(iterations):
        width = _terminal.width
        height = _terminal.height
        supports_color = _terminal.supports_color
        is_tty = _terminal.is_tty
        encoding = _terminal.encoding
    end_time = time.time()
    
    cached_time = end_time - start_time
    print(f"✅ {iterations} cached terminal property accesses: {cached_time:.6f}s")
    print(f"   Average per access: {(cached_time/iterations)*1000:.3f}ms")
    
    # Test if fresh detection is much slower (indicating caching is working)
    start_time = time.time()
    for _ in range(10):  # Fewer iterations since this should be slower
        _refresh_terminal_info()  # Force re-detection
        width = _terminal.width
    end_time = time.time()
    
    fresh_time = end_time - start_time
    print(f"✅ 10 fresh terminal detections: {fresh_time:.6f}s")
    print(f"   Average per detection: {(fresh_time/10)*1000:.3f}ms")
    
    if fresh_time > cached_time:
        speedup = fresh_time / cached_time * (iterations / 10)
        print(f"🎯 Caching provides {speedup:.1f}x speedup - GOOD!")
    else:
        print("⚠️  Caching may not be working properly")

def test_unicode_caching():
    """Test that unicode support detection is properly cached."""
    print("\nTesting Unicode Support Caching...")
    print("=" * 50)
    
    if not MODULES_AVAILABLE:
        print("❌ Cannot test - modules not available")
        return
    
    # Test multiple accesses to unicode properties
    iterations = 100
    
    start_time = time.time()
    for _ in range(iterations):
        unicode_support = _get_unicode_support()
        box_support = unicode_support.supports_box_drawing
        spinner_support = unicode_support.supports_unicode_spinners
        progress_support = unicode_support.supports_progress_blocks
        capabilities = _get_capabilities()
    end_time = time.time()
    
    cached_time = end_time - start_time
    print(f"✅ {iterations} cached unicode property accesses: {cached_time:.6f}s")
    print(f"   Average per access: {(cached_time/iterations)*1000:.3f}ms")
    
    # Show what capabilities were detected
    if capabilities:
        print(f"📊 Detected capabilities: {capabilities}")

def test_thread_safety():
    """Test that caching works correctly across multiple threads."""
    print("\nTesting Thread Safety...")
    print("=" * 50)
    
    if not MODULES_AVAILABLE:
        print("❌ Cannot test - modules not available")
        return
    
    results = []
    errors = []
    
    def worker_thread(thread_id):
        """Worker function that accesses terminal/unicode properties."""
        try:
            # Access terminal properties
            width = _terminal.width
            height = _terminal.height
            
            # Access unicode properties  
            unicode_support = _get_unicode_support()
            box_support = unicode_support.supports_box_drawing
            
            results.append({
                'thread_id': thread_id,
                'width': width,
                'height': height,
                'box_support': box_support
            })
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")
    
    # Run multiple threads
    num_threads = 10
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
        for future in futures:
            future.result()  # Wait for completion
    
    end_time = time.time()
    
    print(f"✅ {num_threads} threads completed in {end_time - start_time:.6f}s")
    
    if errors:
        print(f"❌ Errors encountered: {errors}")
    else:
        print("✅ No errors in multithreaded access")
    
    # Check that all threads got consistent results
    if results:
        first_result = results[0]
        consistent = all(
            r['width'] == first_result['width'] and
            r['height'] == first_result['height'] and
            r['box_support'] == first_result['box_support']
            for r in results
        )
        
        if consistent:
            print("✅ All threads got consistent results - caching is thread-safe")
        else:
            print("⚠️  Inconsistent results across threads")
            for r in results:
                print(f"   Thread {r['thread_id']}: width={r['width']}, box={r['box_support']}")

def test_performance_vs_rich():
    """Compare performance of your caching vs Rich's detection."""
    print("\nComparing Performance vs Rich...")
    print("=" * 50)
    
    if not MODULES_AVAILABLE:
        print("❌ Cannot test - modules not available")
        return
    
    try:
        from rich.console import Console
        
        # Test your cached approach
        iterations = 50
        start_time = time.time()
        for _ in range(iterations):
            width = _terminal.width
            unicode_support = _get_unicode_support()
            box_support = unicode_support.supports_box_drawing
        end_time = time.time()
        
        your_time = end_time - start_time
        
        # Test Rich's approach (creates new console each time)
        start_time = time.time()
        for _ in range(iterations):
            console = Console()
            width = console.size.width
            # Rich doesn't expose unicode detection directly, so just measure console creation
        end_time = time.time()
        
        rich_time = end_time - start_time
        
        print(f"✅ Your cached approach: {your_time:.6f}s ({(your_time/iterations)*1000:.3f}ms avg)")
        print(f"✅ Rich console creation: {rich_time:.6f}s ({(rich_time/iterations)*1000:.3f}ms avg)")
        
        if your_time < rich_time:
            speedup = rich_time / your_time
            print(f"🎯 Your approach is {speedup:.1f}x faster - EXCELLENT!")
        else:
            print("⚠️  Rich might be more optimized than expected")
            
    except ImportError:
        print("Rich not available for comparison")

def run_all_tests():
    """Run all caching verification tests."""
    print("SUITKAISE TERMINAL & UNICODE CACHING VERIFICATION")
    print("=" * 60)
    
    test_terminal_caching()
    test_unicode_caching() 
    test_thread_safety()
    test_performance_vs_rich()
    
    print("\n" + "=" * 60)
    print("CACHING VERIFICATION COMPLETE")
    print("=" * 60)
    
    if MODULES_AVAILABLE:
        print("\n📋 SUMMARY:")
        print("- Terminal detection should show significant caching speedup")
        print("- Unicode detection should be very fast on repeated access")
        print("- Thread safety should show consistent results across threads")
        print("- Performance should be competitive with or better than Rich")
        print("\nIf any tests show warnings, your caching may need optimization!")
    else:
        print("\n⚠️  Could not run tests - ensure suitkaise modules are importable")

if __name__ == "__main__":
    run_all_tests()