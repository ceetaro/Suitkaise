# Quick Start

Install suitkaise:

```bash
pip install suitkaise
```

Requires Python 3.11+.

## 1. Share state across processes

```python
from suitkaise.processing import Share, Pool, Skprocess

share = Share()
share.counter = 0

class Counter(Skprocess):
    def __init__(self, share):
        self.share = share
        self.process_config.runs = 5

    def __run__(self):
        self.share.counter += 1

Pool(workers=4).map(Counter, [share] * 4)
print(share.counter)  # 20 (4 processes × 5 runs)
```

`Share` works with any object. `Skprocess` gives you lifecycle hooks. `Pool` runs them in parallel. That's it.


## 2. Serialize anything

```python
from suitkaise import cucumber

# serialize
data = cucumber.serialize(any_object)

# deserialize
restored = cucumber.deserialize(data)
```

No `PicklingError`. Works with lambdas, closures, threads, database connections, generators, and more.

If the object has live resources (connections, threads), they become `Reconnector` objects:

```python
cucumber.reconnect_all(restored, password='secret')
```


## 3. Time anything

Decorator:

```python
from suitkaise.timing import timethis

@timethis()
def process_data():
    do_work()

for _ in range(100):
    process_data()

print(process_data.timer.mean)
print(process_data.timer.percentile(95))
```

Context manager:

```python
from suitkaise.timing import TimeThis

with TimeThis() as timer:
    do_work()

print(timer.most_recent)
```

## 4. Add modifiers to any function

```python
from suitkaise import sk

@sk
def fetch(url):
    return requests.get(url).json()

# normal call
data = fetch("https://api.example.com")

# retry 3 times
data = fetch.retry(times=3)("https://api.example.com")

# timeout after 5 seconds
data = fetch.timeout(5.0)("https://api.example.com")

# chain them
data = fetch.retry(3).timeout(5.0)("https://api.example.com")

# run in background
future = fetch.background()("https://api.example.com")

# async
data = await fetch.asynced()("https://api.example.com")
```


## 5. Circuit breakers

Auto-resetting:

```python
from suitkaise import Circuit

circuit = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

for request in incoming_requests:
    try:
        process(request)
    except ServiceError:
        circuit.short()  # after 5 failures, sleeps 1s, then resets
```

Manual reset:

```python
from suitkaise import BreakingCircuit

breaker = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

while not breaker.broken:
    try:
        result = risky_operation()
        break
    except OperationError:
        breaker.short()

if breaker.broken:
    handle_failure()
    breaker.reset()
```


## 6. Cross-platform paths

```python
from suitkaise.paths import Skpath, autopath, AnyPath

# project-relative path — same on every machine
path = Skpath("data/file.txt")
print(path.rp)   # "data/file.txt"
print(path.ap)   # "/Users/me/project/data/file.txt"
print(path.id)   # reversible base64 ID for database storage

# auto-convert path types
@autopath()
def process(path: AnyPath):
    print(path.rp)  # always an Skpath, no matter what was passed in

process("data/file.txt")        # str → Skpath
process(Path("data/file.txt"))  # Path → Skpath
```


## Putting it together

The modules are designed to work together:

```python
from suitkaise.processing import Share, Pool, Skprocess
from suitkaise.timing import Sktimer
from suitkaise import Circuit

share = Share()
share.timer = Sktimer()
share.circuit = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=2.0)

class ResilientWorker(Skprocess):
    def __init__(self, share, url):
        self.share = share
        self.url = url

    def __run__(self):
        self.share.timer.start()
        try:
            result = fetch(self.url)
        except ServiceError:
            self.share.circuit.short()
        self.share.timer.stop()

pool = Pool(workers=4)
pool.star().map(ResilientWorker, [(share, url) for url in urls])

print(f"Mean response time: {share.timer.mean:.3f}s")
print(f"Circuit tripped {share.circuit.total_trips} times")
```

Shared timers, shared circuit breakers, parallel workers — all synced automatically.


For full documentation on each module, see the respective module pages. Navigate using the "sidebar menu" in the top left of the page. 

(!!! IMPORTANT: add link that opens the sidebar menu here to "sidebar menu" in quotes in sentence above !!!)