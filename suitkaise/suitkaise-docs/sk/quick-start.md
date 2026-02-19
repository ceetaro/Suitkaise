# `sk` quick start guide

```bash
pip install suitkaise
```

## Add modifiers to a function

```python
from suitkaise import sk

@sk
def fetch(url):
    return requests.get(url).json()

# normal call — works exactly like before
data = fetch("https://api.example.com")

# retry 3 times
data = fetch.retry(times=3)("https://api.example.com")

# timeout after 5 seconds
data = fetch.timeout(5.0)("https://api.example.com")

# run in background, get a Future
future = fetch.background()("https://api.example.com")
result = future.result()

# rate limit to 2 calls per second
data = fetch.rate_limit(2.0)("https://api.example.com")

# async
data = await fetch.asynced()("https://api.example.com")
```

## Chain modifiers

```python
# retry 3 times, 5 second timeout per attempt
data = fetch.retry(3).timeout(5.0)("https://api.example.com")

# order doesn't matter — these are identical
data = fetch.timeout(5.0).retry(3)("https://api.example.com")
```

## Use on classes

```python
@sk
class DataProcessor:
    def __init__(self, config):
        self.config = config

    def process(self, data):
        return transform(data)

    def save(self, path):
        with open(path, 'w') as f:
            f.write(json.dumps(self.results))

processor = DataProcessor(config)

# normal call
processor.process(data)

# with modifiers
processor.process.retry(3)(data)
processor.save.timeout(10.0)("output.json")
future = processor.save.background()("output.json")
```

## Mark blocking code explicitly

When AST detection misses CPU-intensive work:

```python
from suitkaise import sk, blocking

@sk
@blocking
def heavy_computation():
    return sum(x**2 for x in range(10_000_000))

# now .asynced() and .background() are available
result = await heavy_computation.asynced()()
```

## Check for blocking calls

```python
@sk
def slow_fetch(url):
    return requests.get(url).text

print(slow_fetch.has_blocking_calls)  # True
print(slow_fetch.blocking_calls)      # ['requests.get']
```

## Want to learn more?

- **Why page** — why `sk` exists, the call-site modifier pattern, and `_shared_meta` for `Share`
- **How to use** — full API reference for all modifiers
- **Examples** — progressively complex examples into a full script
- **How it works** — AST analysis, `Skfunction` wrappers, execution order (level: intermediate)
