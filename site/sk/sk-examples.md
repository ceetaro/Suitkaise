/*

synced from suitkaise-docs/sk/examples.md

*/

rows = 2
columns = 1

# 1.1

title = "`<suitkaise-api>sk</suitkaise-api>` examples"

# 1.2

text = "
(start of dropdown "Basic examples")
## Basic examples

### Decorate a function

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path
import json

@<suitkaise-api>sk</suitkaise-api>
def load_users(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text())
    return data["users"]

# real file I/O
data_path = Path("data/users.json")
data_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
data_path.write_text(json.dumps({"users": [{"id": 1, "name": "Ana"}]}))

# call normally (no changes to calling style)
users = load_users(data_path)
print(users)  # [{'id': 1, 'name': 'Ana'}]
```

### Use `<suitkaise-api>sk</suitkaise-api>()` as a function

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>

def streamline_format(text: str) -> str:
    return text.strip().lower().replace(" ", "-")

streamline_format = <suitkaise-api>sk</suitkaise-api>(streamline_format)

print(streamline_format("Hello World"))  # "hello-world"
```

### Chaining modifiers (order does not matter)

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path
import hashlib

@<suitkaise-api>sk</suitkaise-api>
def read_and_hash(path: Path) -> str:
    content = Path(path).read_bytes()
    return hashlib.sha256(content).hexdigest()

data_path = Path("data/blob.bin")
data_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
data_path.write_bytes(b"real data" * 100_000)

# same behavior, different order
digest = read_and_hash.<suitkaise-api>retry</suitkaise-api>(times=3, delay=0.1).<suitkaise-api>timeout</suitkaise-api>(1.0)(data_path)
digest = read_and_hash.<suitkaise-api>timeout</suitkaise-api>(1.0).<suitkaise-api>retry</suitkaise-api>(times=3, delay=0.1)(data_path)
```

### Timeout handling

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>sk</suitkaise-api> import <suitkaise-api>FunctionTimeoutError</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
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
    <suitkaise-api>result</suitkaise-api> = count_primes.<suitkaise-api>timeout</suitkaise-api>(0.05)(200_000)
except <suitkaise-api>FunctionTimeoutError</suitkaise-api> as exc:
    print(f"Timed out: {exc}")
```

### Background execution (Future)

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path
import hashlib

@<suitkaise-api>sk</suitkaise-api>
def hash_file(path: Path) -> str:
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()

data_path = Path("data/large.bin")
data_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
data_path.write_bytes(b"x" * 5_000_000)

future = hash_file.<suitkaise-api>background</suitkaise-api>()(data_path)

# do other work
summary = (data_path.stat().st_size, data_path.name)

# get the <suitkaise-api>result</suitkaise-api> (this will block)
<suitkaise-api>result</suitkaise-api> = future.<suitkaise-api>result</suitkaise-api>()
print(summary, <suitkaise-api>result</suitkaise-api>[:12])
```

### Rate limiting

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path

@<suitkaise-api>sk</suitkaise-api>
def file_size(path: Path) -> int:
    return Path(path).stat().st_size

data_path = Path("data/sample.txt")
data_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
data_path.write_text("real content\n" * 1000)

limited = file_size.rate_limit(2.0)  # max 2 calls per second
sizes = [limited(data_path) for _ in range(5)]
print(sizes)
```

### Custom retry exceptions

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path
import json

class ApiError(RuntimeError):
    pass

@<suitkaise-api>sk</suitkaise-api>
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
config_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
config_path.write_text('{"name": "demo"')

# only retry on ApiError
config = load_config.<suitkaise-api>retry</suitkaise-api>(times=2, delay=0.1, exceptions=(ApiError,))(config_path)
print(config)
```

(end of dropdown "Basic examples")


(start of dropdown "Async examples")
## Async examples

### `<suitkaise-api>asynced</suitkaise-api>()` for async code

```python
import asyncio
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path
import csv

@<suitkaise-api>sk</suitkaise-api>
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
<suitkaise-api>paths</suitkaise-api> = []
for i in range(3):
    p = data_dir / f"numbers_{i}.csv"
    p.write_text("\n".join(str(n) for n in range(1, 1000)))
    <suitkaise-api>paths</suitkaise-api>.append(p)

