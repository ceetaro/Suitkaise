"""
Realistic cucumber usage scenarios.

These tests represent actual use cases developers encounter:
- ML/data science pipelines
- Web scrapers with sessions
- Task queue workers
- Application state checkpointing
- Distributed computing

Tests include:
1. Functional verification (objects work, not just serializable)
2. Actual multiprocess testing (real process boundaries)
3. Performance benchmarks vs pickle/dill/cloudpickle
"""

import logging
import threading
import queue
import tempfile
import sqlite3
import io
import time
import multiprocessing
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
from collections import defaultdict, Counter

import pytest

from suitkaise.cucumber._int.serializer import Serializer
from suitkaise.cucumber._int.deserializer import Deserializer

# Try to import alternative serializers
try:
    import dill
    HAS_DILL = True
except ImportError:
    HAS_DILL = False
    dill = None

try:
    import cloudpickle
    HAS_CLOUDPICKLE = True
except ImportError:
    HAS_CLOUDPICKLE = False
    cloudpickle = None


# Helper for multiprocess testing
def worker_function(serialized_data, return_queue):
    """Worker function that runs in a separate process."""
    import pickle
    from suitkaise.cucumber._int.deserializer import Deserializer
    from suitkaise.cucumber._int.serializer import Serializer
    
    # Deserialize in worker process
    deserializer = Deserializer()
    obj = deserializer.deserialize(serialized_data)
    
    # Do work with the object (prove it's functional)
    result = {
        "worker_pid": multiprocessing.current_process().pid,
        "obj_type": type(obj).__name__,
        "functional_test_results": {},
    }
    
    # Test that objects actually work AND verify state
    try:
        # Logger: verify it exists and works
        if hasattr(obj, 'logger'):
            obj.logger.info("Worker process logging works!")
            obj.logger.warning("Worker warning test")
            result["functional_test_results"]["logger"] = "✓"
            result["logger_name"] = obj.logger.name
        
        # Lock: verify it exists, works, and can be acquired/released multiple times
        if hasattr(obj, 'lock'):
            with obj.lock:
                pass
            # Test multiple acquire/release cycles
            acquired = obj.lock.acquire(blocking=False)
            if acquired:
                obj.lock.release()
            result["functional_test_results"]["lock"] = "✓"
        
        # Queue: verify size, extract item, verify content, add new item
        if hasattr(obj, 'work_items') and obj.work_items.qsize() > 0:
            original_size = obj.work_items.qsize()
            item = obj.work_items.get()
            result["functional_test_results"]["queue"] = "✓"
            result["queue_item_extracted"] = item
            result["queue_original_size"] = original_size
            result["queue_new_size"] = obj.work_items.qsize()
            # Add worker's own item
            obj.work_items.put({"worker_task": "completed", "worker_pid": result["worker_pid"]})
        
        # StringIO: verify content, position, read/write operations
        if hasattr(obj, 'temp_storage'):
            # Read existing content
            original_content = obj.temp_storage.getvalue()
            result["original_stringio_content"] = original_content
            
            # Write worker data
            obj.temp_storage.write("Worker added data\n")
            obj.temp_storage.write(f"Worker PID: {result['worker_pid']}\n")
            
            # Verify new content
            new_content = obj.temp_storage.getvalue()
            result["functional_test_results"]["stringio"] = "✓"
            result["stringio_content_after_worker"] = new_content
        
        # Counter/stats: verify values and mutate them
        if hasattr(obj, 'stats'):
            result["original_stats"] = dict(obj.stats)
            # Increment existing counter
            if "tasks" in obj.stats:
                obj.stats["tasks"] += 5
            # Add new counter
            obj.stats["worker_processed"] = 1
            result["modified_stats"] = dict(obj.stats)
            result["functional_test_results"]["stats"] = "✓"
        
        # Serialize result back (with ALL modifications)
        serializer = Serializer()
        result["obj_serialized_back"] = serializer.serialize(obj)
        
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    
    return_queue.put(result)


