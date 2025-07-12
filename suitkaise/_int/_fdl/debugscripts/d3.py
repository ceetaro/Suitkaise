"""
Test to verify if Rich's Panel, Style, and Theme components really have minimal overhead.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

def test_rich_panel_overhead():
    """Test Panel creation and rendering overhead."""
    print("TESTING RICH PANEL OVERHEAD")
    print("=" * 40)
    
    try:
        from rich.panel import Panel
        from rich.console import Console
        
        console = Console()
        iterations = 1000
        
        # Test 1: Panel creation overhead
        start_time = time.time()
        for i in range(iterations):
            panel = Panel(f"Message {i}", title="Test", border_style="blue")
        end_time = time.time()
        
        creation_time = end_time - start_time
        print(f"✅ Panel creation x{iterations}: {creation_time:.6f}s")
        print(f"   Average per panel: {(creation_time/iterations)*1000:.3f}ms")
        
        # Test 2: Panel rendering overhead  
        panels = [Panel(f"Message {i}", title="Test") for i in range(100)]
        
        start_time = time.time()
        for panel in panels:
            with console.capture() as capture:
                console.print(panel)
            result = capture.get()
        end_time = time.time()
        
        render_time = end_time - start_time
        print(f"✅ Panel rendering x100: {render_time:.6f}s")
        print(f"   Average per render: {(render_time/100)*1000:.3f}ms")
        
        # Test 3: Compare with simple string formatting
        start_time = time.time()
        for i in range(iterations):
            # Simple box with ASCII
            content = f"Message {i}"
            box_width = len(content) + 4
            simple_box = f"+{'-' * (box_width-2)}+\n| {content} |\n+{'-' * (box_width-2)}+"
        end_time = time.time()
        
        simple_time = end_time - start_time
        print(f"✅ Simple ASCII box x{iterations}: {simple_time:.6f}s")
        print(f"   Average per box: {(simple_time/iterations)*1000:.3f}ms")
        
        # Compare overhead
        overhead_ratio = creation_time / simple_time
        print(f"\n📊 Rich Panel is {overhead_ratio:.1f}x slower than simple ASCII")
        
        if overhead_ratio > 5:
            print("⚠️  Rich Panel has significant overhead!")
        elif overhead_ratio > 2:
            print("⚠️  Rich Panel has moderate overhead")
        else:
            print("✅ Rich Panel overhead is acceptable")
            
    except ImportError:
        print("❌ Rich not available for testing")

def test_rich_style_overhead():
    """Test Style creation and application overhead."""
    print("\nTESTING RICH STYLE OVERHEAD")
    print("=" * 40)
    
    try:
        from rich.style import Style
        from rich.text import Text
        from rich.console import Console
        
        console = Console()
        iterations = 1000
        
        # Test 1: Style creation overhead
        start_time = time.time()
        for i in range(iterations):
            style = Style(color="red", bold=True, italic=True)
        end_time = time.time()
        
        style_creation_time = end_time - start_time
        print(f"✅ Style creation x{iterations}: {style_creation_time:.6f}s")
        print(f"   Average per style: {(style_creation_time/iterations)*1000:.3f}ms")
        
        # Test 2: Style application overhead
        style = Style(color="red", bold=True)
        texts = [Text(f"Message {i}", style=style) for i in range(100)]
        
        start_time = time.time()
        for text in texts:
            with console.capture() as capture:
                console.print(text)
            result = capture.get()
        end_time = time.time()
        
        style_render_time = end_time - start_time
        print(f"✅ Styled text rendering x100: {style_render_time:.6f}s")
        print(f"   Average per render: {(style_render_time/100)*1000:.3f}ms")
        
        # Test 3: Compare with ANSI codes directly
        start_time = time.time()
        for i in range(iterations):
            # Direct ANSI escape codes
            ansi_text = f"\033[31;1mMessage {i}\033[0m"  # Red + bold
        end_time = time.time()
        
        ansi_time = end_time - start_time
        print(f"✅ Direct ANSI codes x{iterations}: {ansi_time:.6f}s")
        print(f"   Average per ANSI: {(ansi_time/iterations)*1000:.3f}ms")
        
        # Compare overhead
        overhead_ratio = style_creation_time / ansi_time
        print(f"\n📊 Rich Style is {overhead_ratio:.1f}x slower than direct ANSI")
        
        if overhead_ratio > 10:
            print("⚠️  Rich Style has significant overhead!")
        elif overhead_ratio > 3:
            print("⚠️  Rich Style has moderate overhead")
        else:
            print("✅ Rich Style overhead is acceptable")
            
    except ImportError:
        print("❌ Rich not available for testing")

def test_rich_theme_overhead():
    """Test Theme creation and lookup overhead."""
    print("\nTESTING RICH THEME OVERHEAD")
    print("=" * 40)
    
    try:
        from rich.theme import Theme
        from rich.console import Console
        
        # Test 1: Theme creation overhead
        iterations = 1000
        
        start_time = time.time()
        for i in range(iterations):
            theme = Theme({
                "info": "cyan",
                "warning": "yellow", 
                "error": "red bold",
                "success": "green"
            })
        end_time = time.time()
        
        theme_creation_time = end_time - start_time
        print(f"✅ Theme creation x{iterations}: {theme_creation_time:.6f}s")
        print(f"   Average per theme: {(theme_creation_time/iterations)*1000:.3f}ms")
        
        # Test 2: Theme lookup overhead
        theme = Theme({"info": "cyan", "warning": "yellow", "error": "red bold"})
        console = Console(theme=theme)
        
        start_time = time.time()
        for i in range(1000):
            with console.capture() as capture:
                console.print(f"Message {i}", style="info")
            result = capture.get()
        end_time = time.time()
        
        theme_lookup_time = end_time - start_time
        print(f"✅ Theme style lookup x1000: {theme_lookup_time:.6f}s")
        print(f"   Average per lookup: {(theme_lookup_time/1000)*1000:.3f}ms")
        
        # Test 3: Compare with direct style names
        console_no_theme = Console()
        
        start_time = time.time()
        for i in range(1000):
            with console_no_theme.capture() as capture:
                console_no_theme.print(f"Message {i}", style="cyan")
            result = capture.get()
        end_time = time.time()
        
        direct_style_time = end_time - start_time
        print(f"✅ Direct style names x1000: {direct_style_time:.6f}s")
        print(f"   Average per direct: {(direct_style_time/1000)*1000:.3f}ms")
        
        # Compare overhead
        if theme_lookup_time > 0 and direct_style_time > 0:
            overhead_ratio = theme_lookup_time / direct_style_time
            print(f"\n📊 Theme lookup is {overhead_ratio:.1f}x slower than direct styles")
            
            if overhead_ratio > 3:
                print("⚠️  Theme lookup has significant overhead!")
            elif overhead_ratio > 1.5:
                print("⚠️  Theme lookup has moderate overhead")
            else:
                print("✅ Theme lookup overhead is acceptable")
                
    except ImportError:
        print("❌ Rich not available for testing")

def test_threading_safety():
    """Test if Rich components are thread-safe and don't have contention."""
    print("\nTESTING THREADING SAFETY")
    print("=" * 40)
    
    try:
        from rich.panel import Panel
        from rich.style import Style
        from rich.theme import Theme
        from rich.console import Console
        
        def worker_thread(thread_id):
            """Worker that creates Rich objects."""
            results = []
            
            # Create objects in thread
            for i in range(50):
                panel = Panel(f"Thread {thread_id} Message {i}")
                style = Style(color="red", bold=True)
                theme = Theme({"info": "cyan"})
                
                # This should be fast and not cause contention
                console = Console(theme=theme)
                with console.capture() as capture:
                    console.print(panel)
                result = capture.get()
                results.append(len(result))  # Just store length to avoid memory issues
            
            return sum(results)
        
        # Test with multiple threads
        thread_counts = [1, 4, 8]
        
        for num_threads in thread_counts:
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
                results = [future.result() for future in futures]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"✅ {num_threads} threads: {total_time:.6f}s")
            
            # Check for thread scaling issues
            if num_threads > 1:
                expected_time = total_time / num_threads  # Perfect scaling
                single_thread_time = thread_counts[0] if thread_counts[0] == 1 else total_time
                
                if num_threads == 4 and len(thread_counts) > 1:
                    # Compare 4 threads to 1 thread
                    if total_time > single_thread_time * 1.5:  # 50% overhead is concerning
                        print(f"⚠️  Thread scaling issue: {num_threads} threads took {total_time/single_thread_time:.1f}x longer than expected")
                    else:
                        print(f"✅ Good thread scaling: {num_threads} threads")
                        
    except ImportError:
        print("❌ Rich not available for testing")