async def main():
    results = await asyncio.gather(
        sum_csv.<suitkaise-api>asynced</suitkaise-api>()(<suitkaise-api>paths</suitkaise-api>[0]),
        sum_csv.<suitkaise-api>asynced</suitkaise-api>()(<suitkaise-api>paths</suitkaise-api>[1]),
        sum_csv.<suitkaise-api>asynced</suitkaise-api>()(<suitkaise-api>paths</suitkaise-api>[2]),
    )
    print(results)

asyncio.<suitkaise-api>run</suitkaise-api>(main())
```

### Async chaining with timeout + retry

```python
import asyncio
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path
import json

@<suitkaise-api>sk</suitkaise-api>
def load_report(path: Path) -> dict:
    text = Path(path).read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # fix the file and retry
        Path(path).write_text(text + "}")
        raise ValueError("Report was incomplete, repaired and retrying")

report_path = Path("data/report.json")
report_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
report_path.write_text('{"ok": true')

async def main():
    report = await (
        load_report.<suitkaise-api>asynced</suitkaise-api>()
        .<suitkaise-api>retry</suitkaise-api>(times=2, delay=0.1, exceptions=(ValueError,))
        .<suitkaise-api>timeout</suitkaise-api>(0.5)
    )(report_path)
    print(report)

asyncio.<suitkaise-api>run</suitkaise-api>(main())
```

### Async rate limiting

```python
import asyncio
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path
import hashlib

@<suitkaise-api>sk</suitkaise-api>
def hash_text(path: Path) -> str:
    data = Path(path).read_text().encode()
    return hashlib.sha256(data).hexdigest()

data_path = Path("data/log.txt")
data_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
data_path.write_text("log line\n" * 1000)

async def main():
    limited = hash_text.<suitkaise-api>asynced</suitkaise-api>().rate_limit(5.0)
    results = await asyncio.gather(*[limited(data_path) for _ in range(10)])
    print(results[:2])

asyncio.<suitkaise-api>run</suitkaise-api>(main())
```

(end of dropdown "Async examples")

(start of dropdown "Blocking detection")
## Blocking detection

### Inspect blocking calls

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path

@<suitkaise-api>sk</suitkaise-api>
def load_text(path: Path) -> str:
    with open(path, "r") as f:
        return f.read()

data_path = Path("data/readme.txt")
data_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
data_path.write_text("real text")

print(load_text.<suitkaise-api>has_blocking_calls</suitkaise-api>)  # True
print(load_text.<suitkaise-api>blocking_calls</suitkaise-api>)      # includes file I/O
```

### Mark CPU-heavy code with `@<suitkaise-api>blocking</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>, <suitkaise-api>blocking</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
@<suitkaise-api>blocking</suitkaise-api>
def heavy_math(n: int) -> int:
    return sum(range(n))

# background/asynced are now available
future = heavy_math.<suitkaise-api>background</suitkaise-api>()(1_000_000)
<suitkaise-api>result</suitkaise-api> = future.<suitkaise-api>result</suitkaise-api>()
```

(end of dropdown "Blocking detection")

(start of dropdown "Classes")
## Classes

### Decorate a class

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
import json

@<suitkaise-api>sk</suitkaise-api>
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
store.save.<suitkaise-api>timeout</suitkaise-api>(2.0)("output.json")
```

### Class-level async

```python
import asyncio
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>, <suitkaise-api>blocking</suitkaise-api>
from pathlib import Path

@<suitkaise-api>sk</suitkaise-api>
class FileReader:
    @<suitkaise-api>blocking</suitkaise-api>
    def read(self, path: Path) -> str:
        with open(path, "r") as f:
            return f.read()

data_path = Path("data/message.txt")
data_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
data_path.write_text("hello from disk")

async def main():
    reader = FileReader()
    data = await reader.read.<suitkaise-api>asynced</suitkaise-api>()(data_path)
    print(data)

asyncio.<suitkaise-api>run</suitkaise-api>(main())
```

### Handling `<suitkaise-api>SkModifierError</suitkaise-api>` for classes without blocking calls

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>sk</suitkaise-api> import <suitkaise-api>SkModifierError</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
class Counter:
    def __init__(self):
        self.value = 0
    
    def inc(self):
        self.value += 1

try:
    Counter.<suitkaise-api>asynced</suitkaise-api>()
except <suitkaise-api>SkModifierError</suitkaise-api> as exc:
    print(exc)
