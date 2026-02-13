/*

synced from suitkaise-docs/sk/examples.md

*/

rows = 2
columns = 1

# 1.1

title = "`sk` examples"

# 1.2

text = "
(start of dropdown "Basic examples")
## Basic examples

### Decorate a function

```python
from suitkaise import sk
from pathlib import Path
import json

@sk
def load_users(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text())
    return data["users"]

# real file I/O
data_path = Path("data/users.json")
data_path.parent.mkdir(parents=True, exist_ok=True)
data_path.write_text(json.dumps({"users": [{"id": 1, "name": "Ana"}]}))

# call normally (no changes to calling style)
users = load_users(data_path)
print(users)  # [{'id': 1, 'name': 'Ana'}]
```

### Use `sk()` as a function

```python
from suitkaise import sk

def streamline_format(text: str) -> str:
    return text.strip().lower().replace(" ", "-")

streamline_format = sk(streamline_format)

print(streamline_format("Hello World"))  # "hello-world"
```

### Chaining modifiers (order does not matter)

```python
from suitkaise import sk
from pathlib import Path
import hashlib

@sk
def read_and_hash(path: Path) -> str:
    content = Path(path).read_bytes()
    return hashlib.sha256(content).hexdigest()

data_path = Path("data/blob.bin")
data_path.parent.mkdir(parents=True, exist_ok=True)
data_path.write_bytes(b"real data" * 100_000)

# same behavior, different order
digest = read_and_hash.retry(times=3, delay=0.1).timeout(1.0)(data_path)
digest = read_and_hash.timeout(1.0).retry(times=3, delay=0.1)(data_path)
```

### Timeout handling

```python
from suitkaise import sk
from suitkaise.sk import FunctionTimeoutError

@sk
def count_primes(limit: int) -> int:
    primes = []
    for n in range(2, limit):
        is_prime = True
        for p in primes:
            if p * p > n:
                break
            if n % p == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(n)
    return len(primes)

try:
    result = count_primes.timeout(0.05)(200_000)
except FunctionTimeoutError as exc:
    print(f"Timed out: {exc}")
```

### Background execution (Future)

```python
from suitkaise import sk
from pathlib import Path
import hashlib

@sk
def hash_file(path: Path) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()

data_path = Path("data/large.bin")
data_path.parent.mkdir(parents=True, exist_ok=True)
data_path.write_bytes(b"x" * 5_000_000)

future = hash_file.background()(data_path)

# do other work
summary = (data_path.stat().st_size, data_path.name)

# get the result (this will block)
result = future.result()
print(summary, result[:12])
```

### Rate limiting

```python
from suitkaise import sk
from pathlib import Path

@sk
def file_size(path: Path) -> int:
    return Path(path).stat().st_size

data_path = Path("data/sample.txt")
data_path.parent.mkdir(parents=True, exist_ok=True)
data_path.write_text("real content\n" * 1000)

limited = file_size.rate_limit(2.0)  # max 2 calls per second
sizes = [limited(data_path) for _ in range(5)]
print(sizes)
```

### Custom retry exceptions

```python
from suitkaise import sk
from pathlib import Path
import json

class ApiError(RuntimeError):
    pass

@sk
def load_config(path: Path) -> dict:
    text = Path(path).read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # repair the file and retry
        Path(path).write_text(text + "}")
        raise ApiError("Config was incomplete, repaired and retrying")

# create a truncated JSON file
config_path = Path("data/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text('{"name": "demo"')

# only retry on ApiError
config = load_config.retry(times=2, delay=0.1, exceptions=(ApiError,))(config_path)
print(config)
```

(end of dropdown "Basic examples")


(start of dropdown "Async examples")
## Async examples

### `asynced()` for async code

