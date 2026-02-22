# Suitkaise

Write Python at hacker-level speeds.

(pronounced exactly like the word suitcase)

All files in this repository are licensed under the Apache License 2.0, including:
- source code
- examples
- documentation
- tests
- site content code
- and everything else


## Installation

```bash
pip install suitkaise
```

## Info

Explicitly supported Python versions: 3.11 and above

Currently, `suitkaise` is version `0.4.11 beta`.

`suitkaise` contains the following modules:

- `cucumber`: serialization engine
- `circuits`: flow control with the Circuit and BreakingCircuit classes.
- `processing`: upgraded multiprocessing with easy shared state
- `paths`: upgraded path class and utilities for path ops
- `sk`: modifiers for functions and class methods
- `timing`: timer class with deep statistics usable in many ways

## Documentation

All documentation is available for download.

CLI:
- downloads to project root
- cwd must be within project root

```bash
suitkaise docs
```

Python:

```python
from suitkaise import docs

# download to project root
docs.download()

# download to a specific path within your project
docs.download("path/within/project")
```

To place docs outside your project root, use the `Permission` context manager.

```python
from suitkaise import docs

with docs.Permission():
    docs.download("/Users/joe/Documents")
```

You can also view more at [suitkaise.info](https://suitkaise.info).

## Quick Start

### Parallel processing with shared state

```python
from suitkaise.processing import Share, Pool, Skprocess
import logging

# put anything on Share — literally anything
share = Share()
share.counter = 0
share.results = []
share.log = logging.getLogger("worker")

class Worker(Skprocess):
    def __init__(self, share, item):
        self.share = share
        self.item = item

    def __run__(self):
        result = self.item * 2
        self.share.results.append(result)       # shared list
        self.share.counter += 1                 # shared counter
        self.share.log.info(f"done: {result}")  # shared logger

pool = Pool(workers=4)
pool.star().map(Worker, [(share, x) for x in range(20)])

print(share.counter)         # 20
print(len(share.results))    # 20
print(share.log.handlers)    # still works
```

### Serialize anything

```python
from suitkaise import cucumber

data = cucumber.serialize(any_object)
restored = cucumber.deserialize(data)
```

### Time anything

```python
from suitkaise.timing import timethis

@timethis()
def my_function():
    do_work()

my_function()
print(my_function.timer.mean)
```

```python
from suitkaise.timing import TimeThis

with TimeThis() as timer:
    do_this()
    then_this()
    this_too()

# stops timing and records on exit

# get most recent time
print(timer.most_recent)
```

### Add retry, timeout, background execution to any function

```python
from suitkaise import sk

@sk
def fetch(url):
    return requests.get(url).json()

# retry 3 times, timeout after 5 seconds each attempt
data = fetch.retry(3).timeout(5.0)("https://api.example.com")
```

### Cross-platform paths, normalized path types

```python
from suitkaise.paths import Skpath

path = Skpath("data/file.txt")
print(path.rp)  # "data/file.txt" — same on every machine, every OS
```

```python
from suitkaise.paths import autopath

@autopath()
def process(path: AnyPath):
    print(path.rp)  # always an Skpath, no matter what was passed in

process("data/file.txt")        # str → Skpath
process(Path("data/file.txt"))  # Path → Skpath
```


### Circuit breakers

```python
from suitkaise import Circuit

circuit = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

for request in requests:
    try:
        process(request)
    except ServiceError:
        circuit.short()
```

```python
from suitkaise import BreakingCircuit

breaker = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

while not breaker.broken:
    try:
        result = risky_operation()
        break  # success
    except OperationError:
        breaker.short()  # count the failure

if breaker.broken:
    handle_failure()
```

For more, see the full documentation at [suitkaise.info](https://suitkaise.info) or download the docs with `suitkaise docs` in your terminal after installation.