```

### `<suitkaise-api>Share</suitkaise-api>` compatibility

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
class Counter:
    def __init__(self):
        self.value = 0
    
    def inc(self):
        self.value += 1

with <suitkaise-api>Share</suitkaise-api>() as share:
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
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path
import json

@<suitkaise-api>sk</suitkaise-api>
def load_payload(path: Path) -> dict:
    text = Path(path).read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # repair the file, then retry
        Path(path).write_text(text + "}")
        raise RuntimeError("Payload incomplete, repaired and retrying")

payload_path = Path("data/payload.json")
payload_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
payload_path.write_text('{"id": 1, "value": 42')

future = load_payload.<suitkaise-api>retry</suitkaise-api>(times=2, delay=0.1).<suitkaise-api>timeout</suitkaise-api>(1.0).<suitkaise-api>background</suitkaise-api>()(payload_path)
print(future.<suitkaise-api>result</suitkaise-api>())
```

### Rate limiting shared across wrappers

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
from pathlib import Path

@<suitkaise-api>sk</suitkaise-api>
def read_lines(path: Path) -> int:
    return len(Path(path).read_text().splitlines())

log_path = Path("data/log.txt")
log_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
log_path.write_text("line\n" * 500)

# limiter <suitkaise-api>lives</suitkaise-api> inside the wrapper
limited = read_lines.rate_limit(3.0)

batch_a = [limited(log_path) for _ in range(3)]
batch_b = [limited(log_path) for _ in range(3)]
print(batch_a + batch_b)
```

(end of dropdown "Advanced examples")

## Full script using `<suitkaise-api>sk</suitkaise-api>` modifiers

An end-to-end example that uses multiple modifiers together:
- `<suitkaise-api>asynced</suitkaise-api>()` for concurrent fetches
- `<suitkaise-api>retry</suitkaise-api>()` for transient failures
- `<suitkaise-api>timeout</suitkaise-api>()` to cap long calls
- `rate_limit()` to protect external services
- `<suitkaise-api>background</suitkaise-api>()` for CPU-heavy scoring
- `@<suitkaise-api>blocking</suitkaise-api>` to mark CPU-bound work

```python
"""
End-to-end <suitkaise-api>sk</suitkaise-api> modifiers example.

Parses in-memory JSON records, repairs incomplete inputs, scores them in
background, and returns scored records.
"""

import asyncio
import json
import hashlib

from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>, <suitkaise-api>blocking</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>sk</suitkaise-api> import <suitkaise-api>FunctionTimeoutError</suitkaise-api>


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


@<suitkaise-api>sk</suitkaise-api>
@<suitkaise-api>blocking</suitkaise-api>
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


@<suitkaise-api>sk</suitkaise-api>
@<suitkaise-api>blocking</suitkaise-api>
def score_record(record: dict) -> dict:
    payload = f"{record['id']}:{record['value']}".encode()
    digest = hashlib.sha256(payload).hexdigest()
    score = int(digest[:8], 16) % 1000
    return {**record, "score": score}


async def main():
    payloads = seed_records()
    
    loader = (
        load_record.<suitkaise-api>asynced</suitkaise-api>()
        .<suitkaise-api>retry</suitkaise-api>(times=2, delay=0.1, exceptions=(TransientError,))
        .<suitkaise-api>timeout</suitkaise-api>(0.5)
        .rate_limit(20.0)
    )
    
    results = await asyncio.gather(
        *[loader(i, payloads) for i in range(len(payloads))],
        return_exceptions=True,
    )
    
    records = []
    for idx, <suitkaise-api>result</suitkaise-api> in enumerate(results):
        if isinstance(<suitkaise-api>result</suitkaise-api>, <suitkaise-api>FunctionTimeoutError</suitkaise-api>):
            print(f"Timeout: record {idx + 1}")
            continue
        if isinstance(<suitkaise-api>result</suitkaise-api>, Exception):
            print(f"Failed: record {idx + 1}: {<suitkaise-api>result</suitkaise-api>}")
            continue
        records.append(<suitkaise-api>result</suitkaise-api>)
    
    futures = [score_record.<suitkaise-api>background</suitkaise-api>()(record) for record in records]
    scored = [future.<suitkaise-api>result</suitkaise-api>() for future in futures]
    
    print(f"Scored {len(scored)} records")
    print("Sample:", scored[:3])


if __name__ == "__main__":
    asyncio.<suitkaise-api>run</suitkaise-api>(main())
```
"
