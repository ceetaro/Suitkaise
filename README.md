# Suitkaise

Making things easier for developers of all skill levels to develop complex Python programs.

(pronounced exactly like the word suitcase)

## Installation

```bash
pip install suitkaise
```

## Info

Supported Python versions: 3.11 and above

Currently, `suitkaise` is version `0.3.0`.

All files and code in this repository is licensed under the Apache License 2.0.

`suitkaise` contains the following modules:

- cerial: serialization engine

- circuits: flow control with the Circuit and BreakingCircuit classes.

- processing: multiprocessing/subprocesses with pools, methodized queue sharing, and shared memory patterns with the Share class.

- paths: Skpath class and utilities for path operations.

- sk: utility for modifying functions and classes

- timing: Sktimer class and utilities for timing operations.

## Documentation

All documentation is available for download:

```python
from suitkaise import docs

docs.download("path/where/you/want/them/to/go")

# auto send them to project root
docs.download()
```

To send them outside of your project root, use the `Permission` class:

```python
from suitkaise import docs, Permission

with Permission():
    docs.download("Users/joe/Documents")
```

You can also view more at [suitkaise.info](https://suitkaise.info).

## Quick Start

###

### Time all of your code

Time a function/method without a specific timer.
```python
from suitkaise import timing

# time functions and methods automatically
@timing.timethis()
def my_function():
    # your code here
    pass

for i in range(100):
    my_function()

# get stats directly from function object
mean = my_function.timer.mean
stdev = my_function.timer.stdev
```

Time a function/method with a specific timer.
```python
from suitkaise import timing

t = timing.Sktimer()

class MyClass:

    @timing.timethis(timer=t)
    def my_function(self):
        # your code here
        pass

    @timing.timethis(timer=t)
    def my_function_2(self):
        # your code here
        pass

# create an instance of MyClass
my_instance = MyClass()

# get stats from the timer
print(t.mean)
print(t.stdev)
print(t.percentile(95))
```

Time a block of code without a specific timer.
```python
from suitkaise import timing

with timing.TimeThis() as timer:
    # your code here
    pass

# get the time that was just recorded (returns the Sktimer object)
# does not collect stats over time without a specific timer
print(timer.most_recent)
```

Time a block of code with a specific timer.
```python
from suitkaise import timing

t = timing.Sktimer()

with timing.TimeThis(timer=t):
    # your code here
    pass

# get stats
print(t.mean)
print(t.stdev)
print(t.percentile(95))
```

Simple utilities
```python
from suitkaise import timing

# get the current time
start_time = timing.time()

# sleep for a given number of seconds and get time after sleeping
time_after_sleeping = timing.sleep(1)

# get the elapsed time from start time to current time
elapsed_time = timing.elapsed(start_time)

# get the elapsed time from start time to time after sleeping
elapsed_time2 = timing.elapsed(start_time, time_after_sleeping)
```

There is much more to the timing module. For more information, read the docs on timing or visit [suitkaise.info](https://suitkaise.info).

### Path operations and `Skpath`

`Skpath` is a special path object that automatically detects your project root and uses it to normalize paths to an `rp` property.

`Skpaths` in the same project on different machines will be equal without any extra work.

```python
from suitkaise.paths import Skpath

path = Skpath("myproject/feature/file.txt")

# get absolute path as str
abs_path = path.ap

# get path relative to project root as str
rp_path = path.rp

# get path with platform-native separators as str
platform_path = path.platform

# get path as reconstructible ID
path_id = path.id
```

Use the `@autopath` decorator to automatically convert incoming values to their correct types, normalizing them through `Skpath` before passing them to the function.

```python
from suitkaise.paths import autopath, AnyPath

@autopath()
def process_file(path: str):

    # all Skpaths, Paths, and strs will be converted to strs

@autopath(use_caller=True)
def process_file(path: Path):

    # if no path is provided, uses caller file path
    # all Skpaths, Paths, and strs will be converted to Paths

@autopath(only="path")
def process_file(path: str, names: list[str], ids: list[str]):

    # autopath will only do path param 


@autopath()
def copy_file(path: AnyPath, target_path: AnyPath):

    # AnyPath = Skpath | Path | str
    # all Paths and strs will be converted to Skpaths
```

Get caller path automatically
```python
from suitkaise.paths import Skpath

caller = Skpath()

caller = get_caller_path()
```

Get project root automatically
```python
from suitkaise.paths import Skpath

root = Skpath().root

root = get_project_root()
```

Get a nested dict representing your project structure in `Skpaths`
```python
from suitkaise.paths import Skpath

structure = get_project_structure()
```

There is much more to the paths module. For more information, read the docs on paths or visit [suitkaise.info](https://suitkaise.info).

### Flow control with `Circuit` and `BreakingCircuit`





