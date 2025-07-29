"""
SKFunction Example - Function Objects with Presets

This example demonstrates:
- Creating function objects with preset parameters
- Function registries and discovery
- Caching and result management
"""

from suitkaise import skfunction, sktree
import time

def generate_report(store_name, start_date, end_date, format="PDF", include_charts=True):
    """Sample function that generates reports"""
    print(f"Generating {format} report for {store_name}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Include charts: {include_charts}")
    
    # Simulate processing time
    time.sleep(0.5)
    
    return f"{format} report for {store_name} ({start_date} to {end_date})"

def preprocess_data(data_path, model_type, batch_size=32, normalize=True):
    """Sample ML preprocessing function"""
    print(f"Processing {data_path} with {model_type}")
    print(f"Batch size: {batch_size}, Normalize: {normalize}")
    
    # Simulate processing
    time.sleep(0.3)
    
    return f"Processed data from {data_path}"

def main():
    # Initialize function registry
    tree = sktree.connect()
    
    print("=== Basic SKFunction Usage ===")
    
    # Create function objects with presets
    downtown_reports = skfunction.create("downtown_reports", generate_report, {
        "store_name": "Downtown Branch",
        "format": "PDF",
        "include_charts": True
    })
    
    mall_reports = skfunction.create("mall_reports", generate_report, {
        "store_name": "Mall Location",
        "format": "Excel", 
        "include_charts": False
    })
    
    # Register functions in tree
    tree.add("downtown_reports", downtown_reports, path="business/reports")
    tree.add("mall_reports", mall_reports, path="business/reports")
    
    # Use functions with preset parameters
    print("\n--- Using preset functions ---")
    result1 = downtown_reports.call(start_date="2024-01-01", end_date="2024-01-31")
    print(f"Result: {result1}\n")
    
    # Override specific parameters
    result2 = mall_reports.call(
        start_date="2024-02-01", 
        end_date="2024-02-28",
        format="PDF"  # Override the Excel default
    )
    print(f"Result: {result2}\n")
    
    print("=== Function Discovery ===")
    
    # Discover functions from registry
    all_reports = tree.get_all_from("business/reports")
    print(f"Found {len(all_reports)} report functions")
    
    for name, func in all_reports.items():
        print(f"- {name}")
        result = func.call(start_date="2024-03-01", end_date="2024-03-31")
        print(f"  Result: {result}")
    
    print("\n=== ML Pipeline Example ===")
    
    # Create ML preprocessing functions
    image_processor = skfunction.create("image_classifier", preprocess_data, {
        "model_type": "CNN",
        "batch_size": 32,
        "normalize": True
    })
    
    text_processor = skfunction.create("text_classifier", preprocess_data, {
        "model_type": "Transformer",
        "batch_size": 16,
        "normalize": False
    })
    
    # Register in function registry
    tree.add_to_funcrej("image_classifier", image_processor, connection=tree)
    tree.add_to_funcrej("text_classifier", text_processor, connection=tree)
    
    # Use from registry
    classifier = tree.get_from_funcrej("image_classifier")
    result = classifier.call(data_path="./images/dataset1/")
    print(f"Image processing result: {result}")
    
    # Override parameters for different experiment
    result = classifier.call(data_path="./images/dataset2/", batch_size=64)
    print(f"Modified processing result: {result}")
    
    print("\n=== Caching Example ===")
    
    @skfunction.cache_results(ttl=60)  # Cache for 60 seconds
    def expensive_computation(n):
        """Simulate expensive computation"""
        print(f"Computing expensive operation for {n}...")
        time.sleep(1)  # Simulate work
        return n ** 2
    
    # First call - will compute
    start_time = time.time()
    result1 = expensive_computation(10)
    time1 = time.time() - start_time
    print(f"First call result: {result1} (took {time1:.2f}s)")
    
    # Second call - will use cache
    start_time = time.time()
    result2 = expensive_computation(10)
    time2 = time.time() - start_time
    print(f"Second call result: {result2} (took {time2:.2f}s)")

if __name__ == "__main__":
    main()