# Quick Start

Install suitkaise:

```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

Requires Python 3.11+.

---

## 1. Share state across processes

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

share = <suitkaise-api>Share</suitkaise-api>()
share.counter = 0

class Counter(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, share):
        self.share = share
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 5

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.share.counter += 1

<suitkaise-api>Pool</suitkaise-api>(workers=4).<suitkaise-api>map</suitkaise-api>(Counter, [share] * 4)
print(share.counter)  # 20 (4 processes × 5 <suitkaise-api>runs</suitkaise-api>)
```

`<suitkaise-api>Share</suitkaise-api>` works with any object. `<suitkaise-api>Skprocess</suitkaise-api>` gives you lifecycle hooks. `<suitkaise-api>Pool</suitkaise-api>` runs them in parallel. That's it.

---

## 2. Serialize anything

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>

# <suitkaise-api>serialize</suitkaise-api>
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(any_object)

# <suitkaise-api>deserialize</suitkaise-api>
restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
```

No `PicklingError`. Works with lambdas, closures, threads, database connections, generators, and more.

If the object has live resources (connections, threads), they become `Reconnector` objects:

```python
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>(restored, password='secret')
```

---

## 3. Time anything

Decorator:

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>timethis</suitkaise-api>

@<suitkaise-api>timethis</suitkaise-api>()
def process_data():
    do_work()

for _ in range(100):
    process_data()

print(process_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
print(process_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95))
```

Context manager:

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>TimeThis</suitkaise-api>

with <suitkaise-api>TimeThis</suitkaise-api>() as timer:
    do_work()

print(<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>)
```

---

## 4. Add modifiers to any function

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
def fetch(url):
    return requests.get(url).json()

# normal call
data = fetch("https://api.example.com")

# retry 3 times
data = fetch.<suitkaise-api>retry</suitkaise-api>(times=3)("https://api.example.com")

# timeout after 5 seconds
data = fetch.<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com")

# chain them
data = fetch.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com")

# <suitkaise-api>run</suitkaise-api> in background
future = fetch.<suitkaise-api>background</suitkaise-api>()("https://api.example.com")

# async
data = await fetch.<suitkaise-api>asynced</suitkaise-api>()("https://api.example.com")
```

---

## 5. Circuit breakers

Auto-resetting:

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

for request in incoming_requests:
    try:
        process(request)
    except ServiceError:
        circuit.<suitkaise-api>short</suitkaise-api>()  # after 5 failures, sleeps 1s, then resets
```

Manual reset:

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

breaker = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

while not breaker.<suitkaise-api>broken</suitkaise-api>:
    try:
        <suitkaise-api>result</suitkaise-api> = risky_operation()
        break
    except OperationError:
        breaker.<suitkaise-api>short</suitkaise-api>()

if breaker.<suitkaise-api>broken</suitkaise-api>:
    handle_failure()
    breaker.<suitkaise-api>reset</suitkaise-api>()
```

---

## 6. Cross-platform paths

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>, <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>

# project-relative path — same on every machine
path = <suitkaise-api>Skpath</suitkaise-api>("data/file.txt")
print(path.rp)   # "data/file.txt"
print(path.ap)   # "/Users/me/project/data/file.txt"
print(path.<suitkaise-api>id</suitkaise-api>)   # reversible base64 ID for database storage

# auto-convert path types
@<suitkaise-api>autopath</suitkaise-api>()
def process(path: <suitkaise-api>AnyPath</suitkaise-api>):
    print(path.rp)  # always an <suitkaise-api>Skpath</suitkaise-api>, no matter what was passed in

process("data/file.txt")        # str → <suitkaise-api>Skpath</suitkaise-api>
process(Path("data/file.txt"))  # Path → <suitkaise-api>Skpath</suitkaise-api>
```

---

## Putting it together

The modules are designed to work together:

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

share = <suitkaise-api>Share</suitkaise-api>()
share.<suitkaise-api>timer</suitkaise-api> = <suitkaise-api>Sktimer</suitkaise-api>()
share.circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=2.0)

class ResilientWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, share, url):
        self.share = share
        self.url = url

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        try:
            <suitkaise-api>result</suitkaise-api> = fetch(self.url)
        except ServiceError:
            self.share.circuit.<suitkaise-api>short</suitkaise-api>()
        self.share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

pool = <suitkaise-api>Pool</suitkaise-api>(workers=4)
pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(ResilientWorker, [(share, url) for url in urls])

print(f"Mean response time: {share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"<suitkaise-api>Circuit</suitkaise-api> tripped {share.circuit.<suitkaise-api>total_trips</suitkaise-api>} times")
```

Shared timers, shared circuit breakers, parallel workers — all synced automatically.

---

For full documentation on each module, see:
- `<suitkaise-api>processing</suitkaise-api>/` — Skprocess, Pool, Share, Pipe
- `<suitkaise-api>cucumber</suitkaise-api>/` — serialize, deserialize, reconnect_all
- `<suitkaise-api>timing</suitkaise-api>/` — Sktimer, timethis, TimeThis
- `<suitkaise-api>sk</suitkaise-api>/` — @sk, modifiers, @blocking
- `<suitkaise-api>circuits</suitkaise-api>/` — Circuit, BreakingCircuit
- `<suitkaise-api>paths</suitkaise-api>/` — Skpath, @autopath, AnyPath
