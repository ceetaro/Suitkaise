# test tell() and listen() inter-process communication

import time
import pytest  # type: ignore

from suitkaise.processing import Process
from suitkaise import sktime


# =============================================================================
# Basic tell/listen Tests
# =============================================================================

class TestBasicTellListen:
    """Tests for basic tell() and listen() functionality."""
    
    def test_parent_tells_subprocess_listens(self, reporter):
        """Parent can send data to subprocess with tell()."""
        
        class ListenerProcess(Process):
            def __init__(self):
                self.received_data = None
                self.config.runs = 1
            
            def __run__(self):
                # Wait for data from parent
                self.received_data = self.listen(timeout=2.0)
            
            def __result__(self):
                return self.received_data
        
        p = ListenerProcess()
        p.start()
        
        # Give subprocess time to start listening
        time.sleep(0.1)
        
        # Send data to subprocess
        p.tell("hello from parent")
        
        p.wait()
        result = p.result()
        
        reporter.add(f"  sent: 'hello from parent'")
        reporter.add(f"  received: {result}")
        
        assert result == "hello from parent"
    
    def test_subprocess_tells_parent_listens(self, reporter):
        """Subprocess can send data to parent with tell()."""
        
        class TellerProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                # Send data back to parent
                self.tell("hello from subprocess")
            
            def __result__(self):
                return "done"
        
        p = TellerProcess()
        p.start()
        
        # Wait for data from subprocess
        data = p.listen(timeout=2.0)
        
        p.wait()
        
        reporter.add(f"  subprocess sent: 'hello from subprocess'")
        reporter.add(f"  parent received: {data}")
        
        assert data == "hello from subprocess"
    
    def test_bidirectional_communication(self, reporter):
        """Parent and subprocess can exchange messages both ways."""
        
        class EchoProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                # Receive from parent
                data = self.listen(timeout=2.0)
                # Echo back with modification
                self.tell(f"echo: {data}")
            
            def __result__(self):
                return "done"
        
        p = EchoProcess()
        p.start()
        
        # Give subprocess time to start listening
        time.sleep(0.1)
        
        # Send to subprocess
        p.tell("ping")
        
        # Receive response
        response = p.listen(timeout=2.0)
        
        p.wait()
        
        reporter.add(f"  parent sent: 'ping'")
        reporter.add(f"  parent received: {response}")
        
        assert response == "echo: ping"
    
    def test_multiple_messages(self, reporter):
        """Multiple messages can be exchanged."""
        
        class MultiMessageProcess(Process):
            def __init__(self):
                self.messages_received = []
                self.config.runs = 3
            
            def __run__(self):
                # On each run, listen for a message and echo it
                data = self.listen(timeout=2.0)
                if data:
                    self.messages_received.append(data)
                    self.tell(f"got: {data}")
            
            def __result__(self):
                return self.messages_received
        
        p = MultiMessageProcess()
        p.start()
        
        messages = ["msg1", "msg2", "msg3"]
        responses = []
        
        for msg in messages:
            time.sleep(0.05)  # Let subprocess reach listen()
            p.tell(msg)
            response = p.listen(timeout=2.0)
            responses.append(response)
        
        p.wait()
        result = p.result()
        
        reporter.add(f"  sent messages: {messages}")
        reporter.add(f"  received responses: {responses}")
        reporter.add(f"  subprocess received: {result}")
        
        assert result == messages
        assert responses == [f"got: {msg}" for msg in messages]


# =============================================================================
# Complex Data Types
# =============================================================================

