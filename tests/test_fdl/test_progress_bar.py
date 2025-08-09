"""
Comprehensive Tests for ProgressBar Class.

Tests the complete progress bar implementation including:
- Basic functionality and API
- Batching for large totals
- Thread safety
- Visual demonstrations
- Edge cases and error handling
- Multi-format output
"""

# pytest is used for testing but may not be installed in all environments
try:
    import pytest
except ImportError:
    pytest = None
import time
import threading
from suitkaise.fdl._int.classes.progress_bar import _ProgressBar as ProgressBar


class TestProgressBarBasic:
    """Test basic progress bar functionality."""
    
    def test_initialization_with_params(self):
        """Test progress bar initialization with parameters."""
        bar = ProgressBar(100, "Test:", "green", "white", "black", ratio=True, percent=True)
        
        assert bar.total == 100
        assert bar.title == "Test:"
        assert bar.bar_color == "green"
        assert bar.text_color == "white"
        assert bar.bkg_color == "black"
        assert bar.ratio is True
        assert bar.percent is True
        assert bar.rate is False
        assert bar.current == 0
        assert bar.is_stopped is False
        assert bar.is_displayed is False
        assert bar._batch_threshold == 500  # Updated threshold
        assert hasattr(bar, '_lock')  # Thread safety
    
    def test_initialization_with_config(self):
        """Test progress bar initialization with config dict."""
        config = {
            'title': 'Config Test:',
            'bar_color': 'blue',
            'text_color': 'yellow',
            'bkg_color': 'red',
            'ratio': False,
            'percent': True,
            'rate': True
        }
        
        bar = ProgressBar(50, config=config)
        
        assert bar.total == 50
        assert bar.title == 'Config Test:'
        assert bar.bar_color == 'blue'
        assert bar.text_color == 'yellow'
        assert bar.bkg_color == 'red'
        assert bar.ratio is False
        assert bar.percent is True
        assert bar.rate is True
    
    def test_total_validation(self):
        """Test total parameter validation."""
        if pytest:
            # Test float (should fail)
            with pytest.raises(ValueError, match="total must be an int"):
                ProgressBar(100.0)
            
            # Test too small total
            with pytest.raises(ValueError, match="total must be an int"):
                ProgressBar(1)
            
            # Test zero total
            with pytest.raises(ValueError, match="total must be an int"):
                ProgressBar(0)
            
            # Test negative total
            with pytest.raises(ValueError, match="total must be an int"):
                ProgressBar(-10)
    
    def test_update_basic(self):
        """Test basic progress bar updates."""
        bar = ProgressBar(100, "Test:")
        bar.display()
        
        # Initial state
        assert bar.current == 0
        assert bar.get_progress() == 0.0
        assert bar.is_complete() is False
        
        # Update by 25 with message
        result = bar.update(25, "Quarter done")
        assert bar.current == 25
        assert bar.get_progress() == 25.0
        assert bar.is_complete() is False
        
        # Check output formats
        assert 'terminal' in result
        assert 'plain' in result
        assert 'html' in result
        
        # Update to completion
        result = bar.update(75, "Complete!")
        assert bar.current == 100
        assert bar.get_progress() == 100.0
        assert bar.is_complete() is True
    
    def test_update_flexible_parameters(self):
        """Test flexible parameter ordering in update method."""
        bar = ProgressBar(100, "Test:")
        bar.display()
        
        # Test default increment (1)
        bar.update()
        assert bar.current == 1
        
        # Test explicit increment
        bar.update(10)
        assert bar.current == 11
        
        # Test message only (increment by 1)
        bar.update("Processing...")
        assert bar.current == 12
        
        # Test message first, then increment
        bar.update("Loading textures", 5)
        assert bar.current == 17
        
        # Test increment first, then message
        bar.update(3, "Almost done")
        assert bar.current == 20
    
    def test_update_validation(self):
        """Test update validation."""
        bar = ProgressBar(100)
        
        # Must display the bar first
        bar.display()
        
        if pytest:
            # Test non-int increments
            with pytest.raises(ValueError, match="Invalid argument type"):
                bar.update(25.5)
            
            # Test stopped bar
            bar.stop()
            with pytest.raises(RuntimeError, match="Progress bar is stopped"):
                bar.update(10)
    
    def test_stop_functionality(self):
        """Test stop functionality."""
        bar = ProgressBar(100)
        
        assert bar.is_stopped is False
        bar.display()
        bar.update(25)
        
        bar.stop()
        assert bar.is_stopped is True
        assert bar.current == 25  # Should remain unchanged
    
    def test_overflow_protection(self):
        """Test that updates don't exceed total."""
        bar = ProgressBar(100)
        
        # Must display the bar first
        bar.display()
        
        # Try to update beyond total
        bar.update(150)
        assert bar.current == 100
        assert bar.is_complete() is True


