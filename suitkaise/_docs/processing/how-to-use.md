# How to use `processing`

`processing` provides a much simpler way to run Python code across multiple processes. 

It contains 3 features -- `Skprocess`, `Share`, and `Pool`.

`Skprocess` turns complicated process code into a simple class structure.

`Share` allows you to share data between processes with ease.

`Pool` is for quick and flexible batch processing.

All 3 of them are built with `cerial`, a custom engine that handles an expansive range of objects that `pickle`, `cloudpickle`, and even `dill` cannot.


## `Skprocess`

By inheriting from the `Skprocess` class, you can create a well organized process in a class structure.

Since `processing` uses `cerial` (another `suitkaise` module) as its serializer, you can create these process classes with essentially any object you want.

No more `PicklingError: Can't serialize object` errors when you start up your process.

- no more manual serialization
- no more queue management
- lifecycle methods for setup and teardown including error handling
- built in timing
- automatic retries with `lives` system
- automatically supports `Share`

### Lifecycle Methods

Classes that inherit from `Skprocess` have access to 6 lifecycle methods.

These methods are what run the actual process when it is created.

Additionally, `__init__` is modified to automatically call internal setup for you.

In order for `Skprocess` inheriting classes to run correctly, you must implement the `__run__` method.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    def __init__(self):

        # internal setup runs automatically for you
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


    def __result__(self): # If you don't define this, your process will always return None

        # this returns the result of the process
        # don't have to worry about confusing returns
        # store your results as instance attributes
        # and return them here


    def __error__(self):

        # this is __result__() when an error occurs
        # allows for custom return behavior when an error occurs
```

### Methods

#### `start()`

Starts the process.

```python
p = MyProcess()
p.start()
```

#### `run()`

Starts the process, waits for completion, and returns the result.

```python
p = MyProcess()
result = p.run()
```

#### `wait()`

Blocks until the process finishes.

```python
p = MyProcess()
p.start()

p.wait()

# doesn't get called until p finishes
something_else()
```

```python
# with timeout - returns False if timeout reached
finished = p.wait(timeout=10.0)
```


##### `sk` Modifiers

```python
# async - returns coroutine for await
finished = await p.wait.asynced()()
```

`wait()` does not support `retry()`, `timeout()`, or `background()` modifiers.


#### `stop()`

Signals to the subprocess to finish its current run and clean up. 

The subprocess can also call `stop()` itself!

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

Subprocess stops when it encounters a `self.stop()` call from either side.
```python
class MyProcess(Skprocess):

    def __run__(self):

        if found_what_we_need:
            # exit early
            self.stop()

        else:
            # ...  
```

#### `kill()`

Forcefully terminates the process immediately without cleanup.

Do not use this unless something goes wrong (like a process hanging).

- immediately closes
- does not finish current run
- does not call `__onfinish__()`
- does not call `__result__()` or `__error__()`
- does not add a result for the parent to retrieve

```python
p = MyProcess()
p.start()
 
p.kill() # immediate termination

# p.result() will be None
```

#### `tell()`

Sends data to the other process using `cerial` serialization.

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

#### `listen()`

Blocks until data is received from the other process.

```python
corrupt_files = []

p = MyProcess()
p.start()

data = p.listen()

if data[0] == "i have found a corrupt file":
    corrupt_files.append(data[1])
```

```python
class MyProcess(Skprocess):

    def __run__(self):

        command = self.listen(timeout=5.0)

        if not command:
            raise TimeoutError("No command received")
        else:
            run_command(command)
```

```python
# with timeout - returns None if timeout reached
data = p.listen(timeout=5.0)
```


##### `sk` Modifiers

`background()`

```python
# background - returns Future immediately
future = p.listen.background()()
data = future.result()  # blocks here


# async - returns coroutine for await
data = await p.listen.asynced()()
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

#### `sk` Modifiers

```python
# with timeout - raises ResultTimeoutError if exceeded
data = p.result.timeout(10.0)()


# background - returns Future immediately
future = p.result.background()()
data = future.result()  # blocks here


# async - returns coroutine for await
data = await p.result.asynced()()
```

`result()` does not support `retry()`.

## Configuration

`Skprocess` also has a `process_config` attribute that allows you to configure the process in the inheriting class.

The config can only be updated in the `__init__()` method, and it already exists before your `__init__()` runs.