class TestTellListenDataTypes:
    """Tests for various data types in tell/listen."""
    
    def test_tell_listen_dict(self, reporter):
        """Can send and receive dictionaries."""
        
        class DictProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                data = self.listen(timeout=2.0)
                # Modify and send back
                data["processed"] = True
                data["count"] += 1
                self.tell(data)
            
            def __result__(self):
                return "done"
        
        p = DictProcess()
        p.start()
        
        time.sleep(0.1)
        p.tell({"count": 5, "name": "test"})
        
        response = p.listen(timeout=2.0)
        
        p.wait()
        
        reporter.add(f"  sent: {{'count': 5, 'name': 'test'}}")
        reporter.add(f"  received: {response}")
        
        assert response["count"] == 6
        assert response["processed"] == True
        assert response["name"] == "test"
    
    def test_tell_listen_list(self, reporter):
        """Can send and receive lists."""
        
        class ListProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                data = self.listen(timeout=2.0)
                # Double each element
                self.tell([x * 2 for x in data])
            
            def __result__(self):
                return "done"
        
        p = ListProcess()
        p.start()
        
        time.sleep(0.1)
        p.tell([1, 2, 3, 4, 5])
        
        response = p.listen(timeout=2.0)
        
        p.wait()
        
        reporter.add(f"  sent: [1, 2, 3, 4, 5]")
        reporter.add(f"  received: {response}")
        
        assert response == [2, 4, 6, 8, 10]
    
    def test_tell_listen_tuple(self, reporter):
        """Can send and receive tuples."""
        
        class TupleProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                data = self.listen(timeout=2.0)
                # Echo back the tuple
                self.tell(data)
            
            def __result__(self):
                return "done"
        
        p = TupleProcess()
        p.start()
        
        time.sleep(0.1)
        sent = (1, "two", 3.0, None)
        p.tell(sent)
        
        response = p.listen(timeout=2.0)
        
        p.wait()
        
        reporter.add(f"  sent: {sent}")
        reporter.add(f"  received: {response}")
        
        assert response == sent
    
    def test_tell_listen_nested_data(self, reporter):
        """Can send and receive nested data structures."""
        
        class NestedProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                data = self.listen(timeout=2.0)
                self.tell(data)
            
            def __result__(self):
                return "done"
        
        p = NestedProcess()
        p.start()
        
        time.sleep(0.1)
        sent = {
            "users": [
                {"name": "Alice", "scores": [95, 87, 92]},
                {"name": "Bob", "scores": [88, 91, 85]},
            ],
            "metadata": {
                "version": (1, 2, 3),
                "active": True,
            }
        }
        p.tell(sent)
        
        response = p.listen(timeout=2.0)
        
        p.wait()
        
        reporter.add(f"  sent nested data structure")
        reporter.add(f"  received matches: {response == sent}")
        
        assert response == sent


# =============================================================================
# Timeout Behavior
# =============================================================================

class TestListenTimeout:
    """Tests for listen() timeout behavior."""
    
    def test_listen_timeout_returns_none(self, reporter):
        """listen() with timeout returns None if no data arrives."""
        
        class TimeoutProcess(Process):
            def __init__(self):
                self.config.runs = 1
                self.timed_out = False
            
            def __run__(self):
                # Nobody will send data, so this should timeout
                result = self.listen(timeout=0.1)
                if result is None:
                    self.timed_out = True
            
            def __result__(self):
                return self.timed_out
        
        p = TimeoutProcess()
        p.start()
        
        # Don't send anything
        
        p.wait()
        result = p.result()
        
        reporter.add(f"  subprocess listen timed out: {result}")
        
        assert result == True
    
    def test_parent_listen_timeout(self, reporter):
        """Parent's listen() returns None on timeout."""
        
        class SilentProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                # Don't send anything
                time.sleep(0.2)
            
            def __result__(self):
                return "done"
        
        p = SilentProcess()
        p.start()
        
        # Try to listen but subprocess won't send anything
        result = p.listen(timeout=0.1)
        
        reporter.add(f"  parent listen with timeout=0.1s")
        reporter.add(f"  result: {result}")
        
        assert result is None
        
        p.wait()


# =============================================================================
# Real-World Use Cases
# =============================================================================