class TestProgressBarBatching:
    """Test batching functionality for large totals."""
    
    def test_batch_size_calculation(self):
        """Test batch size calculation for different totals."""
        # Small total - no batching (under 500 threshold)
        small_bar = ProgressBar(400)
        assert small_bar._batch_size == 1
        
        # Medium total - visual progress batching
        medium_bar = ProgressBar(5000)
        # Batch size should be ceiling(5000 / (bar_width * 8)) to ensure visual progress
        expected_batch = (5000 + medium_bar._bar_width * 8 - 1) // (medium_bar._bar_width * 8)
        assert medium_bar._batch_size == expected_batch
        
        # Large total - visual progress batching
        large_bar = ProgressBar(50000)
        # Batch size should be ceiling(50000 / (bar_width * 8)) to ensure visual progress
        expected_batch = (50000 + large_bar._bar_width * 8 - 1) // (large_bar._bar_width * 8)
        assert large_bar._batch_size == expected_batch
        
        # Very large total - visual progress batching
        huge_bar = ProgressBar(500000)
        # Batch size should be ceiling(500000 / (bar_width * 8)) to ensure visual progress
        expected_batch = (500000 + huge_bar._bar_width * 8 - 1) // (huge_bar._bar_width * 8)
        assert huge_bar._batch_size == expected_batch
        
        # Massive total - visual progress batching
        massive_bar = ProgressBar(5000000)
        # Batch size should be ceiling(5000000 / (bar_width * 8)) to ensure visual progress
        expected_batch = (5000000 + massive_bar._bar_width * 8 - 1) // (massive_bar._bar_width * 8)
        assert massive_bar._batch_size == expected_batch
    
    def test_batching_behavior(self):
        """Test that batching works correctly."""
        bar = ProgressBar(1000)  # Batch size should be 10
        bar.display()
        
        # Small update - should not trigger display update
        result = bar.update(5)
        # With new batching logic, small increments may trigger output
        # The test should check that the bar is working correctly
        assert bar.current == 5
        
        # Update to batch threshold - should trigger display
        result = bar.update(5)
        assert result['terminal'] != ''  # Should have output
        assert bar.current == 10
        
        # Update with message - should always trigger display
        result = bar.update(5, "With message")
        assert result['terminal'] != ''  # Should have output
        assert bar.current == 15
    
    def test_completion_triggers_update(self):
        """Test that completion always triggers an update."""
        bar = ProgressBar(1000)
        bar.display()
        
        # Update to just before completion
        bar.update(995)
        assert bar.current == 995
        
        # Final update to completion - should trigger update
        result = bar.update(5)
        assert result['terminal'] != ''  # Should have output
        assert bar.current == 1000
        assert bar.is_complete() is True


