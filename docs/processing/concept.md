The first rendition of the Process class concept is very complicated.

I want it to be simpler and more intuitive.

Uses my Cerial module to handle data serialization and deserialization.

- User makes a class that inherits from Process
- user defines initial attributes in __init__(), as well as update the self.config subobject.

No more:
- config object
- complicated timing
- complicated configuration

Instead, all configuration is done by the user in the __init__() method using attributes.

- Process splits into 3 parts:

Process: untimed process that runs until it ends itself or is asked to rejoin

```python
# runs until it calls __onfinish__() itself or is asked to rejoin
class MyProcess(Process):
```

What remains:
- __preloop__(), __loop__(), __postloop__()
- respective error classes (PreloopError, MainLoopError, PostLoopError)

Setting up a process

```python
from suitkaise.process import Process

class MyProcess(Process):
    
    def __init__(self):
        self.counter = 0
    
    # called before every __loop__() iteration
    def __preloop__(self):
        print("Preloop")
        self.counter += 1
        

    # this is where the user does their core work
    # this code should NOT loop itself, the engine loops for you
    def __loop__(self):
        print("Loop")
        self.counter += 1
        
    # called after every __loop__() iteration
    def __postloop__(self):
        print("Postloop")
        self.counter += 1

        if self.counter >= 10:
            self.stop()

    # called when self.stop() is called or a limit (time or number of loops) is reached
    def __onfinish__(self):
        print("Onfinish")
        self.counter += 1

    # called after __onfinish__() to return data in a predictable package
    def __result__(self):
        return self.counter

    # called after a section if an error occurs in that section
    # for example: the system would raise a PreloopError that will raise the error it caught. that is what is stored in self.error. that way user can see where in loop error occurred and what the actual error was.
    def __error__(self):
        print(f"Error caught: {self.error}")
        return self.error
        
```

Automatic initialization (no `super().__init__()` needed)

When you inherit from `Process`, you don't need to call `super().__init__()`. The `Process` class uses Python's `__init_subclass__` to automatically wrap your `__init__` method and run the parent's initialization behind the scenes.

```python
# ✅ Just write your __init__ naturally
class MyProcess(Process):
    def __init__(self, data):
        self.data = data
        self.config.num_loops = 10

# ❌ No need for this
class MyProcess(Process):
    def __init__(self, data):
        super().__init__()  # Not required!
        self.data = data
```

This automatic initialization:
- Sets up internal process state (name, status, communication channels, etc.)
- Creates the `self.config` object with default values
- Lets your `__init__` override defaults by simply assigning to `self.config.*`
- Works for all subclasses, even if you inherit from your own Process subclass

How it works under the hood:

```python
class Process:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # Wrap the child's __init__ to auto-call parent setup
        if '__init__' in cls.__dict__:
            original_init = cls.__dict__['__init__']
            
            def wrapped_init(self, *args, **kwargs):
                Process._setup(self)  # Parent initialization
                original_init(self, *args, **kwargs)  # User's __init__
            
            cls.__init__ = wrapped_init
```

This means every class that inherits from `Process` (or a `Process` subclass) automatically gets the parent setup, with zero boilerplate from the user.


Process config options:

```python

# for regular Process objects
class MyProcess(Process):

    def __init__(self):

        # number of loops to run before calling __onfinish__()
        # if this threshold is reached, self.stop() is called
        self.config.num_loops = 10

        # time to run before calling __onfinish__()
        # if this threshold is reached, self.stop() is called
        self.config.join_in = 30.0

        # number of times to restart the process if it crashes before just calling __error__()
        self.config.lives = 10

        # timeout for __preloop__()
        # if this threshold is reached, self.error() is called
        self.config.timeouts.preloop = 30.0 

        # timeout for __loop__()
        # if this threshold is reached, self.error() is called
        self.config.timeouts.loop = 300.0 

        # timeout for __postloop__()
        # if this threshold is reached, self.error() is called
        self.config.timeouts.postloop = 60.0 

        # timeout for __onfinish__()
        # if this threshold is reached, process will be killed
        self.config.timeouts.onfinish = 60.0
```


Creating and rejoining a process

```python
from suitkaise.processing import Process

class MyProcess(Process):

    # ...

# create the process obj
process = MyProcess()

# start the process
# this automatically creates a new process for you using your Process object
process.start()

# wait for the process to finish (blocks until done)
# will raise an error if called from inside the process
process.wait()

# stop the process
# if called from outside the process, this works by sending the stop signal. process checks for stop signal between each part of the loop.
process.stop()

# kill the process without finishing gracefully
# this just kills the process without finishing current and calling __onfinish__()
process.kill()

# get results
try:
    process_result = process.result()
except Exception as e:
    print(f"Error: {e}")

```


Running multiple processes

```python
class Worker(Process):
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.config.num_loops = 5
    
    def __loop__(self):
        # do work
        pass
    
    def __result__(self):
        return f"Worker {self.worker_id} done"

# create multiple processes
processes = [Worker(i) for i in range(5)]

# start all
for p in processes:
    p.start()

# wait for all to finish
for p in processes:
    p.wait()

# collect results
results = [p.result() for p in processes]
```

The wait loop iterates in order, but waiting on an already-finished process returns immediately. So if process 3 finishes before process 0, you'll block on process 0, and when you reach process 3 it returns instantly.

Total wall-clock time = duration of the slowest process (not the sum of all).

```
Timeline example:

Process 0: ████████████░░░░░░░░░░ (finishes at 12s)
Process 1: ████░░░░░░░░░░░░░░░░░░ (finishes at 4s)  
Process 2: ██████████████████████ (finishes at 22s) <- slowest
Process 3: ██████░░░░░░░░░░░░░░░░ (finishes at 6s)
Process 4: ████████░░░░░░░░░░░░░░ (finishes at 8s)

Wait loop:
  p[0].wait() -> blocks 12s
  p[1].wait() -> already done, instant
  p[2].wait() -> blocks 10 more seconds
  p[3].wait() -> already done, instant
  p[4].wait() -> already done, instant

Total time: 22 seconds
```


How to time the process to record statistics

```python
from suitkaise.processing import Process

class MyProcess(Process):
    
    def __init__(self):

        self.custom_timer = sktime.Timer()

        # ...

# automatically use section timers

    @processing.timethis()
    def __preloop__(self):

    @processing.timethis()
    def __loop__(self):

    @processing.timethis()
    def __postloop__(self):

    @processing.timethis()
    def __onfinish__(self):


# manually use custom timers using sktime
from suitkaise import sktime

    def __preloop__(self):
        with sktime.TimeThis(self.custom_timer) as timer:


    def __loop__(self):
        with sktime.TimeThis(self.custom_timer) as timer:


# accessing the times

# a timer is added to timers for every @processing.timethis() decorated function it knows what timer to use.

# each of these acts just like an sktime.Timer instance. you can use all the same methods on it.
self.timers.preloop
self.timers.loop
self.timers.postloop
self.timers.onfinish

# this is a special timer that adds up the most recent time from existing self.timers.preloop, loop, and postloop.
# if one of the timers is not used, the full_loop timer will not use it either.
self.timers.full_loop

# accessing custom timer is the same as accessing any other sktime.Timer instance.

# get the most recent time from the custom timer
self.custom_timer.most_recent
```


Other statistics:

```python
# get the current runthrough of the loop
self.current_lap
```