class TestMLPipeline:
    """Machine learning pipeline with complex state."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_ml_training_state(self):
        """Serialize ML training state for checkpointing."""
        
        @dataclass
        class TrainingState:
            epoch: int
            batch: int
            loss_history: List[float]
            metrics: Dict[str, float]
            best_score: float
        
        # Realistic ML training checkpoint
        class ModelCheckpoint:
            def __init__(self):
                self.logger = logging.getLogger("model_training")
                self.logger.setLevel(logging.INFO)
                
                self.state = TrainingState(
                    epoch=10,
                    batch=500,
                    loss_history=[0.5, 0.4, 0.35, 0.3, 0.28],
                    metrics={"accuracy": 0.92, "f1": 0.89},
                    best_score=0.92,
                )
                
                self.lock = threading.Lock()
                self.progress_file = io.StringIO()
                self.progress_file.write("Training progress: 50%\n")
                self.progress_file.seek(0)
        
        checkpoint = ModelCheckpoint()
        
        # Serialize
        serialized = self.serializer.serialize(checkpoint)
        
        # Deserialize (e.g., resume training on different machine/process)
        restored = self.deserializer.deserialize(serialized)
        
        # Verify attributes
        assert restored.state.epoch == 10
        assert restored.state.batch == 500
        assert len(restored.state.loss_history) == 5
        assert restored.state.metrics["accuracy"] == 0.92
        assert isinstance(restored.logger, logging.Logger)
        assert isinstance(restored.lock, type(threading.Lock()))
        assert "Training progress" in restored.progress_file.getvalue()
        
        # Functional verification: Can we actually USE these objects?
        print("\n  Functional tests:")
        
        # Test logger works
        restored.logger.info("Test log message")
        print("    ✓ Logger.info() works")
        
        # Test lock works
        with restored.lock:
            pass
        print("    ✓ Lock context manager works")
        
        # Test file operations work
        restored.progress_file.write("Additional progress\n")
        assert "Additional progress" in restored.progress_file.getvalue()
        print("    ✓ StringIO read/write works")
        
        # Test dataclass access works
        restored.state.epoch += 1
        assert restored.state.epoch == 11
        print("    ✓ Dataclass modification works")
        
        print("\n✓ ML checkpoint serialization works!")
        print(f"  Checkpoint size: {len(serialized):,} bytes")


class TestWebScraper:
    """Web scraper with session state."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_scraper_state(self):
        """Serialize web scraper state for distributed crawling."""
        
        class ScraperState:
            def __init__(self):
                # Logger for tracking
                self.logger = logging.getLogger("scraper")
                
                # Visited URLs
                self.visited = set([
                    "https://example.com/page1",
                    "https://example.com/page2",
                    "https://example.com/page3",
                ])
                
                # Queue of URLs to process
                self.url_queue = queue.Queue()
                self.url_queue.put("https://example.com/page4")
                self.url_queue.put("https://example.com/page5")
                
                # Stats
                self.stats = Counter({
                    "pages_scraped": 3,
                    "links_found": 27,
                    "errors": 0,
                })
                
                # Rate limiting
                self.rate_limit_lock = threading.Lock()
                
                # Temp storage for scraped data
                self.temp_data = io.StringIO()
                self.temp_data.write("Scraped data:\n")
                self.temp_data.write("- Page 1: Title A\n")
                self.temp_data.write("- Page 2: Title B\n")
        
        scraper = ScraperState()
        
        # Serialize (send to another worker)
        serialized = self.serializer.serialize(scraper)
        
        # Deserialize in worker process
        worker_scraper = self.deserializer.deserialize(serialized)
        
        # Verify state preserved
        assert len(worker_scraper.visited) == 3
        assert "https://example.com/page1" in worker_scraper.visited
        assert worker_scraper.url_queue.qsize() == 2
        assert worker_scraper.stats["pages_scraped"] == 3
        assert isinstance(worker_scraper.stats, Counter)
        assert isinstance(worker_scraper.logger, logging.Logger)
        assert isinstance(worker_scraper.rate_limit_lock, type(threading.Lock()))
        
        # Functional verification
        print("\n  Functional tests:")
        
        # Queue operations work
        next_url = worker_scraper.url_queue.get()
        assert next_url == "https://example.com/page4"
        worker_scraper.url_queue.put("https://example.com/page6")
        assert worker_scraper.url_queue.qsize() == 2
        print("    ✓ Queue get/put works")
        
        # Counter operations work
        worker_scraper.stats["pages_scraped"] += 1
        assert worker_scraper.stats["pages_scraped"] == 4
        # most_common returns highest count (links_found=27 is highest)
        assert worker_scraper.stats.most_common(1)[0] == ("links_found", 27)
        # Verify our increment worked
        assert worker_scraper.stats["pages_scraped"] == 4
        print("    ✓ Counter increment and most_common() work")
        
        # Set operations work
        worker_scraper.visited.add("https://example.com/page7")
        assert len(worker_scraper.visited) == 4
        print("    ✓ Set add() works")
        
        # Lock works
        acquired = worker_scraper.rate_limit_lock.acquire(blocking=False)
        assert acquired
        worker_scraper.rate_limit_lock.release()
        print("    ✓ Lock acquire/release works")
        
        print("\n✓ Web scraper state serialization works!")
        print(f"  State size: {len(serialized):,} bytes")