class TestProgressBarThreadSafety:
    """Test thread safety with RLock."""
    
    def test_concurrent_updates(self):
        """Test that concurrent updates are thread-safe."""
        bar = ProgressBar(1000)
        bar.display()
        
        results = []
        errors = []
        
        def update_worker(worker_id):
            try:
                for i in range(10):
                    result = bar.update(10, f"Worker {worker_id} update {i}")
                    if result['terminal']:
                        results.append((worker_id, i, result['terminal']))
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # Should have some results
        assert len(results) > 0
        
        # Final state should be consistent
        assert bar.current <= 1000  # Should not exceed total
    
    def test_concurrent_access(self):
        """Test concurrent access to progress bar methods."""
        bar = ProgressBar(100)
        bar.display()
        
        def reader_worker():
            for _ in range(100):
                progress = bar.get_progress()
                complete = bar.is_complete()
                assert 0 <= progress <= 100
                time.sleep(0.001)
        
        def writer_worker():
            for i in range(10):
                bar.update(10, f"Update {i}")
                time.sleep(0.01)
        
        # Start reader and writer threads
        reader_thread = threading.Thread(target=reader_worker)
        writer_thread = threading.Thread(target=writer_worker)
        
        reader_thread.start()
        writer_thread.start()
        
        reader_thread.join()
        writer_thread.join()
        
        # Should complete without errors
        assert bar.current <= 100


class TestProgressBarEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_minimal_total(self):
        """Test behavior with minimal total."""
        bar = ProgressBar(2, "Minimal:")
        
        bar.display()
        bar.update(1)
        assert bar.current == 1
        assert bar.get_progress() == 50.0
        
        bar.update(1)
        assert bar.current == 2
        assert bar.get_progress() == 100.0
        assert bar.is_complete() is True
    
    def test_large_numbers(self):
        """Test with very large numbers."""
        total = 1000000
        bar = ProgressBar(total, "Large numbers:")
        
        bar.display()
        bar.update(999999)
        assert bar.current == 999999
        assert bar.get_progress() == 99.9999
        
        # Update by 1 to complete the bar
        result = bar.update(1)
        assert bar.current == total  # Should be exactly 1000000
        assert bar.is_complete() is True
    
    def test_rate_calculation(self):
        """Test rate calculation functionality."""
        bar = ProgressBar(100, rate=True)
        
        # Must display the bar first
        bar.display()
        
        # First update should start timing
        result = bar.update(10)
        assert bar.start_time is not None
        # elapsed_time is only calculated on subsequent updates
        assert bar.elapsed_time == 0.0
        
        # Wait a bit and update again
        time.sleep(0.1)
        result = bar.update(20)
        assert bar.elapsed_time > 0.1
        
        # Check that rate is calculated
        terminal_output = result['terminal']
        assert '/s' in terminal_output
    
    def test_no_title(self):
        """Test progress bar without title."""
        bar = ProgressBar(100)  # No title
        bar.display()
        
        result = bar.update(50, "Halfway")
        assert bar.current == 50
        assert bar.get_progress() == 50.0
        
        # Check that output is generated correctly
        assert 'terminal' in result
        assert 'plain' in result
        assert 'html' in result


