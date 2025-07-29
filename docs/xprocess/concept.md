# XProcess Concept

## What is xprocess (and skthreading)?

xprocess is suitkaise's process and thread manager. It allows you to create new processes similar to multiprocessing, but also allows you to add tasks to complete when initializing every new process/thread. Additionally, it will automatically sync serializable data to other processes (through the process that contains what is right now called "top level storage"). It also automatically handles process crashes or blocks due to errors, is able to report processes' statuses, recall processes, auto create background threads in processes, etc.

## Core Architecture

### Process Setup Options

There are two main approaches to setting up processes:

#### Option 1: Context Manager Approach
Using `xp.ProcessSetup()` with context managers for different lifecycle phases:
- `xp.OnStart()` - Results added to config going into main function kwargs
- `xp.BeforeLoop()` - Results added to this loop's kwargs  
- `xp.AfterLoop()` - Results optionally added to next loop kwargs
- `xp.OnFinish()` - Final cleanup and processing

#### Option 2: Class-Based Approach
Inheriting from `Process` class with dunder methods:
- `__init__()` - Process setup
- `__beforeloop__()` - Called before every loop iteration
- `__afterloop__()` - Called after every loop iteration  
- `__onfinish__()` - Called when process finishes

## Process Configuration

Processes can be configured with special kwargs:
- `join_in`: Join (end process) in n seconds, None being no auto join
- `join_after`: Join after n function loops, None being no auto join

## Integration with SKTree

xprocess integrates seamlessly with sktree for global storage:
- Automatic data syncing between processes
- Path-based organization of process data
- Metadata tracking for process cleanup
- Cross-process communication through shared storage

## Threading Integration

SKThreading provides easy threading and thread management:
- Create single threads or thread pools
- Configurable looping behavior
- Graceful thread termination with `rejoin()`
- Same lifecycle approach as processes but for threads

## Examples

### Context Manager Approach

```python
# file name: my_file1.py
from suitkaise import xprocess, sktree
from my_events import create_event_bus

# initialize cross processing
xp = xprocess.CrossProcessing()
# get or create global storage, organized into containers that follow your project structure
tree = sktree.connect()

# create a new process
# params: name, func, func args, func kwargs
# we have some special kwargs that can be added
ui_process_config = {
    "join_in": None, # join (end process) in n seconds, None being no auto join (user has to join manually)
    "join_after": None, # join after n function loops, None being no auto join
}

# args and kwargs can be added, but they weren't in this case. I am just displaying that it takes these.
ui_process = xp.create_process("UI_handler", ui_loop(), args=None, kwargs=ui_process_config)

# add tasks that processes have to run before main work
with xp.ProcessSetup() as setup:
    # results here are added to config going into main function kwargs
    with xp.OnStart() as start:
        # create an event bus in another thread
        bus = create_event_bus()

        process_name = xp.get_process_name()
        pid = xp.get_process_id()
        process_metadata = {
            "process_name": process_name,
            "pid": pid,
            "remove_on_process_join": True
        }

    # results here are added to this loop's kwargs
    with xp.BeforeLoop() as before:
        current = xp.get_current_loop()
        loop_time_result_name = f"{process_name}-{current}" # added to kwargs of main func
        to_add = {
            "current_loop": current,
            "loop_time_result_name": loop_time_result_name
        }
        before.add_these(to_add)

    # results optionally added to next loop kwargs
    with xp.AfterLoop(add_for_next=False) as after:
        time = xp.get_last_loop_time()
        tree.add(name=loop_time_result_name, value=time, path="my_file1", metadata=process_metadata)
        after.add({"last_loop_time": time})

    with xp.OnFinish() as finish:
        to_select = {"pid": pid, "remove_on_process_join": True}
        tree.select_all_with(to_select, "my_file1")
        # dummy function that handles loop time stats
        report = generate_loop_time_report()
        report_name = f"{process_name} loop times report"
        # add to project root container
        tree.add_to_root(report_name, report)
        tree.remove_selected() # and "deselects"
        cleanup()

# NOTE: if tree.add() has no path argued, defaults to caller file path (in this case, my_file1's path)

setup1 = setup.build() # returns the data in workable form from the context manager

# creating a process including setup1 from xp.ProcessSetup
ui_process = xp.create_process("UI_handler", ui_loop(), setup1, args=None, kwargs=ui_process_config)
```

### Class-Based Approach