class TestTellListenUseCases:
    """Real-world use cases for tell/listen."""
    
    def test_progress_reporting(self, reporter):
        """Subprocess reports progress to parent."""
        
        class ProgressProcess(Process):
            def __init__(self, total_items):
                self.total_items = total_items
                self.config.runs = total_items
            
            def __run__(self):
                # Report progress
                progress = (self._current_run + 1) / self.total_items * 100
                self.tell({"progress": progress, "item": self._current_run})
                time.sleep(0.01)  # Simulate work
            
            def __result__(self):
                return "complete"
        
        p = ProgressProcess(total_items=5)
        p.start()
        
        progress_reports = []
        for _ in range(5):
            report = p.listen(timeout=2.0)
            if report:
                progress_reports.append(report)
        
        p.wait()
        
        reporter.add(f"  received {len(progress_reports)} progress reports")
        for r in progress_reports:
            reporter.add(f"    item {r['item']}: {r['progress']:.0f}%")
        
        assert len(progress_reports) == 5
        assert progress_reports[-1]["progress"] == 100
    
    def test_command_response_pattern(self, reporter):
        """Parent sends commands, subprocess responds."""
        
        class CommandProcess(Process):
            def __init__(self):
                self.state = 0
            
            def __run__(self):
                command = self.listen(timeout=1.0)
                
                if command is None:
                    return
                
                if command == "get":
                    self.tell(self.state)
                elif command == "increment":
                    self.state += 1
                    self.tell("ok")
                elif command == "stop":
                    self.tell("stopping")
                    self.stop()
                else:
                    self.tell(f"unknown: {command}")
            
            def __result__(self):
                return self.state
        
        p = CommandProcess()
        p.start()
        
        time.sleep(0.1)
        
        # Send commands
        commands = ["get", "increment", "increment", "get", "stop"]
        responses = []
        
        for cmd in commands:
            p.tell(cmd)
            response = p.listen(timeout=1.0)
            responses.append(response)
        
        p.wait()
        final_state = p.result()
        
        reporter.add(f"  commands: {commands}")
        reporter.add(f"  responses: {responses}")
        reporter.add(f"  final state: {final_state}")
        
        assert responses[0] == 0  # Initial get
        assert responses[1] == "ok"  # First increment
        assert responses[2] == "ok"  # Second increment
        assert responses[3] == 2  # Get after increments
        assert responses[4] == "stopping"
        assert final_state == 2
    
    def test_error_notification(self, reporter):
        """Subprocess notifies parent of errors via tell()."""
        
        class ErrorNotifyProcess(Process):
            def __init__(self, items):
                self.items = items
                self.config.runs = len(items)
            
            def __run__(self):
                item = self.items[self._current_run]
                
                try:
                    if item < 0:
                        raise ValueError(f"Negative value: {item}")
                    self.tell({"status": "ok", "item": item, "result": item ** 2})
                except Exception as e:
                    self.tell({"status": "error", "item": item, "error": str(e)})
            
            def __result__(self):
                return "complete"
        
        items = [1, 2, -3, 4, -5]
        p = ErrorNotifyProcess(items)
        p.start()
        
        notifications = []
        for _ in range(len(items)):
            notif = p.listen(timeout=2.0)
            if notif:
                notifications.append(notif)
        
        p.wait()
        
        reporter.add(f"  processed items: {items}")
        reporter.add(f"  notifications:")
        for n in notifications:
            reporter.add(f"    {n}")
        
        errors = [n for n in notifications if n["status"] == "error"]
        oks = [n for n in notifications if n["status"] == "ok"]
        
        assert len(errors) == 2  # -3 and -5
        assert len(oks) == 3  # 1, 2, 4


# =============================================================================
# Edge Cases
# =============================================================================

class TestTellListenEdgeCases:
    """Edge cases for tell/listen."""
    
    def test_tell_before_subprocess_listens(self, reporter):
        """Data sent before subprocess listens is queued."""
        
        class DelayedListenProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                # Delay before listening
                time.sleep(0.2)
                data = self.listen(timeout=1.0)
                self.tell(f"got: {data}")
            
            def __result__(self):
                return "done"
        
        p = DelayedListenProcess()
        p.start()
        
        # Send immediately (before subprocess starts listening)
        p.tell("early message")
        
        # Wait for response
        response = p.listen(timeout=2.0)
        
        p.wait()
        
        reporter.add(f"  sent: 'early message' (before subprocess listening)")
        reporter.add(f"  received: {response}")
        
        assert response == "got: early message"
    
    def test_tell_none_value(self, reporter):
        """Can send None as a value."""
        
        class NoneProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                data = self.listen(timeout=2.0)
                self.tell(data)
            
            def __result__(self):
                return "done"
        
        p = NoneProcess()
        p.start()
        
        time.sleep(0.1)
        p.tell(None)
        
        response = p.listen(timeout=2.0)
        
        p.wait()
        
        reporter.add(f"  sent: None")
        reporter.add(f"  received: {response}")
        reporter.add(f"  is None: {response is None}")
        
        # Note: This tests if None can be distinguished from timeout
        # The response should be None because we sent None
        assert response is None
    
    def test_rapid_fire_messages(self, reporter):
        """Many messages sent rapidly are all received."""
        
        class RapidReceiver(Process):
            def __init__(self):
                self.messages = []
                self.config.runs = 10
            
            def __run__(self):
                data = self.listen(timeout=0.5)
                if data is not None:
                    self.messages.append(data)
            
            def __result__(self):
                return self.messages
        
        p = RapidReceiver()
        p.start()
        
        # Send 10 messages rapidly
        for i in range(10):
            time.sleep(0.02)  # Small delay
            p.tell(f"msg_{i}")
        
        p.wait()
        result = p.result()
        
        reporter.add(f"  sent 10 messages rapidly")
        reporter.add(f"  received: {len(result)} messages")
        reporter.add(f"  all present: {len(result) == 10}")
        
        assert len(result) == 10
        assert result == [f"msg_{i}" for i in range(10)]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])