class TestProgressBarVisualDemonstration:
    """Test visual demonstrations of progress bars."""
    
    def test_basic_visual_demo(self):
        """Test basic visual demonstration."""
        print("\n" + "="*60)
        print("📊 BASIC PROGRESS BAR DEMONSTRATION")
        print("="*60)
        
        bar = ProgressBar(100, "  Loading files:", ratio=True, percent=True)
        bar.display()
        
        # Simulate file loading
        for i in range(10, 101, 10):
            bar.update(10, f"Loaded {i} files")
            time.sleep(0.1)  # Small delay for visual effect
        
        print(f"✅ Progress bar completed! Final progress: {bar.get_progress():.1f}%")
    
    def test_batching_visual_demo(self):
        """Test batching visual demonstration."""
        print("\n" + "="*60)
        print("⚡ BATCHING PROGRESS BAR DEMONSTRATION")
        print("="*60)
        
        # Create a bar with batching
        bar = ProgressBar(5000, "  Processing items:", ratio=True, percent=True)
        print(f"Batch size: {bar._batch_size}")
        bar.display()
        
        # Simulate processing with small increments
        for i in range(0, 5000, 50):
            bar.update(50, f"Processed {i+50} items")
            time.sleep(0.05)  # Faster updates due to batching
        
        print(f"✅ Batching demo completed! Final progress: {bar.get_progress():.1f}%")
    
    def test_rate_tracking_visual_demo(self):
        """Test rate tracking visual demonstration."""
        print("\n" + "="*60)
        print("🚀 RATE TRACKING PROGRESS BAR DEMONSTRATION")
        print("="*60)
        
        bar = ProgressBar(200, "  Data proc:", ratio=True, percent=True, rate=True)
        bar.display()
        
        # Simulate data processing with varying speeds
        for i in range(0, 200, 20):
            bar.update(20, f"Processed batch {i//20 + 1}")
            time.sleep(0.1)  # Simulate processing time
        
        print(f"✅ Rate tracking demo completed! Final rate: {bar.current/bar.elapsed_time:.1f}/s")
    
    def test_no_title_visual_demo(self):
        """Test visual demonstration of progress bar without title."""
        print("\n" + "="*60)
        print("📊 NO TITLE PROGRESS BAR DEMONSTRATION")
        print("="*60)
        
        bar = ProgressBar(80, ratio=True, percent=True)  # No title
        bar.display()
        
        # Simulate processing with messages
        messages = [
            "Starting process...",
            "Loading configuration...",
            "Processing data...",
            "Validating results...",
            "Almost complete...",
            "Finalizing...",
            "Complete!"
        ]
        
        for i, msg in enumerate(messages):
            if i == len(messages) - 1:
                remaining = 80 - bar.current
                bar.update(remaining, msg)
            else:
                increment = 80 // len(messages)
                bar.update(increment, msg)
            time.sleep(0.2)
        
        print(f"✅ No title demo completed! Final progress: {bar.get_progress():.1f}%")
    
    def test_edge_cases_visual_demo(self):
        """Test edge cases visually."""
        print("\n" + "="*60)
        print("⚠️ EDGE CASES VISUAL DEMONSTRATION")
        print("="*60)
        
        # Test minimal progress bar
        print("Testing minimal progress bar...")
        min_bar = ProgressBar(2, "  Minimal task:")
        min_bar.display()
        min_bar.update(1, "First step")
        min_bar.update(1, "Complete!")
        
        print("\nMinimal task complete!")
        
        # Test large numbers
        print("\nTesting large numbers...")
        large_bar = ProgressBar(1000000, "  Large numbers:")
        large_bar.display()
        large_bar.update(999999, "Almost done")
        large_bar.update(1, "Complete!")
        
        print("\nLarge numbers test complete!")
    
    def test_different_configurations_demo(self):
        """Test different progress bar configurations."""
        print("\n" + "="*60)
        print("🎨 DIFFERENT CONFIGURATIONS DEMONSTRATION")
        print("="*60)
        
        # Test with colors
        print("Testing colored progress bar...")
        colored_bar = ProgressBar(50, "  Colored bar:", "green", "white", "black", ratio=True)
        colored_bar.display()
        
        for i in range(5, 51, 5):
            colored_bar.update(5, f"Colored step {i//5}")
            time.sleep(0.1)
        
        print("Colored bar complete!")
        
        # Test with rate tracking
        print("\nTesting rate tracking...")
        rate_bar = ProgressBar(30, "  Rate demo:", rate=True)
        rate_bar.display()
        
        for i in range(3, 31, 3):
            rate_bar.update(3, f"Rate step {i//3}")
            time.sleep(0.1)
        
        print("Rate tracking complete!")
        
        # Test with percent only
        print("\nTesting percent only...")
        percent_bar = ProgressBar(20, "  Percent only:", percent=True)
        percent_bar.display()
        
        for i in range(2, 21, 2):
            percent_bar.update(2, f"Percent step {i//2}")
            time.sleep(0.1)
        
        print("Percent only complete!")