```python
# file name: my_file1.py
from suitkaise import xprocess, Process
from suitkaise import sktree
from my_events import create_event_bus
from my_memory import mem_usage

# initialize dummy memory usage tracker
memu = mem_usage.MemoryUsageTracker()
# initialize cross processing
xp = xprocess.CrossProcessing()
# get or create global storage, organized into containers that follow your project structure
_TREE = sktree.connect()

# create a new process
# params: name, func, func args, func kwargs
# we have some special kwargs that can be added
ui_process_config = {
    "join_in": None, # join (end process) in n seconds, None being no auto join (user has to join manually)
    "join_after": None, # join after n function loops, None being no auto join
}

# args and kwargs can be added, but they weren't in this case. I am just displaying that it takes these.
ui_process = xp.create_process("UI_handler", ui_loop(), args=None, kwargs=ui_process_config)

# add tasks that processes have to run before main work (Process is xprocess.Process)
class UiProcess(Process):

    # this is the process setup, which is run before the main function
    def __init__(self, name, num_loops=None):
        super().__init__(name, num_loops)
        # self.name = process_name # initialized in Process
        # self.pid = Process.get_pid() # initialized in Process
        # self.current_loop = Process.get_current_loop() # initialized in Process
        # self.num_loops = num_loops otherwise an infinity marker # initialized in Process
        # self.metadata = {
        #     "name": self.process_name,
        #     "pid": self.pid,
        #     "current_loop": self.current_loop,
        #     "num_loops": self.num_loops,
        #     "remove_on_process_join": True
        # } # initialized in Process

        self.tree = sktree.connect()  # connect to global storage tree separately from module?
        # we could also do: self.tree = _TREE possibly...

        self.loop_time_result_name = f"{self.name}-{self.get_current_loop}"

        # create an event bus in another thread
        self.bus = create_event_bus()

    # this is called automatically before every "loop"
    # when __beforeloop__ is called, it:
    # - starts the current loop timer
    def __beforeloop__(self):
        self.loop_time_result_name = f"{self.name}-{self.get_current_loop}"

        # example functionality
        if self.last_loop:
            print(f"This is the last loop before process join.")

    # optionally, you can add the main function directly here using __loop__

    # when __afterloop__ is called, it:
    # - finishes the current loop, increasing the loop counter and recording the loop time
    def __afterloop__(self):
        time = self.last_loop_time
        self.tree.add(
            name=loop_time_result_name, 
            value=time, 
            path="my_file1", 
            metadata=process_metadata
        )

        if memu.over_limit():
            print(f"Memory usage exceeded limit in process {self.name}.")
            self.rejoin()  # gracefully end the process if memory usage is too high
            # if self.rejoin() is called anywhere, it will not end the execution before calling __afterloop__ one last time and then __onfinish__. to forcefully end the process, use self.force_finish().

    # __onfinish__ is called when the process finishes its last loop
    def __onfinish__(self):
        # refine search to only entries with this pid and remove_on_process_join set to True
        to_select = {"pid": pid, "remove_on_process_join": True}

        # select all entries with this metadata that are in myfile1's tree branch
        tree.select_all_with(to_select, "my_file1")

        # dummy function that handles loop time stats
        # default name: "{self.name} loop times report"
        report = self.generate_loop_time_report("custom_name_if_you_want")

        # add to project root container
        tree.add_to_root(report_name, report)
        tree.remove_selected() # and "deselects"

        # finally, cleanup and gracefully join the process
        # we ASSUME that all data you would like to keep has already been stored somewhere else, so we clean up pretty aggressively
        self.cleanup()

# NOTE: if tree.add() has no path argued, defaults to caller file path (in this case, my_file1's path)

setup1 = UiProcess("UI_handler")

# creating a process including setup1 from UiProcess
ui_process = xp.create_process(ui_loop(), setup1, args=None, kwargs=ui_process_config)
```

### SKThreading Example

```python
from suitkaise import skthreading, skglobals
from random import randint

def do_work(value1: int, value2: int):
    result = convert_to_word_form(value1) + " " + convert_to_word_form(value2)
    return result

# the user can decide if they want the thread to loop or not, and we handle looping, joining looping threads, looping a certain number of times, etc internally and gracefully. 
with skthreading.ThreadSetup as setup:
    setup.loop_infinitely = True

    with skthreading.OnStart() as start:
        list_of_results = []
        value1 = None
        value2 = None

    with skthreading.BeforeLoop() as before:
        if value1 is None:
            value1 = randint(1, 99999)
        if value2 is None:
            value2 = randint(1, 99999)

    with skthreading.AfterLoop() as after:
        # append last result to list of results
        skthreading.add_last_result(list_of_results)

    with skthreading.OnFinish() as finish:
        # add list of results to global storage
        skglobals.create(list_of_results)

dw_thread = skthreading.create_thread(name="do_work_thread", func=do_work, setup=setup.build(), args=None, kwargs=None)

# end an infinite looping thread or a finite looping thread early and gracefully (let it end its current loop)
skthreading.rejoin(dw_thread)
```

### Alternative Class-Based Threading

```python
# something like this might be a better/clearer idea!
class DoWorkThread(skthreading.SKThread):

    self.loop_infinitely = True

    def __on_start__(self):
        self.list_of_results = []
        self.value1 = None
        self.value2 = None

    def __before_loop__(self):
        if self.value1 is None:
            self.value1 = randint(1, 99999)
        if self.value2 is None:
            self.value2 = randint(1, 99999)

    # ...
```