```python
import asyncio
from suitkaise import sk
from pathlib import Path
import csv

@sk
def sum_csv(path: Path) -> int:
    total = 0
    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            total += int(row[0])
    return total

# real CSV work
data_dir = Path("data")
data_dir.mkdir(parents=True, exist_ok=True)
paths = []
for i in range(3):
    p = data_dir / f"numbers_{i}.csv"
    p.write_text("\n".join(str(n) for n in range(1, 1000)))
    paths.append(p)

async def main():
    results = await asyncio.gather(
        sum_csv.asynced()(paths[0]),
        sum_csv.asynced()(paths[1]),
        sum_csv.asynced()(paths[2]),
    )
    print(results)

asyncio.run(main())
```

### Async chaining with timeout + retry

```python
import asyncio
from suitkaise import sk
from pathlib import Path
import json

@sk
def load_report(path: Path) -> dict:
    text = Path(path).read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # fix the file and retry
        Path(path).write_text(text + "}")
        raise ValueError("Report was incomplete, repaired and retrying")

report_path = Path("data/report.json")
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text('{"ok": true')

async def main():
    report = await (
        load_report.asynced()
        .retry(times=2, delay=0.1, exceptions=(ValueError,))
        .timeout(0.5)
    )(report_path)
    print(report)

asyncio.run(main())
```

### Async rate limiting

```python
import asyncio
from suitkaise import sk
from pathlib import Path
import hashlib

@sk
def hash_text(path: Path) -> str:
    data = Path(path).read_text().encode()
    return hashlib.sha256(data).hexdigest()

data_path = Path("data/log.txt")
data_path.parent.mkdir(parents=True, exist_ok=True)
data_path.write_text("log line\n" * 1000)

async def main():
    limited = hash_text.asynced().rate_limit(5.0)
    results = await asyncio.gather(*[limited(data_path) for _ in range(10)])
    print(results[:2])

asyncio.run(main())
```

(end of dropdown "Async examples")

(start of dropdown "Blocking detection")
## Blocking detection

### Inspect blocking calls

```python
from suitkaise import sk
from pathlib import Path

@sk
def load_text(path: Path) -> str:
    with open(path, "r") as f:
        return f.read()

data_path = Path("data/readme.txt")
data_path.parent.mkdir(parents=True, exist_ok=True)
data_path.write_text("real text")

print(load_text.has_blocking_calls)  # True
print(load_text.blocking_calls)      # includes file I/O
```

### Mark CPU-heavy code with `@blocking`

```python
from suitkaise import sk, blocking

@sk
@blocking
def heavy_math(n: int) -> int:
    return sum(range(n))

# background/asynced are now available
future = heavy_math.background()(1_000_000)
result = future.result()
```

(end of dropdown "Blocking detection")

(start of dropdown "Classes")
## Classes

### Decorate a class

```python
from suitkaise import sk
import json

@sk
class DataStore:
    def __init__(self):
        self.data = {}
    
    def set(self, key: str, value: dict):
        self.data[key] = value
    
    def save(self, path: str):
        with open(path, "w") as f:
            f.write(json.dumps(self.data))

store = DataStore()
store.set("a", {"value": 1})
store.save("output.json")

# modifiers on methods
store.save.timeout(2.0)("output.json")
```

### Class-level async

```python
import asyncio
from suitkaise import sk, blocking
from pathlib import Path

@sk
class FileReader:
    @blocking
    def read(self, path: Path) -> str:
        with open(path, "r") as f:
            return f.read()

data_path = Path("data/message.txt")
data_path.parent.mkdir(parents=True, exist_ok=True)
data_path.write_text("hello from disk")

async def main():
    reader = FileReader()
    data = await reader.read.asynced()(data_path)
    print(data)

asyncio.run(main())
```

### Handling `SkModifierError` for classes without blocking calls

```python
from suitkaise import sk
from suitkaise.sk import SkModifierError

@sk
class Counter:
    def __init__(self):
        self.value = 0
    
    def inc(self):
        self.value += 1

try:
    Counter.asynced()
except SkModifierError as exc:
    print(exc)
```

### `Share` compatibility

