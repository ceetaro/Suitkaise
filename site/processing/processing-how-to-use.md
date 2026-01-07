/*

how to use the processing module. this is the default page when entered from the home page "learn more" or nav bar sidebar "processing" link.

*/

rows = 2
columns = 1

# 1.1

title = "How to use `processing`"

# 1.2

text = "
`processing` provides a much simpler way to run Python code in subprocesses. 

Designed to make using multiple processes really easy.

By inheriting from the `Process` class, you can create a well organized process in a class structure.

Since `processing` uses `cerial` (another `suitkaise` module) as its serializer, you can create these process classes with essentially any object you want.

No more `PicklingError: Can't serialize object` errors when you start up your process!

- no more manual serialization
- no more queue management
- lifecycle methods for setup and teardown including error handling
- built in timing
- automatic retries with `lives` system

## `Process` class special methods

Classes that inherit from `Process` have access to 6 special methods.

These methods are what run the actual process when it is created.

Additionally, `__init__` is modified to automatically call `super().__init__()` for you.

In order for `Process` inheriting classes to run correctly, you must implement the `__run__` method.

```python
from suitkaise.processing import Process

class MyProcess(Process):

    def __init__(self):

        # super().__init__() is called automatically for you
        # setup your process here
        # initalize attributes
        # configure Process attributes


    def __prerun__(self):

        # here, you can setup before the main part
        # connect to databases
        # make API calls
        # read files


    def __run__(self): # REQUIRED

        # this is the main part
        # you can just write your code here
        # it repeats for you, no need to write looping code


    def __postrun__(self):

        # this is where you clean up your work
        # close connections
        # add results to attributes

    
    def __onfinish__(self): 

        # this is when you clean up the process
        # calculate summaries
        # save results to files
        # send emails or do other actions


    def __result__(self):

        # this returns the result of the process
        # don't have to worry about confusing returns
        # store your results as instance attributes
        # and return them here


    def __error__(self):

        # this is __result__() when an error occurs

```

## Methods

### `start()`

Starts the process.

```python
p = MyProcess()
p.start()
```

### `wait()`

Blocks until the process finishes.

```python
p = MyProcess()
p.start()

p.wait()

# doesn't get called until p finishes
something_else()
```

### `stop()`

Signals to the process to finish its current run and clean up. 

Does not block (so you can stop other processes without having to wait)

- finishes current run
- calls `__onfinish__()`
- calls `__result__()` or `__error__()` depending on status
- closes

```python
p = MyProcess()
p.start()

# manually signal to stop
p.stop()

p.wait()
```

### `kill()`

Forcefully terminates the process immediately without cleanup.

Do not use this unless something goes wrong (like a process hanging).

- immediately closes
- does not finish current run
- does not call `__onfinish__()`
- does not call `__result__()` or `__error__()`

```python
p = MyProcess()
p.start()
 
p.kill() # Immediate termination

# p.result will be None
```

### `result` property

Retrieves the result from the process.

- blocks if not finished
- raises if error occurred

```python
p = MyProcess()
p.start()

try:
    # blocks until process finishes and returns __result__() output
    data = p.result

except ProcessError as e:
    print(f"{e}")
```

## Configuration

`Process` also has a `config` attribute that allows you to configure the process in the inheriting class.

The config can only be updated in the `__init__()` method.

All values assigned in the code block below are the defaults.

```python
from suitkaise.processing import Process

class MyProcess(Process):

    # CAN ONLY BE UPDATED IN __INIT__
    def __init__(self):

        # None = infinite number of runs
        self.config.runs = None

        # None = no time limit before auto-joining
        self.config.join_in = None

        # 1 = no retries
        self.config.lives = 1

        # None = no timeout
        self.config.timeouts.prerun = None
        self.config.timeouts.run = None
        self.config.timeouts.postrun = None
        self.config.timeouts.onfinish = None
        self.config.timeouts.result = None
        self.config.timeouts.error = None
```

Setting any of these numbers to zero or lower will reset them to the default value.

## Timing

```python
from suitkaise.processing import Process

class MyProcess(Process):

    def __init__(self):

        # ...

    def __prerun__(self):

        # ...
    
    def __run__(self):

        # ...

    def __postrun__(self):

        # ...

    def __onfinish__(self):

        # ...

    def __result__(self):

        # ...

    def __error__(self):

        # ...


p = MyProcess()
p.start()

p.wait()

prerun_timer = p.__prerun__.timer
run_timer = p.__run__.timer
postrun_timer = p.__postrun__.timer
onfinish_timer = p.__onfinish__.timer
result_timer = p.__result__.timer
error_timer = p.__error__.timer

# adds prerun, run, and postrun times together
full_run_timer = p.timer
```

The `p.timer` adds up the times from the `__prerun__`, `__run__`, and `__postrun__` method timers into one value, and records that value. It does this every iteration/run.

All timers are `suitkaise.sktime.Timer` objects, and function exactly the same.

Timers will not be accessible unless you define their respective methods yourself.

## `lives` system

Setting `self.config.lives` to a number greater than 1 will automatically retry the process if an error occurs, as long as there are still lives left.

```python
from suitkaise.processing import Process

class MyProcess(Process):
    def __init__(self):

        # 3 attempts total
        self.config.lives = 3
```

When a process needs to retry, it retries the current run starting from `__prerun__`. (Does not fully reset to run 0)

Using `kill()` will ignore `lives` and immediately terminate the process.

`wait()` will block until the process finishes successfully. It will not return if the process fails and restarts with remaining lives.


## Error Handling

All errors are caught and handled by the process.

If an error occurs, the process will call `__error__()` instead of `__result__()`.

All errors inherit from a `ProcessError` class, and wrap the actual error that happened.

### `ProcessError`

Base class for all process errors.

If an error occurs outside of one of the inherited `Process` methods, it will be wrapped in a `ProcessError`.

### Error Classes

- `PreRunError` - error raised when an error occurs in the `__prerun__` method.

- `RunError` - error raised when an error occurs in the `__run__` method.

- `PostRunError` - error raised when an error occurs in the `__postrun__` method.

- `OnFinishError` - error raised when an error occurs in the `__onfinish__` method.

- `ResultError` - error raised when an error occurs in the `__result__` method.

### Timeout Errors

If a timeout occurs, a `ProcessTimeoutError` will be raised. It contains the section name, timeout value, and current run number.

(start of dropdown)
### Error Examples

```text
Traceback (most recent call last):
  File \"my_script.py\", line 25, in <module>
    result = p.result
             ^^^^^^^^
  ...
suitkaise.processing.RunError: Error in __run__ on run 5

The above exception was caused by:

Traceback (most recent call last):
  File \"my_script.py\", line 14, in __run__
    data = fetch_from_api()
  File \"my_script.py\", line 8, in fetch_from_api
    raise ConnectionError(\"Failed to connect to server\")
ConnectionError: Failed to connect to server
```

```text
suitkaise.processing.ProcessTimeoutError: Timeout in run after 5.0s on run 3
```

(end of dropdown)

### Accessing the Original Error

All `ProcessError` subclasses store the original exception:

```python
try:
    result = p.result
except ProcessError as e:
    print(f\"Process error: {e}\")
    print(f\"Original error: {e.original_error}\")
    print(f\"Run number: {e.current_run}\")

# Output:
# Process error: Error in __run__ on run 5
# Original error: ConnectionError('Failed to connect to server')
# Run number: 5
```