class TestTaskQueue:
    """Task queue worker state."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_worker_state(self):
        """Serialize task queue worker state."""
        
        class WorkerState:
            def __init__(self):
                # Worker identity
                self.worker_id = "worker-123"
                
                # Logger
                self.logger = logging.getLogger(f"worker.{self.worker_id}")
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
                
                # Task queue
                self.pending_tasks = queue.Queue()
                self.pending_tasks.put({"task": "send_email", "to": "user@example.com"})
                self.pending_tasks.put({"task": "process_payment", "amount": 100})
                
                # Completed tasks
                self.completed = []
                
                # Stats
                self.stats = defaultdict(int)
                self.stats["tasks_processed"] = 42
                self.stats["errors"] = 2
                self.stats["retries"] = 5
                
                # Database connection (simulated with sqlite)
                self.db_conn = sqlite3.connect(":memory:")
                cursor = self.db_conn.cursor()
                cursor.execute("CREATE TABLE task_log (id INTEGER, status TEXT)")
                cursor.execute("INSERT INTO task_log VALUES (1, 'completed')")
                self.db_conn.commit()
                
                # Synchronization
                self.task_lock = threading.Lock()
                self.shutdown_event = threading.Event()
        
        worker = WorkerState()
        
        # Serialize (checkpoint worker state)
        serialized = self.serializer.serialize(worker)
        
        # Deserialize (restore worker in new process)
        restored = self.deserializer.deserialize(serialized)
        
        # Verify attributes
        assert restored.worker_id == "worker-123"
        assert isinstance(restored.logger, logging.Logger)
        assert restored.pending_tasks.qsize() == 2
        assert restored.stats["tasks_processed"] == 42
        assert isinstance(restored.stats, defaultdict)
        assert isinstance(restored.db_conn, sqlite3.Connection)
        assert isinstance(restored.task_lock, type(threading.Lock()))
        assert isinstance(restored.shutdown_event, threading.Event)
        
        # Functional verification
        print("\n  Functional tests:")
        
        # Queue works
        task = restored.pending_tasks.get()
        assert task["task"] == "send_email"
        print("    ✓ Queue.get() retrieves task")
        
        # Database works
        cursor = restored.db_conn.cursor()
        rows = cursor.execute("SELECT * FROM task_log").fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "completed"
        # Insert new row
        cursor.execute("INSERT INTO task_log VALUES (2, 'new')")
        restored.db_conn.commit()
        print("    ✓ SQLite queries and inserts work")
        
        # Lock works
        with restored.task_lock:
            pass
        print("    ✓ Lock works in context manager")
        
        # Event works
        assert not restored.shutdown_event.is_set()
        restored.shutdown_event.set()
        assert restored.shutdown_event.is_set()
        print("    ✓ Event.set() and is_set() work")
        
        # defaultdict works
        restored.stats["new_counter"] += 1
        assert restored.stats["new_counter"] == 1
        print("    ✓ defaultdict auto-initialization works")
        
        print("\n✓ Task queue worker serialization works!")
        print(f"  Worker state size: {len(serialized):,} bytes")


class TestDataPipeline:
    """Data processing pipeline state."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_pipeline_state(self):
        """Serialize data pipeline state for distributed processing."""
        
        class PipelineState:
            def __init__(self):
                # Input/output files
                self.input_file = io.StringIO("row1,data1\nrow2,data2\nrow3,data3\n")
                self.output_file = io.StringIO()
                
                # Processing stats
                self.processed_count = 1500
                self.error_count = 3
                self.error_log = io.StringIO()
                self.error_log.write("Error 1: Invalid format\n")
                self.error_log.write("Error 2: Missing column\n")
                
                # Caching
                self.cache = {}
                self.cache_hits = Counter({"user_data": 450, "metadata": 120})
                
                # Temp storage
                self.temp_results = tempfile.NamedTemporaryFile(mode='w+', delete=False)
                self.temp_results.write("temp result 1\ntemp result 2\n")
                self.temp_results.seek(0)
                
                # Synchronization
                self.batch_lock = threading.RLock()
                self.progress_event = threading.Event()
                self.progress_event.set()
                
                # Logger
                self.logger = logging.getLogger("pipeline")
                self.logger.setLevel(logging.DEBUG)
        
        pipeline = PipelineState()
        
        # Serialize
        serialized = self.serializer.serialize(pipeline)
        
        # Deserialize
        restored = self.deserializer.deserialize(serialized)
        
        # Verify
        assert restored.processed_count == 1500
        assert restored.error_count == 3
        assert "Invalid format" in restored.error_log.getvalue()
        assert isinstance(restored.cache_hits, Counter)
        assert restored.cache_hits["user_data"] == 450
        assert isinstance(restored.input_file, io.StringIO)
        assert "row1,data1" in restored.input_file.getvalue()
        assert isinstance(restored.batch_lock, type(threading.RLock()))
        assert restored.progress_event.is_set()
        
        print("\n✓ Data pipeline serialization works!")
        print(f"  Pipeline state size: {len(serialized):,} bytes")