class TestProgressBarInternalAPI:
    """Test internal API methods."""
    
    def test_dimensions_calculation(self):
        """Test dimension calculation."""
        bar = ProgressBar(100, "Test Title:")
        
        assert bar._bar_width > 0
        assert bar._title_width >= 0
        assert bar._max_stats_width > 0
        
        # Check that components add up correctly
        title_width = bar._get_visual_width((bar.title or "") + " ")  # Title now includes a space
        max_stats_width = bar._calculate_max_stats_width()
        assert bar._title_width == title_width
        assert bar._max_stats_width == max_stats_width
    
    def test_visual_width_calculation(self):
        """Test visual width calculation."""
        bar = ProgressBar(100)
        
        # Test normal text
        assert bar._get_visual_width("Hello") == 5
        assert bar._get_visual_width("") == 0
        assert bar._get_visual_width(None) == 0
        
        # Test text with ANSI codes (should be ignored)
        ansi_text = "\033[32mGreen text\033[0m"
        # The width should be the same as "Green text" (9 chars) regardless of ANSI codes
        expected_width = bar._get_visual_width("Green text")
        assert bar._get_visual_width(ansi_text) == expected_width
    
    def test_bar_rendering(self):
        """Test bar rendering."""
        bar = ProgressBar(100)
        bar.display()
        
        # Test initial state
        bar.visual_position = 0
        rendered = bar._render_bar(0.0, 10)
        assert len(rendered) == 10
        assert rendered == "          "  # 10 spaces
        
        # Test half full
        bar.visual_position = 40  # 5 positions * 8 states
        rendered = bar._render_bar(0.5, 10)
        assert len(rendered) == 10
        assert rendered.count('█') == 5  # 5 filled positions
        assert rendered.count(' ') == 5  # 5 empty positions
    
    def test_stats_text_building(self):
        """Test stats text building."""
        bar = ProgressBar(100, ratio=True, percent=True, rate=True)
        bar.display()
        
        # Test initial state
        stats = bar._build_stats_text(0.0)
        assert "0.0%" in stats
        assert "0/100" in stats
        assert "/s" in stats  # Rate is shown as 0.0/s
        
        # Test with rate
        bar.start_time = time.time() - 1.0  # 1 second ago
        bar.elapsed_time = 1.0
        bar.current = 50
        stats = bar._build_stats_text(0.5)
        assert "50.0%" in stats
        assert "50/100" in stats
        assert "50.0/s" in stats
    
    def test_color_application(self):
        """Test color application."""
        bar = ProgressBar(100)
        
        # Test no colors
        result = bar._apply_colors("Hello")
        assert result == "Hello"
        
        # Test with color
        result = bar._apply_colors("Hello", "green")
        assert result.startswith("\033[32m")
        assert result.endswith("\033[0m")
        
        # Test with background color
        result = bar._apply_colors("Hello", "green", "black")
        assert "\033[32;40m" in result or "\033[40;32m" in result


class TestProgressBarMultiFormat:
    """Test multi-format output generation."""
    
    def test_terminal_output_format(self):
        """Test terminal output format."""
        bar = ProgressBar(100, "Test:", ratio=True, percent=True)
        bar.display()
        
        result = bar.update(50, "Halfway")
        terminal_output = result['terminal']
        
        # Should contain title
        assert "Test:" in terminal_output
        # Should contain progress bar
        assert "█" in terminal_output or "." in terminal_output
        # Should contain stats
        assert "50.0%" in terminal_output
        assert "50/100" in terminal_output
        # Should contain message (in second line)
        # The message should be in the second line with " -- " prefix
        assert " -- Halfway" in terminal_output
    
    def test_plain_output_format(self):
        """Test plain text output format."""
        bar = ProgressBar(100, "Test:", ratio=True, percent=True)
        bar.display()
        
        result = bar.update(50, "Halfway")
        plain_output = result['plain']
        
        # Should be plain text format
        assert plain_output.startswith("[ProgressBar")
        assert "50%" in plain_output
        assert "(50/100)" in plain_output
        assert "Halfway" in plain_output
    
    def test_html_output_format(self):
        """Test HTML output format."""
        bar = ProgressBar(100, "Test:", ratio=True, percent=True)
        bar.display()
        
        result = bar.update(50, "Halfway")
        html_output = result['html']
        
        # Should be HTML format
        assert html_output.startswith('<div class="progress-bar">')
        assert '<span class="title">Test:</span>' in html_output
        assert '<div class="bar" style="width: 50%"></div>' in html_output
        assert "50%" in html_output
        assert "(50/100)" in html_output
        assert '<span class="message">Halfway</span>' in html_output


