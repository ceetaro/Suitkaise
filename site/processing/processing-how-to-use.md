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

By inheriting from the `Skprocess` class, you can create a well organized process in a class structure.

Since `processing` uses `cerial` (another `suitkaise` module) as its serializer, you can create these process classes with essentially any object you want.

You can also use the `Pool` class for batch processing.

`Pool` also uses `cerial` for serialization, so you can use it with any object you want, and it also allows you to use `Skprocess` inheriting classes instead of just functions.

No more `PicklingError: Can't serialize object` errors when you start up your process!

- no more manual serialization
- no more queue management
- lifecycle methods for setup and teardown including error handling
- built in timing
- automatic retries with `lives` system

## Lifecycle Methods

Classes that inherit from `Skprocess` have access to 6 lifecycle methods.

These methods are what run the actual process when it is created.

Additionally, `__init__` is modified to automatically call `super().__init__()` for you.

In order for `Skprocess` inheriting classes to run correctly, you must implement the `__run__` method.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    def __init__(self):

        # super().__init__() is called automatically for you
        # setup your process here
        # initalize attributes
        # configure Skprocess attributes


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

Signals to the subprocess to finish its current run and clean up. 

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

```python
class MyProcess(Skprocess):

    def __run__(self):

        if found_what_we_need:
            # exit early
            self.stop()

        else:
            # ...  
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

# p.result() will be None
```

### `tell()`

Sends data to the other process.

If the other process calls `listen()`, it will receive the data from `tell()`.

`tell()` is not a blocking method.

```python
p = MyProcess()
p.start()

# sends "data" to the subprocess
p.tell("some data")

p.wait()
```

```python
class MyProcess(Skprocess):

    def __run__(self):

        self.tell(("i have found a corrupt file", "corrupt_file.txt"))
```

### `listen()`

Blocks until data is received from the other process.

Optional timeout.

```python
corrupt_files = []

p = MyProcess()
p.start()

data = p.listen(timeout=1.0)

if data[0] == "i have found a corrupt file":
    corrupt_files.append(data[1])
```

```python
class MyProcess(Skprocess):

    def __run__(self):

        command = self.listen(timeout=5.0)

        if not command:
            raise ProcessTimeoutError("No command received")
        else:
            run_command(command)
```

### `result()`

Retrieves the result from the process.

- blocks if not finished
- raises if error occurred

```python
p = MyProcess()
p.start()

try:
    # blocks until process finishes and returns __result__() output
    data = p.result()

except ProcessError as e:
    print(f"{e}")
```

## Configuration

`Skprocess` also has a `process_config` attribute that allows you to configure the process in the inheriting class.

The config can only be updated in the `__init__()` method.

All values assigned in the code block below are the defaults.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    # CAN ONLY BE UPDATED IN __INIT__
    def __init__(self):

        # None = infinite number of runs
        self.process_config.runs = None

        # None = no time limit before auto-joining
        self.process_config.join_in = None

        # 1 = no retries
        self.process_config.lives = 1

        # None = no timeout
        self.process_config.timeouts.prerun = None
        self.process_config.timeouts.run = None
        self.process_config.timeouts.postrun = None
        self.process_config.timeouts.onfinish = None
        self.process_config.timeouts.result = None
        self.process_config.timeouts.error = None
```

Setting any of these numbers to zero or lower will reset them to the default value.

## Timing

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

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
full_run_timer = p.process_timer
```

The `p.process_timer` adds up the times from the `__prerun__`, `__run__`, and `__postrun__` method timers into one value, and records that value. It does this every iteration/run.

All timers are `suitkaise.sktime.Timer` objects, and function exactly the same.

Timers will not be accessible unless you define their respective lifecycle methods yourself.

## `lives` system

Setting `self.process_config.lives` to a number greater than 1 will automatically retry the process if an error occurs, as long as there are still lives left.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):
    def __init__(self):

        # 3 attempts total
        self.process_config.lives = 3
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

If an error occurs outside of one of the inherited `Skprocess` methods, it will be wrapped in a `ProcessError`.

### Error Classes

- `PreRunError` - error raised when an error occurs in the `__prerun__` method.

- `RunError` - error raised when an error occurs in the `__run__` method.

- `PostRunError` - error raised when an error occurs in the `__postrun__` method.

- `OnFinishError` - error raised when an error occurs in the `__onfinish__` method.

- `ResultError` - error raised when an error occurs in the `__result__` method.

### Timeout Errors