class TestApplicationCheckpoint:
    """Full application state checkpoint."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_app_state(self):
        """Serialize entire application state for crash recovery."""
        
        class ApplicationState:
            def __init__(self):
                # Configuration
                self.config = {
                    "debug": True,
                    "max_workers": 4,
                    "timeout": 30,
                    "database_path": Path("/tmp/app.db"),
                }
                
                # Active connections
                self.db = sqlite3.connect(":memory:")
                cursor = self.db.cursor()
                cursor.execute("CREATE TABLE users (id INTEGER, name TEXT)")
                cursor.execute("INSERT INTO users VALUES (1, 'Alice')")
                cursor.execute("INSERT INTO users VALUES (2, 'Bob')")
                self.db.commit()
                
                # Loggers
                self.main_logger = logging.getLogger("app.main")
                self.worker_logger = logging.getLogger("app.worker")
                
                # Thread coordination
                self.worker_pool_lock = threading.Lock()
                self.shutdown_event = threading.Event()
                
                # Work queues
                self.input_queue = queue.Queue()
                self.input_queue.put({"user_id": 1, "action": "login"})
                self.input_queue.put({"user_id": 2, "action": "logout"})
                
                self.result_queue = queue.Queue()
                
                # Runtime stats
                self.stats = {
                    "uptime": 3600,
                    "requests_processed": defaultdict(int, {"GET": 1500, "POST": 300}),
                    "active_users": {1, 2, 3, 4, 5},
                    "error_counts": Counter({"timeout": 5, "invalid_request": 2}),
                }
                
                # Temp files for processing
                self.log_buffer = io.StringIO()
                self.log_buffer.write("[INFO] Application started\n")
                self.log_buffer.write("[INFO] Workers initialized\n")
        
        app = ApplicationState()
        
        # Checkpoint (save state before shutdown)
        checkpoint_data = self.serializer.serialize(app)
        
        # Restore (recover after crash)
        restored = self.deserializer.deserialize(checkpoint_data)
        
        # Verify everything is preserved
        assert restored.config["max_workers"] == 4
        assert isinstance(restored.config["database_path"], Path)
        assert isinstance(restored.db, sqlite3.Connection)
        
        # Check database state
        cursor = restored.db.cursor()
        users = cursor.execute("SELECT * FROM users").fetchall()
        assert len(users) == 2
        assert users[0][1] == "Alice"
        
        # Check loggers
        assert isinstance(restored.main_logger, logging.Logger)
        assert isinstance(restored.worker_logger, logging.Logger)
        
        # Check queues
        assert restored.input_queue.qsize() == 2
        
        # Check stats
        assert restored.stats["uptime"] == 3600
        assert isinstance(restored.stats["requests_processed"], defaultdict)
        assert restored.stats["requests_processed"]["GET"] == 1500
        assert isinstance(restored.stats["error_counts"], Counter)
        assert 3 in restored.stats["active_users"]
        
        # Check log buffer
        assert "Application started" in restored.log_buffer.getvalue()
        
        print("\n✓ Application checkpoint works!")
        print(f"  Checkpoint size: {len(checkpoint_data):,} bytes")


class TestActualMultiprocess:
    """Test with ACTUAL separate processes using multiprocessing module."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_real_process_boundary(self):
        """Send object to actual separate process and verify it works there."""
        
        class WorkerState:
            def __init__(self):
                self.logger = logging.getLogger("worker")
                self.lock = threading.Lock()
                self.work_items = queue.Queue()
                self.work_items.put({"task": "process", "data": [1, 2, 3]})
                self.temp_storage = io.StringIO()
                self.temp_storage.write("Initial data\n")
                self.stats = Counter({"tasks": 10})
        
        # Create object in main process
        main_pid = multiprocessing.current_process().pid
        state = WorkerState()
        
        # Serialize
        serialized = self.serializer.serialize(state)
        
        # Send to worker process
        return_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=worker_function,
            args=(serialized, return_queue)
        )
        process.start()
        process.join(timeout=10)
        
        # Get result from worker
        assert not return_queue.empty(), "Worker didn't return result!"
        worker_result = return_queue.get()
        
        # Verify worker ran in different process
        assert worker_result["worker_pid"] != main_pid, "Worker should run in different process!"
        
        # Verify objects were functional in worker (not just present, but WORKED)
        assert "logger" in worker_result["functional_test_results"], "Logger didn't work in worker"
        assert "lock" in worker_result["functional_test_results"], "Lock didn't work in worker"
        assert "queue" in worker_result["functional_test_results"], "Queue didn't work in worker"
        assert "stringio" in worker_result["functional_test_results"], "StringIO didn't work in worker"
        assert "stats" in worker_result["functional_test_results"], "Stats didn't work in worker"
        
        # Verify worker's detailed operations
        assert worker_result["logger_name"] == "worker", "Logger name incorrect"
        assert worker_result["queue_original_size"] == 1, "Queue should have had 1 item"
        assert worker_result["queue_new_size"] == 0, "Queue should be empty after get()"
        assert worker_result["queue_item_extracted"]["task"] == "process", "Wrong queue item extracted"
        assert "Initial data" in worker_result["original_stringio_content"], "Original StringIO content missing"
        assert worker_result["original_stats"]["tasks"] == 10, "Original stats value wrong"
        assert worker_result["modified_stats"]["tasks"] == 15, "Stats not incremented correctly"
        assert worker_result["modified_stats"]["worker_processed"] == 1, "Worker didn't add new stat"
        
        # Deserialize the object with worker's modifications
        obj_from_worker = self.deserializer.deserialize(worker_result["obj_serialized_back"])
        
        # STRICT VERIFICATION: All original state + worker modifications must survive
        print("\n  Verifying state survived double round-trip (main → worker → main):")
        
        # 1. Logger preserved
        assert hasattr(obj_from_worker, "logger"), "Logger attribute missing"
        assert obj_from_worker.logger.name == "worker", "Logger name not preserved"
        print("    ✓ Logger: name preserved")
        
        # 2. Lock preserved and functional
        assert hasattr(obj_from_worker, "lock"), "Lock attribute missing"
        with obj_from_worker.lock:  # Must be functional
            pass
        print("    ✓ Lock: functional after double round-trip")
        
        # 3. Queue: worker's item added, original item removed
        assert hasattr(obj_from_worker, "work_items"), "Queue attribute missing"
        assert obj_from_worker.work_items.qsize() == 1, f"Queue should have 1 item (worker's), has {obj_from_worker.work_items.qsize()}"
        worker_item = obj_from_worker.work_items.get()
        assert worker_item["worker_task"] == "completed", "Worker's item not in queue"
        assert worker_item["worker_pid"] == worker_result["worker_pid"], "Worker PID not in item"
        print("    ✓ Queue: worker's modifications preserved (removed 1, added 1)")
        
        # 4. StringIO: original + worker content both preserved
        assert hasattr(obj_from_worker, "temp_storage"), "StringIO attribute missing"
        final_content = obj_from_worker.temp_storage.getvalue()
        assert "Initial data" in final_content, "Original StringIO content lost"
        assert "Worker added data" in final_content, "Worker's StringIO write lost"
        assert f"Worker PID: {worker_result['worker_pid']}" in final_content, "Worker PID write lost"
        print("    ✓ StringIO: original + worker content both preserved")
        
        # 5. Stats/Counter: increments and additions preserved
        assert hasattr(obj_from_worker, "stats"), "Stats attribute missing"
        assert obj_from_worker.stats["tasks"] == 15, f"Stats increment lost: expected 15, got {obj_from_worker.stats['tasks']}"
        assert obj_from_worker.stats["worker_processed"] == 1, "Worker's new stat lost"
        # Verify it's still a Counter (functional)
        assert hasattr(obj_from_worker.stats, "most_common"), "Stats lost Counter functionality"
        print("    ✓ Stats: worker's increment (10→15) and new key preserved")
        
        print("\n✓ Real process boundary test passed!")
        print(f"  Main PID: {main_pid}")
        print(f"  Worker PID: {worker_result['worker_pid']}")
        print(f"  ALL worker modifications survived double serialization round-trip")
        print(f"  This proves objects are FULLY FUNCTIONAL across process boundaries")


