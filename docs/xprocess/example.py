"""
XProcess Example - Basic Process Management

This example demonstrates the core features of xprocess:
- Creating processes with lifecycle hooks
- Context manager approach
- Class-based approach
"""

from suitkaise import xprocess, sktree
import time

def worker_function(data, process_id=None):
    """A simple worker function that processes data"""
    print(f"Process {process_id} processing: {data}")
    time.sleep(1)  # Simulate work
    return f"Processed: {data}"

def main():
    # Initialize cross processing
    xp = xprocess.CrossProcessing()
    tree = sktree.connect()
    
    # Example 1: Context Manager Approach
    print("=== Context Manager Approach ===")
    
    with xp.ProcessSetup() as setup:
        with xp.OnStart() as start:
            print("Process starting up...")
            
        with xp.BeforeLoop() as before:
            current_loop = xp.get_current_loop()
            before.add_these({"loop_number": current_loop})
            
        with xp.AfterLoop() as after:
            loop_time = xp.get_last_loop_time()
            print(f"Loop completed in {loop_time}s")
            
        with xp.OnFinish() as finish:
            print("Process finishing...")
    
    # Create and run process
    process_config = {"join_in": 5, "join_after": 3}
    process = xp.create_process("worker", worker_function, setup.build(), 
                              args=["test_data"], kwargs=process_config)
    
    # Example 2: Class-Based Approach
    print("\n=== Class-Based Approach ===")
    
    class DataProcessor(xprocess.Process):
        def __init__(self, name, data_source):
            super().__init__(name)
            self.data_source = data_source
            
        def __beforeloop__(self):
            print(f"Starting loop {self.current_loop}")
            
        def __afterloop__(self):
            print(f"Completed loop {self.current_loop}")
            
        def __onfinish__(self):
            print(f"Process {self.name} finished after {self.current_loop} loops")
    
    # Create class-based process
    processor = DataProcessor("data_processor", "sample_data")
    class_process = xp.create_process(worker_function, processor, 
                                    args=["class_data"], kwargs={"join_after": 2})

if __name__ == "__main__":
    main()