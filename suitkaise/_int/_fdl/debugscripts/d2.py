"""
Analysis of the actual cost of accessing local variables in tracebacks.
"""

import time
import traceback
import sys
from typing import Dict, Any

def benchmark_locals_access():
    """Benchmark different levels of locals access."""
    
    print("LOCAL VARIABLES ACCESS COST ANALYSIS")
    print("=" * 50)
    
    def create_frame_with_locals():
        """Create a function frame with various local variables."""
        # Small locals
        username = "alice"
        user_id = 12345
        is_active = True
        
        # Medium locals  
        config = {"debug": True, "timeout": 30, "retries": 3}
        tags = ["user", "active", "premium"]
        
        # Large locals
        large_list = list(range(1000))
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100)}
        
        # Cause an error to get traceback
        return large_list[2000]  # IndexError
    
    # Test 1: Just getting the traceback (no locals access)
    print("\n1. BASELINE - Traceback without locals access:")
    iterations = 1000
    
    start_time = time.time()
    for _ in range(iterations):
        try:
            create_frame_with_locals()
        except Exception:
            # Just get the traceback, don't access locals
            tb = sys.exc_info()[2]
            frames = list(traceback.walk_tb(tb))
    end_time = time.time()
    
    baseline_time = end_time - start_time
    print(f"✅ {iterations} tracebacks (no locals): {baseline_time:.6f}s")
    print(f"   Average: {(baseline_time/iterations)*1000:.3f}ms")
    
    # Test 2: Accessing frame.f_locals (getting the dict)
    print("\n2. ACCESSING frame.f_locals dict:")
    
    start_time = time.time()
    for _ in range(iterations):
        try:
            create_frame_with_locals()
        except Exception:
            tb = sys.exc_info()[2]
            for frame, lineno in traceback.walk_tb(tb):
                locals_dict = frame.f_locals  # This is the cost we're measuring
    end_time = time.time()
    
    locals_dict_time = end_time - start_time
    print(f"✅ {iterations} locals dict access: {locals_dict_time:.6f}s")
    print(f"   Average: {(locals_dict_time/iterations)*1000:.3f}ms")
    print(f"   Overhead vs baseline: {((locals_dict_time - baseline_time)/baseline_time)*100:.1f}%")
    
    # Test 3: Iterating through locals (keys and values)
    print("\n3. ITERATING through locals:")
    
    start_time = time.time()
    for _ in range(iterations):
        try:
            create_frame_with_locals()
        except Exception:
            tb = sys.exc_info()[2]
            for frame, lineno in traceback.walk_tb(tb):
                locals_dict = frame.f_locals
                # Iterate through all locals
                for name, value in locals_dict.items():
                    pass  # Just iterate, don't process
    end_time = time.time()
    
    locals_iter_time = end_time - start_time
    print(f"✅ {iterations} locals iteration: {locals_iter_time:.6f}s")
    print(f"   Average: {(locals_iter_time/iterations)*1000:.3f}ms")
    print(f"   Overhead vs baseline: {((locals_iter_time - baseline_time)/baseline_time)*100:.1f}%")
    
    # Test 4: Simple repr() of locals values
    print("\n4. SIMPLE repr() of locals:")
    
    start_time = time.time()
    for _ in range(iterations // 10):  # Fewer iterations since this is slower
        try:
            create_frame_with_locals()
        except Exception:
            tb = sys.exc_info()[2]
            for frame, lineno in traceback.walk_tb(tb):
                locals_dict = frame.f_locals
                for name, value in locals_dict.items():
                    if not name.startswith('__'):
                        repr_str = repr(value)  # This is where cost adds up
                        if len(repr_str) > 100:
                            repr_str = repr_str[:97] + "..."
    end_time = time.time()
    
    locals_repr_time = end_time - start_time
    # Normalize to same number of iterations
    locals_repr_time_normalized = locals_repr_time * 10
    print(f"✅ {iterations//10} locals repr (normalized): {locals_repr_time_normalized:.6f}s")
    print(f"   Average: {(locals_repr_time_normalized/(iterations))*1000:.3f}ms")
    print(f"   Overhead vs baseline: {((locals_repr_time_normalized - baseline_time)/baseline_time)*100:.1f}%")
    
    # Test 5: Rich-style pretty printing (expensive!)
    print("\n5. RICH-STYLE pretty printing:")
    
    try:
        from rich.pretty import pretty_repr
        
        start_time = time.time()
        for _ in range(iterations // 50):  # Much fewer iterations
            try:
                create_frame_with_locals()
            except Exception:
                tb = sys.exc_info()[2]
                for frame, lineno in traceback.walk_tb(tb):
                    locals_dict = frame.f_locals
                    for name, value in locals_dict.items():
                        if not name.startswith('__'):
                            pretty_str = pretty_repr(value)  # Very expensive
        end_time = time.time()
        
        rich_pretty_time = end_time - start_time
        # Normalize to same number of iterations
        rich_pretty_time_normalized = rich_pretty_time * 50
        print(f"✅ {iterations//50} Rich pretty repr (normalized): {rich_pretty_time_normalized:.6f}s")
        print(f"   Average: {(rich_pretty_time_normalized/iterations)*1000:.3f}ms")
        print(f"   Overhead vs baseline: {((rich_pretty_time_normalized - baseline_time)/baseline_time)*100:.1f}%")
        
    except ImportError:
        print("❌ Rich not available for pretty printing test")
    
    print(f"\n📊 COST BREAKDOWN SUMMARY:")
    print(f"   Baseline traceback:        {(baseline_time/iterations)*1000:.3f}ms")
    print(f"   + Access locals dict:      +{((locals_dict_time - baseline_time)/iterations)*1000:.3f}ms")
    print(f"   + Iterate locals:          +{((locals_iter_time - locals_dict_time)/iterations)*1000:.3f}ms")
    print(f"   + Simple repr():           +{((locals_repr_time_normalized - locals_iter_time)/iterations)*1000:.3f}ms")
    if 'rich_pretty_time_normalized' in locals():
        print(f"   + Rich pretty printing:    +{((rich_pretty_time_normalized - locals_repr_time_normalized)/iterations)*1000:.3f}ms")

def analyze_locals_size_impact():
    """Show how the size/complexity of locals affects performance."""
    
    print("\n" + "=" * 50)
    print("LOCALS SIZE IMPACT ANALYSIS")
    print("=" * 50)
    
    def small_locals_frame():
        x = 1
        y = "hello"
        return x[10]  # Error
    
    def medium_locals_frame():
        config = {"key": "value"}
        data = list(range(100))
        items = [{"id": i} for i in range(10)]
        return config[10]  # Error
    
    def large_locals_frame():
        huge_list = list(range(10000))
        huge_dict = {f"key_{i}": list(range(i % 20)) for i in range(1000)}
        nested_data = {"level1": {"level2": {"level3": list(range(100))}}}
        return huge_list[20000]  # Error
    
    scenarios = [
        ("Small locals", small_locals_frame),
        ("Medium locals", medium_locals_frame), 
        ("Large locals", large_locals_frame)
    ]
    
    for scenario_name, func in scenarios:
        print(f"\n{scenario_name}:")
        
        # Test simple repr approach
        start_time = time.time()
        for _ in range(100):
            try:
                func()
            except Exception:
                tb = sys.exc_info()[2]
                for frame, lineno in traceback.walk_tb(tb):
                    locals_dict = frame.f_locals
                    for name, value in locals_dict.items():
                        if not name.startswith('__'):
                            repr_str = repr(value)
                            if len(repr_str) > 100:
                                repr_str = repr_str[:97] + "..."
        end_time = time.time()
        
        simple_time = end_time - start_time
        print(f"  Simple repr: {(simple_time/100)*1000:.3f}ms per traceback")
        
        # Show actual locals info
        try:
            func()
        except Exception:
            tb = sys.exc_info()[2]
            frame = list(traceback.walk_tb(tb))[0][0]
            locals_dict = frame.f_locals
            num_vars = len([k for k in locals_dict.keys() if not k.startswith('__')])
            total_repr_size = sum(len(repr(v)) for k, v in locals_dict.items() if not k.startswith('__'))
            print(f"  Variables: {num_vars}, Total repr size: {total_repr_size:,} chars")

def show_optimization_strategies():
    """Show different strategies for optimizing locals display."""
    
    print("\n" + "=" * 50)
    print("OPTIMIZATION STRATEGIES")
    print("=" * 50)
    
    print("""
🎯 PERFORMANCE OPTIMIZATION OPTIONS:

1. **SKIP LOCALS ENTIRELY** (Fastest)
   - Cost: ~0.1ms overhead
   - Benefit: Maximum performance
   - Trade-off: No variable debugging info

2. **LOCALS NAMES ONLY** (Very Fast)
   - Cost: ~0.5ms overhead
   - Show: just variable names and types
   - Example: "username (str), user_id (int), config (dict)"

3. **LIMITED SIMPLE REPR** (Fast)
   - Cost: ~2-5ms overhead
   - Show: basic repr() but truncated
   - Limit: max 100 chars per variable

4. **SMART FILTERING** (Balanced)
   - Cost: ~1-3ms overhead
   - Skip: large objects, private vars, modules
   - Show: only small, useful variables

5. **CONFIGURABLE LEVELS** (Flexible)
   - Level 0: No locals
   - Level 1: Names and types only
   - Level 2: Simple values only
   - Level 3: All locals (truncated)
""")

if __name__ == "__main__":
    benchmark_locals_access()
    analyze_locals_size_impact()
    show_optimization_strategies()