def analyze_memory_overhead():
    """Check memory overhead of Rich objects."""
    print("\nTESTING MEMORY OVERHEAD")
    print("=" * 40)
    
    try:
        import sys
        from rich.panel import Panel
        from rich.style import Style
        from rich.theme import Theme
        
        # Test Panel memory
        panels = [Panel(f"Test {i}") for i in range(1000)]
        panel_size = sys.getsizeof(panels) + sum(sys.getsizeof(p) for p in panels)
        print(f"✅ 1000 Panels: ~{panel_size/1024:.1f}KB ({panel_size/1000:.1f} bytes per panel)")
        
        # Test Style memory
        styles = [Style(color="red", bold=True) for _ in range(1000)]
        style_size = sys.getsizeof(styles) + sum(sys.getsizeof(s) for s in styles)
        print(f"✅ 1000 Styles: ~{style_size/1024:.1f}KB ({style_size/1000:.1f} bytes per style)")
        
        # Test Theme memory
        themes = [Theme({"info": "cyan", "error": "red"}) for _ in range(100)]
        theme_size = sys.getsizeof(themes) + sum(sys.getsizeof(t) for t in themes)
        print(f"✅ 100 Themes: ~{theme_size/1024:.1f}KB ({theme_size/100:.1f} bytes per theme)")
        
        # Compare with simple strings
        simple_strings = [f"Test {i}" for i in range(1000)]
        string_size = sys.getsizeof(simple_strings) + sum(sys.getsizeof(s) for s in simple_strings)
        print(f"✅ 1000 Strings: ~{string_size/1024:.1f}KB ({string_size/1000:.1f} bytes per string)")
        
        # Memory overhead ratios
        panel_overhead = panel_size / string_size
        style_overhead = style_size / string_size
        
        print(f"\n📊 Memory overhead:")
        print(f"   Panels: {panel_overhead:.1f}x more memory than strings")
        print(f"   Styles: {style_overhead:.1f}x more memory than strings")
        
        if panel_overhead > 5:
            print("⚠️  Panel memory overhead is high!")
        elif panel_overhead > 2:
            print("⚠️  Panel memory overhead is moderate")
        else:
            print("✅ Panel memory overhead is acceptable")
            
    except ImportError:
        print("❌ Rich not available for testing")

def main():
    """Run all overhead tests."""
    print("RICH 'SAFE' COMPONENTS OVERHEAD ANALYSIS")
    print("=" * 60)
    
    test_rich_panel_overhead()
    test_rich_style_overhead()
    test_rich_theme_overhead()
    test_threading_safety()
    analyze_memory_overhead()
    
    print("\n" + "=" * 60)
    print("FINAL RECOMMENDATION:")
    print("Based on these tests, determine if Rich components have")
    print("acceptable overhead for your performance-critical fdl library.")
    print("=" * 60)

if __name__ == "__main__":
    main()