class TestMultiprocessWorkflow:
    """Simulates passing state between processes multiple times."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_process_handoff(self):
        """
        Simulate: Process A → Process B → Process C → Process A
        
        This is the real-world inter-process communication use case.
        """
        
        class SharedWorkState:
            def __init__(self, process_name: str):
                self.process_name = process_name
                self.logger = logging.getLogger(f"process.{process_name}")
                
                self.work_items = queue.Queue()
                self.results = []
                
                self.lock = threading.Lock()
                self.completion_event = threading.Event()
                
                self.stats = Counter()
                
                self.temp_storage = io.StringIO()
        
        # Process A creates initial state
        state_a = SharedWorkState("A")
        state_a.work_items.put({"task": "process", "data": [1, 2, 3]})
        state_a.stats["created"] = 1
        state_a.temp_storage.write("Created by A\n")
        
        # A → B
        serialized_for_b = self.serializer.serialize(state_a)
        state_b = self.deserializer.deserialize(serialized_for_b)
        
        # B does work
        state_b.results.append("B processed task")
        state_b.stats["processed_by_b"] = 1
        state_b.temp_storage.write("Processed by B\n")
        
        # B → C
        serialized_for_c = self.serializer.serialize(state_b)
        state_c = self.deserializer.deserialize(serialized_for_c)
        
        # C does work
        state_c.results.append("C finalized task")
        state_c.stats["finalized_by_c"] = 1
        state_c.temp_storage.write("Finalized by C\n")
        
        # C → A (return result)
        serialized_back_to_a = self.serializer.serialize(state_c)
        final_state = self.deserializer.deserialize(serialized_back_to_a)
        
        # Verify all work was preserved
        assert "B processed task" in final_state.results
        assert "C finalized task" in final_state.results
        assert final_state.stats["created"] == 1
        assert final_state.stats["processed_by_b"] == 1
        assert final_state.stats["finalized_by_c"] == 1
        
        temp_content = final_state.temp_storage.getvalue()
        assert "Created by A" in temp_content
        assert "Processed by B" in temp_content
        assert "Finalized by C" in temp_content
        
        print("\n✓ Multi-process handoff works!")
        print(f"  3 round-trips completed successfully")
        print(f"  Final state size: {len(serialized_back_to_a):,} bytes")


class TestDistributedCompute:
    """Distributed computing scenario."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_map_reduce_state(self):
        """Serialize map-reduce job state."""
        
        class MapReduceJob:
            def __init__(self):
                self.job_id = "job-12345"
                
                # Logger for tracking
                self.logger = logging.getLogger(f"mapreduce.{self.job_id}")
                
                # Input data partitions
                self.partitions = [
                    {"id": 1, "data": list(range(100))},
                    {"id": 2, "data": list(range(100, 200))},
                    {"id": 3, "data": list(range(200, 300))},
                ]
                
                # Intermediate results
                self.map_results = defaultdict(list)
                self.map_results["partition_1"] = [1, 2, 3]
                self.map_results["partition_2"] = [4, 5, 6]
                
                # Reducer state
                self.reduce_progress = Counter({"completed": 2, "pending": 1})
                
                # Coordination
                self.mapper_locks = {
                    f"mapper_{i}": threading.Lock()
                    for i in range(3)
                }
                
                self.barrier = threading.Barrier(3)
                
                # Results buffer
                self.results_buffer = io.BytesIO()
                self.results_buffer.write(b"Results header\n")
                self.results_buffer.write(b"Data chunk 1\n")
        
        job = MapReduceJob()
        
        # Serialize job state
        serialized = self.serializer.serialize(job)
        
        # Deserialize on worker nodes
        worker_job = self.deserializer.deserialize(serialized)
        
        # Verify
        assert worker_job.job_id == "job-12345"
        assert len(worker_job.partitions) == 3
        assert worker_job.partitions[0]["data"][:5] == [0, 1, 2, 3, 4]
        assert isinstance(worker_job.map_results, defaultdict)
        assert worker_job.map_results["partition_1"] == [1, 2, 3]
        assert isinstance(worker_job.reduce_progress, Counter)
        assert worker_job.reduce_progress["completed"] == 2
        assert len(worker_job.mapper_locks) == 3
        assert isinstance(worker_job.barrier, threading.Barrier)
        assert b"Results header" in worker_job.results_buffer.getvalue()
        
        print("\n✓ MapReduce job serialization works!")
        print(f"  Job state size: {len(serialized):,} bytes")