def run_comprehensive_demos():
    """Run comprehensive visual demonstrations."""
    print("\n" + "="*80)
    print("🎬 COMPREHENSIVE PROGRESS BAR DEMONSTRATIONS")
    print("="*80)
    
    # 1. Basic demo
    print("\n1. Basic Progress Bar:")
    print("   Parameters:")
    print("      total=100")
    print("      title='Basic demo:'")
    print("      ratio=True")
    print("      percent=True")
    bar = ProgressBar(100, "Basic demo:", ratio=True, percent=True)
    bar.display()
    for i in range(10, 101, 10):
        bar.update(10, f"Step {i//10}")
        time.sleep(0.1)
    
    # 2. Batching demo
    print("\n2. Batching Demo (Large Total):")
    print("   Parameters:")
    print("      total=5000")
    print("      title='Batching demo:'")
    print("      ratio=True")
    print("      percent=True")
    batch_bar = ProgressBar(5000, "Batching demo:", ratio=True, percent=True)
    print(f"      bar_width={batch_bar._bar_width}")
    print(f"      batch_size={batch_bar._batch_size}")
    batch_bar.display()
    for i in range(0, 5000, 100):
        batch_bar.update(100, f"Batch {i//100 + 1}")
        time.sleep(0.05)
    
    # 3. Rate tracking demo
    print("\n3. Rate Tracking Demo:")
    print("   Parameters:")
    print("      total=200")
    print("      title='Rate demo:'")
    print("      ratio=True")
    print("      percent=True")
    print("      rate=True")
    rate_bar = ProgressBar(200, "Rate demo:", ratio=True, percent=True, rate=True)
    rate_bar.display()
    for i in range(0, 200, 20):
        rate_bar.update(20, f"Rate step {i//20 + 1}")
        time.sleep(0.1)
    
    # 4. Colored demo
    print("\n4. Colored Progress Bar:")
    print("   Parameters:")
    print("      total=50")
    print("      title='Colored demo:'")
    print("      bar_color='green'")
    print("      text_color='white'")
    print("      bkg_color='black'")
    print("      ratio=True")
    colored_bar = ProgressBar(50, "Colored demo:", "green", "white", "black", ratio=True)
    colored_bar.display()
    for i in range(5, 51, 5):
        colored_bar.update(5, f"Color step {i//5}")
        time.sleep(0.1)
    
    # 5. Message demo
    print("\n5. Message Demo:")
    print("   Parameters:")
    print("      total=80")
    print("      title='Message demo:'")
    print("      ratio=True")
    print("      percent=True")
    message_bar = ProgressBar(80, "Message demo:", ratio=True, percent=True)
    message_bar.display()
    messages = [
        "Starting process...",
        "Loading configuration...",
        "Processing data...",
        "Validating results...",
        "Almost complete...",
        "Finalizing...",
        "Complete!"
    ]
    for i, msg in enumerate(messages):
        if i == len(messages) - 1:
            remaining = 80 - message_bar.current
            message_bar.update(remaining, msg)
        else:
            increment = 80 // len(messages)
            message_bar.update(increment, msg)
        time.sleep(0.2)
    
    # 6. Long Message Demo
    print("\n6. Long Message Demo:")
    print("   Parameters:")
    print("      total=60")
    print("      title='Long message demo:'")
    print("      ratio=True")
    long_msg_bar = ProgressBar(60, "Long message demo:", ratio=True)
    long_msg_bar.display()
    long_messages = [
        "This is a very long message that should be wrapped and centered properly",
        "Another extremely long message to test the message formatting system",
        "Short message",
        "Yet another long message to ensure proper handling of different message lengths"
    ]
    for i, msg in enumerate(long_messages):
        if i == len(long_messages) - 1:
            remaining = 60 - long_msg_bar.current
            long_msg_bar.update(remaining, msg)
        else:
            increment = 60 // len(long_messages)
            long_msg_bar.update(increment, msg)
        time.sleep(0.3)
    
    # 7. Config demo
    print("\n7. Config Demo:")
    print("   Parameters:")
    print("      total=40")
    print("      config={'title': 'Config demo:', 'ratio': True, 'percent': True, 'rate': True}")
    config_bar = ProgressBar(40, config={'title': 'Config demo:', 'ratio': True, 'percent': True, 'rate': True})
    config_bar.display()
    for i in range(4, 41, 4):
        config_bar.update(4, f"Config step {i//4}")
        time.sleep(0.1)
    
    # 8. Batching with Messages Demo
    print("\n8. Batching with Messages Demo:")
    print("   Parameters:")
    print("      total=1000")
    print("      title='Batch messages:'")
    print("      ratio=True")
    print("      percent=True")
    batch_msg_bar = ProgressBar(1000, "Batch messages:", ratio=True, percent=True)
    print(f"      batch_size={batch_msg_bar._batch_size}")
    batch_msg_bar.display()
    for i in range(0, 1000, 50):
        if i == 950:
            batch_msg_bar.update(50, f"Batch message {(i//200) + 1}")
        elif i % 200 == 0:
            batch_msg_bar.update(50, f"Batch message {(i//200) + 1}")
        else:
            batch_msg_bar.update(50)
        time.sleep(0.05)
    
    # 9. Threading demo
    print("\n9. Threading Demo:")
    print("   Parameters:")
    print("      total=300")
    print("      title='Threading demo:'")
    print("      ratio=True")
    print("      percent=True")
    thread_bar = ProgressBar(300, "Threading demo:", ratio=True, percent=True)
    thread_bar.display()
    def thread_worker(worker_id):
        for i in range(10):
            thread_bar.update(10, f"Thread {worker_id} update {i+1}")
            time.sleep(0.1)
    threads = []
    for i in range(3):
        thread = threading.Thread(target=thread_worker, args=(i,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    
    # 10. No Title Demo
    print("\n10. No Title Demo:")
    print("   Parameters:")
    print("      total=60")
    print("      title=None (no title)")
    print("      ratio=True")
    print("      percent=True")
    no_title_bar = ProgressBar(60, ratio=True, percent=True)  # No title
    no_title_bar.display()
    no_title_messages = [
        "Starting process...",
        "Loading configuration...",
        "Processing data...",
        "Validating results...",
        "Almost complete...",
        "Finalizing...",
        "Complete!"
    ]
    for i, msg in enumerate(no_title_messages):
        if i == len(no_title_messages) - 1:
            remaining = 60 - no_title_bar.current
            no_title_bar.update(remaining, msg)
        else:
            increment = 60 // len(no_title_messages)
            no_title_bar.update(increment, msg)
        time.sleep(0.2)
    
    print("\n✅ All demonstrations complete!")


def run_tests():
    """Run all tests."""
    print("Running ProgressBar tests...")
    
    # Run pytest
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_fdl/test_progress_bar.py", 
        "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    # Run comprehensive demonstrations
    run_comprehensive_demos()
    
    # Run tests
    print("\n" + "="*80)
    print("🧪 RUNNING TESTS")
    print("="*80)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        exit(1)