All values assigned in the code block below are the defaults.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    # can ONLY be updated in __init__
    def __init__(self):

        # none = infinite number of runs
        self.process_config.runs = None

        # none = no time limit before auto-joining
        self.process_config.join_in = None

        # 1 = no retries
        self.process_config.lives = 1

        # none = no timeout
        self.process_config.timeouts.prerun = None
        self.process_config.timeouts.run = None
        self.process_config.timeouts.postrun = None
        self.process_config.timeouts.onfinish = None
        self.process_config.timeouts.result = None
        self.process_config.timeouts.error = None
```

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

The `process_timer` adds up the times from the `__prerun__`, `__run__`, and `__postrun__` method timers into one value, and records that value. It does this every iteration/run.

All timers are `suitkaise.timing.Sktimer` objects, and function exactly the same.

Timers will not be accessible unless you define their respective lifecycle methods yourself.

## `lives` system

Setting `self.process_config.lives` to a number greater than 1 will automatically retry the process if an error occurs, as long as there are still lives left.

Retries restart from end of the latest successful run, not from the beginning.

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

- `ErrorHandlerError` - error raised when an error occurs in the `__error__` method itself.

### Timeout Errors

If a lifecycle timeout occurs, a `ProcessTimeoutError` will be raised. It contains the section name, timeout value, and current run number.

If a modifier timeout occurs via `result().timeout(...)`, a `ResultTimeoutError` will be raised. Pool timeouts raise `TimeoutError`.

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

# output:
# Process error: Error in __run__ on run 5
# Original error: ConnectionError('Failed to connect to server')
# Run number: 5
```

## `Share`

`Share` lets you share data between processes with ease.

Works with `Skprocess` inheriting classes and uses `cerial` for serialization of complex objects.

It routes all writes through a single coordinator, and ensures reads wait until all writes that are still "sharing" have completed.

Super simple - just create the instance and add objects to it, then pass it to subprocesses when you make them.

```python
from suitkaise.processing import Share, Skprocess
from suitkaise import timing

class Worker(Skprocess):

    def __init__(self, share):
        self.share = share

    def __run__(self):
        self.share.counter += 1
        self.share.timer.add_time(0.1)

        if self.share.counter >= 100:
            self.stop()


share = Share()  # starts automatically

share.timer = timing.Sktimer()
share.counter = 0

for _ in range(10):
    worker = Worker(share)
    worker.start()
    
    while share.counter < 100:
        timing.sleep(0.1)

for _ in range(10):
    worker.wait()

final_count = share.counter

# stop sharing
share.exit()

# start sharing again
share.start()

# clear the share of all objects
share.clear()
```

## `Pool`

`Pool` allows you to run multiple processes in parallel.

It does 3 things differently from other process pool libraries.

- uses `cerial` for serialization of complex objects between processes
- allows for the use of `Skprocess` inheriting classes as well as functions
- super flexible mapping patterns using modifiers

```python
from suitkaise.processing import Pool

pool = Pool(workers=8)
```


### `map()`

Takes a function or `Skprocess` class and a list of arguments.

Blocks until all processes finish, and then returns a list of results in the same order as the arguments.


```python
results = pool.map(MyProcess, data_set)
```

#### `sk` Modifiers

```python
# with timeout - raises TimeoutError if exceeded
results = pool.map.timeout(30.0)(MyProcess, data_set)


# background - returns Future immediately
future = pool.map.background()(MyProcess, data_set)
results = future.result()  # blocks here


# async - returns coroutine for await
results = await pool.map.asynced()(MyProcess, data_set)
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

#### `sk` Modifiers

```python
# with timeout - raises TimeoutError if exceeded
for result in pool.imap.timeout(30.0)(upscale_image_section, data_set):
    full_image_data.append(result)


# background - returns Future with list
future = pool.imap.background()(upscale_image_section, data_set)
full_image_data.extend(future.result())


# async - returns list for await
results = await pool.imap.asynced()(upscale_image_section, data_set)
full_image_data.extend(results)
```

### `unordered_imap()`

Returns an iterator of results.

Each result is returned as it is ready, regardless of order.

Fastest way to get results, but not in order.

```python
# use Skprocess inheriting class UpscaleImage to process each image in data_set
for processed_image in pool.unordered_imap(UpscaleImage, data_set):

    upscaled_images.append(processed_image)
```

#### `sk` Modifiers

```python
# with timeout - raises TimeoutError if exceeded
for result in pool.unordered_imap.timeout(30.0)(UpscaleImage, data_set):
    upscaled_images.append(result)


# background - returns Future with list
future = pool.unordered_imap.background()(UpscaleImage, data_set)
upscaled_images.extend(future.result())