If a timeout occurs, a `ProcessTimeoutError` will be raised. It contains the section name, timeout value, and current run number.

### Error Examples

```text
Traceback (most recent call last):
  File "my_script.py", line 25, in <module>
    result = p.result()
             ^^^^^^^^
  ...
suitkaise.processing.RunError: Error in __run__ on run 5

The above exception was caused by:

Traceback (most recent call last):
  File "my_script.py", line 14, in __run__
    data = fetch_from_api()
  File "my_script.py", line 8, in fetch_from_api
    raise ConnectionError("Failed to connect to server")
ConnectionError: Failed to connect to server
```

```text
suitkaise.processing.ProcessTimeoutError: Timeout in run after 5.0s on run 3
```

### Accessing the Original Error

All `ProcessError` subclasses store the original exception:

```python
try:
    result = p.result()
except ProcessError as e:
    print(f"Process error: {e}")
    print(f"Original error: {e.original_error}")
    print(f"Run number: {e.current_run}")

# Output:
# Process error: Error in __run__ on run 5
# Original error: ConnectionError('Failed to connect to server')
# Run number: 5
```

## `Pool`

`Pool` allows you to run multiple processes in parallel.

It does 2 things differently.

- uses `cerial` for serialization of complex objects between processes
- allows for the use of the `Skprocess` inheriting classes mentioned above

```python
from suitkaise.processing import Pool

# a class of type ["processing.Skprocess"]
p = MyProcess()
data_set = get_data()

pool = Pool(workers=8)
```

### `map()`

Takes a function and a list of arguments.

Blocks until all processes finish, and then returns a list of results in the same order as the arguments.

```python
results = pool.map(p, data_set)
```

### `imap()`

Returns an iterator of results.

Each result is returned in order. If the next result is not ready, it will block until it is.

```python
def upscale_image_section(image_data):

    # ... upscale image data ...
    return upscaled_image_data

full_image_data = []

# call function to upscale chunk of image data
for result in pool.imap(upscale_image_section, data_set):

    full_image_data.append(result)
```


### `async_map()`

Non-blocking version of `map()`.

It returns immediately, with several methods to check and get the results.

```python
results = pool.async_map(p, data_set)

# check if results are ready
if results.ready():
    # ...

# block and wait for results to be ready but don't get them
results.wait()

# block until results are ready and get them
actual_results = results.get()

# block until results are ready and get them or until timeout
actual_results = results.get(timeout=1.0)
```

#### `unordered_imap()`

Returns an iterator of results.

Each result is returned as it is ready, regardless of order.

Fastest way to get results, but not in order.

```python
# use Skprocess inheriting class UpscaleImage to process each image in data_set
for processed_image in pool.unordered_imap(UpscaleImage, data_set):

    upscaled_images.append(processed_image)
```

### `star()`

Modifier of `map()`, `imap()`, `async_map()`, and `unordered_imap()`.

When used, it makes iterators of tuples spread across multiple arguments instead of the entire tuple being passed as a single argument.

```python
# map - always passes item as single argument
pool.map(fn or Skprocess, [(1, 2), (3, 4)])  # fn((1, 2), ), fn((3, 4), )

# star map - unpacks tuples as arguments (but only tuples!)
pool.star().map(fn or Skprocess, [(1, 2), (3, 4)])  # fn(1, 2), fn(3, 4)
```

```python
# imap - always passes item as single argument
for result in pool.imap(fn or Skprocess, [(1, 2), (3, 4)]): # fn((1, 2), ), fn((3, 4), )

# star imap - unpacks tuples as arguments (but only tuples!)
for result in pool.star().imap(fn or Skprocess, [(1, 2), (3, 4)]): # fn(1, 2), fn(3, 4)
```

### Using `Pool` with `Skprocess` inheriting classes

When using `Pool` with `Skprocess` inheriting classes, pass the class itself (not an instance) as the first argument to `map()` or `imap()`.

The second argument will be an argument (or arguments) to `__init__()`.

Classes run as they would normally, including ones that don't have a run or time limit (you can still use `stop()` to stop them in `Pools`).

```python
class UpscaleImage(Skprocess):

    def __init__(self, image):
        self.image_data = image

for result in pool.unordered_imap(UpscaleImage, data_set):

    upscaled_images.append(result)
```

```python
class ColorImage(Skprocess):

    def __init__(self, image, color, percent_change):
        self.image_data = image
        self.color = color
        self.percent_change = percent_change

colored_images = pool.star().map(ColorImage, zip(images, colors, percent_changes))
```