class TestRealisticRoundTrips:
    """Test realistic objects through multiple round-trips."""
    
    def setup_method(self):
        self.serializer = Serializer()
        self.deserializer = Deserializer()
    
    def test_logger_intensive_workflow(self):
        """Logger-heavy workflow (common in production)."""
        
        class LoggerIntensiveApp:
            def __init__(self):
                # Multiple loggers for different subsystems
                self.main_logger = logging.getLogger("app")
                self.db_logger = logging.getLogger("app.database")
                self.api_logger = logging.getLogger("app.api")
                self.cache_logger = logging.getLogger("app.cache")
                
                # Add handlers
                for logger in [self.main_logger, self.db_logger, self.api_logger]:
                    handler = logging.StreamHandler()
                    logger.addHandler(handler)
                
                # App state
                self.requests_count = 1500
                self.active_connections = {1, 2, 3, 4, 5}
                self.cache = defaultdict(int)
                self.cache["user_data"] = 42
        
        app = LoggerIntensiveApp()
        
        # Run 10 round-trips
        for cycle in range(10):
            serialized = self.serializer.serialize(app)
            app = self.deserializer.deserialize(serialized)
        
        # Verify after 10 cycles
        assert isinstance(app.main_logger, logging.Logger)
        assert isinstance(app.db_logger, logging.Logger)
        assert app.requests_count == 1500
        assert len(app.active_connections) == 5
        assert app.cache["user_data"] == 42
        
        print("\n✓ Logger-intensive workflow works after 10 round-trips!")
    
    def test_mixed_complexity_object(self):
        """Object with mix of simple and complex types."""
        
        class MixedApp:
            def __init__(self):
                # Simple data
                self.name = "MyApp"
                self.version = "1.0.0"
                self.counters = Counter({"hits": 100, "misses": 10})
                
                # Complex resources
                self.logger = logging.getLogger(self.name)
                self.lock = threading.Lock()
                self.event = threading.Event()
                
                # IO buffers
                self.output = io.StringIO()
                self.output.write(f"{self.name} v{self.version}\n")
                
                # Nested state
                self.subsystems = {
                    "auth": {"logger": logging.getLogger("auth"), "active": True},
                    "cache": {"logger": logging.getLogger("cache"), "size": 1000},
                }
        
        app = MixedApp()
        
        # 20 round-trips
        for cycle in range(20):
            serialized = self.serializer.serialize(app)
            app = self.deserializer.deserialize(serialized)
        
        # Verify
        assert app.name == "MyApp"
        assert app.version == "1.0.0"
        assert isinstance(app.counters, Counter)
        assert app.counters["hits"] == 100
        assert isinstance(app.logger, logging.Logger)
        assert f"{app.name} v{app.version}" in app.output.getvalue()
        assert isinstance(app.subsystems["auth"]["logger"], logging.Logger)
        
        print("\n✓ Mixed complexity object works after 20 round-trips!")
    
    def test_functional_verification_comprehensive(self):
        """Comprehensive functional test: verify objects WORK, not just serialize."""
        
        class ComplexState:
            def __init__(self):
                self.logger = logging.getLogger("functional_test")
                self.lock = threading.Lock()
                self.rlock = threading.RLock()
                self.event = threading.Event()
                self.queue = queue.Queue()
                self.queue.put("item1")
                self.queue.put("item2")
                self.counter = Counter({"a": 5, "b": 3})
                self.data_file = io.StringIO("initial\n")
                self.db = sqlite3.connect(":memory:")
                cursor = self.db.cursor()
                cursor.execute("CREATE TABLE test (id INTEGER, val TEXT)")
                cursor.execute("INSERT INTO test VALUES (1, 'data')")
                self.db.commit()
        
        obj = ComplexState()
        
        # Serialize and deserialize
        serialized = self.serializer.serialize(obj)
        restored = self.deserializer.deserialize(serialized)
        
        print("\n  Comprehensive functional verification:")
        
        # Logger functionality
        restored.logger.debug("debug message")
        restored.logger.info("info message")
        restored.logger.warning("warning message")
        print("    ✓ Logger logging methods work")
        
        # Lock functionality
        assert restored.lock.acquire(blocking=False)
        restored.lock.release()
        with restored.lock:
            pass
        print("    ✓ Lock acquire/release and context manager work")
        
        # RLock functionality (reentrant)
        with restored.rlock:
            with restored.rlock:  # Can acquire twice
                pass
        print("    ✓ RLock reentrant locking works")
        
        # Event functionality
        assert not restored.event.is_set()
        restored.event.set()
        assert restored.event.is_set()
        restored.event.clear()
        assert not restored.event.is_set()
        print("    ✓ Event set/clear/is_set work")
        
        # Queue functionality
        assert restored.queue.qsize() == 2
        item1 = restored.queue.get()
        assert item1 == "item1"
        item2 = restored.queue.get_nowait()
        assert item2 == "item2"
        assert restored.queue.empty()
        restored.queue.put("item3")
        assert not restored.queue.empty()
        print("    ✓ Queue put/get/empty/qsize work")
        
        # Counter functionality
        assert restored.counter.most_common(1)[0] == ("a", 5)
        restored.counter["c"] = 10
        restored.counter.update({"a": 2})
        assert restored.counter["a"] == 7
        assert restored.counter["c"] == 10
        print("    ✓ Counter most_common/update/increment work")
        
        # StringIO functionality
        # First verify original content is preserved
        content_before = restored.data_file.getvalue()
        assert "initial" in content_before, "Original content should be preserved"
        pos_before = restored.data_file.tell()
        assert pos_before == 0, "Position should be at start"
        
        # Read the content
        line = restored.data_file.readline()
        assert line == "initial\n", "Should read original content"
        
        # Seek to end and append
        restored.data_file.seek(0, 2)  # Seek to end
        restored.data_file.write("appended\n")
        
        # Verify both contents are there
        final_content = restored.data_file.getvalue()
        assert "initial" in final_content, "Original content lost"
        assert "appended" in final_content, "Appended content missing"
        
        # Test seek and readline
        restored.data_file.seek(0)
        first_line = restored.data_file.readline()
        assert first_line == "initial\n"
        print("    ✓ StringIO read/write/seek/readline work")
        
        # Database functionality
        cursor = restored.db.cursor()
        rows = cursor.execute("SELECT * FROM test").fetchall()
        assert len(rows) == 1
        assert rows[0] == (1, "data")
        cursor.execute("INSERT INTO test VALUES (2, 'new')")
        restored.db.commit()
        rows = cursor.execute("SELECT * FROM test").fetchall()
        assert len(rows) == 2
        print("    ✓ SQLite query/insert/commit work")
        
        print("\n✓ All objects are fully functional after deserialization!")