# async - returns list for await
results = await pool.unordered_imap.asynced()(UpscaleImage, data_set)
upscaled_images.extend(results)
```

### `star()`

Modifier of `map()`, `imap()`, and `unordered_imap()`.

When used, it makes iterators of tuples spread across multiple arguments instead of the entire tuple being passed as a single argument.

```python
# map - always passes item as single argument
pool.map(fn or Skprocess, [(1, 2), (a, b)])  # fn((1, 2), ), fn((a, b), )

# star map - unpacks tuples as arguments (but only tuples!)
pool.star().map(fn or Skprocess, [(1, 2), (a, b)])  # fn(1, 2), fn(a, b)
```

```python
# imap - always passes item as single argument
for result in pool.imap(fn or Skprocess, [(1, 2), (a, b)]): # fn((1, 2), ), fn((a, b), )

# star imap - unpacks tuples as arguments (but only tuples!)
for result in pool.star().imap(fn or Skprocess, [(1, 2), (a, b)]): # fn(1, 2), fn(a, b)
```

### Using `Pool` with `Skprocess` inheriting classes

When using `Pool` with `Skprocess` inheriting classes, pass the class itself (not an instance) as the first argument to `map()` or `imap()`.

The second argument will be an argument (or arguments) to `__init__()`.

Classes run as they would normally, including ones that don't have a run or time limit. (you can still use `stop()` inside class code to have them stop themselves)

```python
class UpscaleImage(Skprocess):

    def __init__(self, image):
        self.image_data = image
        self.process_config.runs = 1
        self.process_config.lives = 2

for result in pool.unordered_imap(UpscaleImage, data_set):

    upscaled_images.append(result)
```

```python
class ColorImage(Skprocess):

    def __init__(self, image, color, percent_change):
        self.process_config.runs = 1
        self.process_config.lives = 2
        
        self.image_data = image
        self.color = color
        self.percent_change = percent_change


colored_images = pool.star().map(ColorImage, zip(images, colors, percent_changes))
```

---

## `autoreconnect`

When a `Skprocess` is serialized to run in a subprocess, resources like database connections become `Reconnector` placeholders.

The `@autoreconnect` decorator automatically calls `reconnect_all()` after deserialization, restoring these resources.

### Basic usage (no credentials needed)

For sockets, threads, pipes, sqlite files, etc.:

```python
from suitkaise.processing import Skprocess, autoreconnect

@autoreconnect()
class MyProcess(Skprocess):
    def __init__(self):
        self.socket = socket.socket(...)  # becomes SocketReconnector
    
    def __run__(self):
        # self.socket is a live socket again
        self.socket.send(b"hello")
```

### With credentials

Pass passwords (connection metadata like host/port/user is stored during serialization):

```python
from suitkaise.processing import Skprocess, autoreconnect

@autoreconnect(**{
    "psycopg2.Connection": {
        "*": "secret",
        "analytics_db": "other_pass",
    },
    "redis.Redis": {
        "*": "redis_pass",
    },
})
class MyProcess(Skprocess):
    def __init__(self):
        self.db = psycopg2.connect(...)
        self.analytics_db = psycopg2.connect(...)
        self.cache = redis.Redis(...)
    
    def __run__(self):
        # db, analytics_db, cache are all live connections
        cursor = self.db.cursor()
        ...
```

### Password structure

```python
{
    "TypeKey": {
        "*": "password",           # default password for all instances
        "attr_name": "password",   # specific password for attr named "attr_name"
    }
}
```

- **Type keys** are `"module.ClassName"` (e.g., `"psycopg2.Connection"`)
- **`"*"`** provides default password for all instances of that type
- **Specific attr names** override the default
- Connection metadata (host, port, user, database) is stored during serialization

### Note on special types

- **Elasticsearch**: `password` is the api_key if no user was stored
- **InfluxDB v2**: `password` represents the token

### Manual reconnect in `__prerun__`

If you need dynamic credentials (e.g., from environment variables), use `reconnect_all()` directly:

```python
from suitkaise.processing import Skprocess
from suitkaise.cerial import reconnect_all
import os

class MyProcess(Skprocess):
    def __init__(self):
        self.db = psycopg2.connect(...)
    
    def __prerun__(self):
        reconnect_all(self, **{
            "psycopg2.Connection": {
                "*": os.environ["DB_PASSWORD"],
            },
        })
    
    def __run__(self):
        cursor = self.db.cursor()
        ...
```