```python
from suitkaise import sk
from suitkaise.processing import Share

@sk
class Counter:
    def __init__(self):
        self.value = 0
    
    def inc(self):
        self.value += 1

with Share() as share:
    share.counter = Counter()
    share.counter.inc()
    share.counter.inc()
    print(share.counter.value)  # 2
```

(end of dropdown "Classes")

(start of dropdown "Advanced examples")
## Advanced examples

### Combining retry + timeout + background

```python
from suitkaise import sk
from pathlib import Path
import json

@sk
def load_payload(path: Path) -> dict:
    text = Path(path).read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # repair the file, then retry
        Path(path).write_text(text + "}")
        raise RuntimeError("Payload incomplete, repaired and retrying")

payload_path = Path("data/payload.json")
payload_path.parent.mkdir(parents=True, exist_ok=True)
payload_path.write_text('{"id": 1, "value": 42')

future = load_payload.retry(times=2, delay=0.1).timeout(1.0).background()(payload_path)
print(future.result())
```

### Rate limiting shared across wrappers

```python
from suitkaise import sk
from pathlib import Path

@sk
def read_lines(path: Path) -> int:
    return len(Path(path).read_text().splitlines())

log_path = Path("data/log.txt")
log_path.parent.mkdir(parents=True, exist_ok=True)
log_path.write_text("line\n" * 500)

# limiter lives inside the wrapper
limited = read_lines.rate_limit(3.0)

batch_a = [limited(log_path) for _ in range(3)]
batch_b = [limited(log_path) for _ in range(3)]
print(batch_a + batch_b)
```

(end of dropdown "Advanced examples")

## Full script using `sk` modifiers

An end-to-end example that uses multiple modifiers together:
- `asynced()` for concurrent fetches
- `retry()` for transient failures
- `timeout()` to cap long calls
- `rate_limit()` to protect external services
- `background()` for CPU-heavy scoring
- `@blocking` to mark CPU-bound work

```python
"""
End-to-end sk modifiers example.

Parses in-memory JSON records, repairs incomplete inputs, scores them in
background, and returns scored records.
"""

import asyncio
import json
import hashlib

from suitkaise import sk, blocking
from suitkaise.sk import FunctionTimeoutError


class TransientError(RuntimeError):
    pass


def seed_records() -> list[str]:
    """Create a mix of valid and truncated JSON payloads."""
    payloads = []
    for record_id in range(1, 11):
        record = {"id": record_id, "value": record_id * 3}
        text = json.dumps(record)
        if record_id == 4:
            text = text[:-1]  # truncate one payload to trigger repair
        payloads.append(text)
    return payloads


@sk
@blocking
def load_record(index: int, payloads: list[str]) -> dict:
    text = payloads[index]
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        # repair and retry in memory
        payloads[index] = text + "}"
        raise TransientError("Record incomplete, repaired and retrying")
    
    if "id" not in record or "value" not in record:
        raise ValueError("Missing required keys")
    
    return record


@sk
@blocking
def score_record(record: dict) -> dict:
    payload = f"{record['id']}:{record['value']}".encode()
    digest = hashlib.sha256(payload).hexdigest()
    score = int(digest[:8], 16) % 1000
    return {**record, "score": score}


async def main():
    payloads = seed_records()
    
    loader = (
        load_record.asynced()
        .retry(times=2, delay=0.1, exceptions=(TransientError,))
        .timeout(0.5)
        .rate_limit(20.0)
    )
    
    results = await asyncio.gather(
        *[loader(i, payloads) for i in range(len(payloads))],
        return_exceptions=True,
    )
    
    records = []
    for idx, result in enumerate(results):
        if isinstance(result, FunctionTimeoutError):
            print(f"Timeout: record {idx + 1}")
            continue
        if isinstance(result, Exception):
            print(f"Failed: record {idx + 1}: {result}")
            continue
        records.append(result)
    
    futures = [score_record.background()(record) for record in records]
    scored = [future.result() for future in futures]
    
    print(f"Scored {len(scored)} records")
    print("Sample:", scored[:3])


if __name__ == "__main__":
    asyncio.run(main())
```
"