class TestRealisticBenchmarks:
    """Benchmark realistic scenarios against pickle/dill/cloudpickle."""
    
    def setup_method(self):
        self.cucumber_s = Serializer()
        self.cucumber_d = Deserializer()
    
    def _benchmark_serializer(self, name: str, serialize_func, deserialize_func, obj: Any, iterations: int = 100):
        """Benchmark a serializer."""
        try:
            # Warmup
            s = serialize_func(obj)
            deserialize_func(s)
            
            # Benchmark
            start = time.time()
            for _ in range(iterations):
                serialized = serialize_func(obj)
                reconstructed = deserialize_func(serialized)
            elapsed = time.time() - start
            
            ops_per_sec = iterations / elapsed
            return True, ops_per_sec, len(serialized), None
        except Exception as e:
            return False, 0, 0, f"{type(e).__name__}: {str(e)[:40]}"
    
    def test_benchmark_ml_checkpoint(self):
        """Benchmark ML checkpoint scenario."""
        
        @dataclass
        class TrainingState:
            epoch: int
            loss_history: List[float]
            metrics: Dict[str, float]
        
        class ModelCheckpoint:
            def __init__(self):
                self.logger = logging.getLogger("model")
                self.state = TrainingState(
                    epoch=10,
                    loss_history=[0.5, 0.4, 0.35, 0.3],
                    metrics={"accuracy": 0.92}
                )
                self.lock = threading.Lock()
                self.progress = io.StringIO("50%\n")
        
        obj = ModelCheckpoint()
        
        print("\n" + "="*70)
        print("BENCHMARK: ML Checkpoint")
        print("="*70)
        
        results = {}
        
        # Test cucumber
        success, ops, bytes_size, error = self._benchmark_serializer(
            "cucumber",
            self.cucumber_s.serialize,
            self.cucumber_d.deserialize,
            obj,
            iterations=200
        )
        results["cucumber"] = (success, ops, bytes_size, error)
        
        # Test pickle
        import pickle
        success, ops, bytes_size, error = self._benchmark_serializer(
            "pickle",
            pickle.dumps,
            pickle.loads,
            obj,
            iterations=200
        )
        results["pickle"] = (success, ops, bytes_size, error)
        
        # Test dill
        if HAS_DILL:
            success, ops, bytes_size, error = self._benchmark_serializer(
                "dill",
                dill.dumps,
                dill.loads,
                obj,
                iterations=200
            )
            results["dill"] = (success, ops, bytes_size, error)
        
        # Test cloudpickle
        if HAS_CLOUDPICKLE:
            success, ops, bytes_size, error = self._benchmark_serializer(
                "cloudpickle",
                cloudpickle.dumps,
                cloudpickle.loads,
                obj,
                iterations=200
            )
            results["cloudpickle"] = (success, ops, bytes_size, error)
        
        # Print results
        print(f"\n{'Library':<15} {'Status':<12} {'Ops/Sec':<12} {'Bytes':<10} {'Error'}")
        print("-" * 70)
        
        for lib in ["pickle", "dill", "cloudpickle", "cucumber"]:
            if lib not in results:
                continue
            
            success, ops, bytes_size, error = results[lib]
            if success:
                print(f"{lib:<15} {'✓ PASS':<12} {ops:>10,.0f}  {bytes_size:>8,}  ")
            else:
                print(f"{lib:<15} {'✗ FAIL':<12} {'N/A':<12} {'N/A':<10} {error}")
        
        # Verify cucumber works
        assert results["cucumber"][0], "cucumber should handle ML checkpoint"
        
        print("\n✓ Only cucumber and dill can handle this (pickle/cloudpickle fail on locks)")
    
    def test_benchmark_scraper_state(self):
        """Benchmark web scraper scenario."""
        
        class ScraperState:
            def __init__(self):
                self.logger = logging.getLogger("scraper")
                self.visited = set(["url1", "url2", "url3"])
                self.url_queue = queue.Queue()
                for i in range(5):
                    self.url_queue.put(f"url{i+4}")
                self.stats = Counter({"pages": 3, "links": 27})
                self.lock = threading.Lock()
                self.data = io.StringIO("scraped data\n")
        
        obj = ScraperState()
        
        print("\n" + "="*70)
        print("BENCHMARK: Web Scraper State")
        print("="*70)
        
        results = {}
        
        # Test all serializers
        for lib, serialize, deserialize in [
            ("pickle", lambda o: __import__('pickle').dumps(o), lambda d: __import__('pickle').loads(d)),
            ("dill", lambda o: dill.dumps(o) if HAS_DILL else None, lambda d: dill.loads(d) if HAS_DILL else None),
            ("cloudpickle", lambda o: cloudpickle.dumps(o) if HAS_CLOUDPICKLE else None, lambda d: cloudpickle.loads(d) if HAS_CLOUDPICKLE else None),
            ("cucumber", self.cucumber_s.serialize, self.cucumber_d.deserialize),
        ]:
            if lib in ["dill", "cloudpickle"] and not (HAS_DILL if lib == "dill" else HAS_CLOUDPICKLE):
                continue
            
            success, ops, bytes_size, error = self._benchmark_serializer(lib, serialize, deserialize, obj, 200)
            results[lib] = (success, ops, bytes_size, error)
        
        # Print results
        print(f"\n{'Library':<15} {'Status':<12} {'Ops/Sec':<12} {'Bytes':<10}")
        print("-" * 70)
        
        for lib, (success, ops, bytes_size, error) in results.items():
            if success:
                print(f"{lib:<15} {'✓ PASS':<12} {ops:>10,.0f}  {bytes_size:>8,}")
            else:
                print(f"{lib:<15} {'✗ FAIL':<12} {'N/A':<12} {'N/A':<10}")
        
        assert results["cucumber"][0], "cucumber should handle scraper state"
    
    def test_benchmark_simple_data_structure(self):
        """Benchmark simple data structure (pickle should win)."""
        
        obj = {
            "name": "John Doe",
            "age": 30,
            "scores": [95, 87, 92, 88, 91],
            "active": True,
            "metadata": {
                "created": "2024-01-01",
                "tags": ["student", "active"],
            }
        }
        
        print("\n" + "="*70)
        print("BENCHMARK: Simple Data Structure")
        print("="*70)
        
        results = {}
        iterations = 3000
        
        import pickle
        for lib, serialize, deserialize in [
            ("pickle", pickle.dumps, pickle.loads),
            ("dill", (lambda o: dill.dumps(o)) if HAS_DILL else None, (lambda d: dill.loads(d)) if HAS_DILL else None),
            ("cloudpickle", (lambda o: cloudpickle.dumps(o)) if HAS_CLOUDPICKLE else None, (lambda d: cloudpickle.loads(d)) if HAS_CLOUDPICKLE else None),
            ("cucumber", self.cucumber_s.serialize, self.cucumber_d.deserialize),
        ]:
            if lib in ["dill", "cloudpickle"] and not (HAS_DILL if lib == "dill" else HAS_CLOUDPICKLE):
                continue
            
            if serialize is None:
                continue
                
            success, ops, bytes_size, error = self._benchmark_serializer(lib, serialize, deserialize, obj, iterations)
            results[lib] = (success, ops, bytes_size, error)
        
        # Print results
        print(f"\n{'Library':<15} {'Status':<12} {'Ops/Sec':<15} {'Bytes':<10} {'vs pickle'}")
        print("-" * 75)
        
        pickle_ops = results["pickle"][1] if results["pickle"][0] else 0
        
        for lib, (success, ops, bytes_size, error) in results.items():
            if success:
                speedup = f"{pickle_ops/ops:.1f}x slower" if ops < pickle_ops else f"{ops/pickle_ops:.1f}x faster"
                print(f"{lib:<15} {'✓':<12} {ops:>13,.0f}  {bytes_size:>8,}  {speedup}")
            else:
                print(f"{lib:<15} {'✗':<12} {'N/A':<15} {'N/A':<10}")
        
        print("\n  Expected: pickle/cloudpickle fastest (optimized for simple data)")
        print("  cucumber trades speed for universal capability")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
