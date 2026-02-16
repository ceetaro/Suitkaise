/*

synced from suitkaise-docs/sk/quick-start.md

*/

rows = 2
columns = 1

# 1.1

title = "Quick Start: `<suitkaise-api>sk</suitkaise-api>`"

# 1.2

text = "
```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Add modifiers to a function

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
def fetch(url):
    return requests.get(url).json()

# normal call — works exactly like before
data = fetch("https://api.example.com")

# retry 3 times
data = fetch.<suitkaise-api>retry</suitkaise-api>(times=3)("https://api.example.com")

# timeout after 5 seconds
data = fetch.<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com")

# <suitkaise-api>run</suitkaise-api> in background, get a Future
future = fetch.<suitkaise-api>background</suitkaise-api>()("https://api.example.com")
<suitkaise-api>result</suitkaise-api> = future.<suitkaise-api>result</suitkaise-api>()

# rate limit to 2 calls per second
data = fetch.rate_limit(2.0)("https://api.example.com")

# async
data = await fetch.<suitkaise-api>asynced</suitkaise-api>()("https://api.example.com")
```

## Chain modifiers

```python
# retry 3 times, 5 second timeout per attempt
data = fetch.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com")

# order doesn't matter — these are identical
data = fetch.<suitkaise-api>timeout</suitkaise-api>(5.0).<suitkaise-api>retry</suitkaise-api>(3)("https://api.example.com")
```

## Use on classes

```python
@<suitkaise-api>sk</suitkaise-api>
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
processor.process.<suitkaise-api>retry</suitkaise-api>(3)(data)
processor.save.<suitkaise-api>timeout</suitkaise-api>(10.0)("output.json")
future = processor.save.<suitkaise-api>background</suitkaise-api>()("output.json")
```

## Mark blocking code explicitly

When AST detection misses CPU-intensive work:

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>, <suitkaise-api>blocking</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
@<suitkaise-api>blocking</suitkaise-api>
def heavy_computation():
    return sum(x**2 for x in range(10_000_000))

# now .<suitkaise-api>asynced</suitkaise-api>() and .<suitkaise-api>background</suitkaise-api>() are available
<suitkaise-api>result</suitkaise-api> = await heavy_computation.<suitkaise-api>asynced</suitkaise-api>()()
```

## Check for blocking calls

```python
@<suitkaise-api>sk</suitkaise-api>
def slow_fetch(url):
    return requests.get(url).text

print(slow_fetch.<suitkaise-api>has_blocking_calls</suitkaise-api>)  # True
print(slow_fetch.<suitkaise-api>blocking_calls</suitkaise-api>)      # ['requests.get']
```

## Want to learn more?

- **Why page** — why `<suitkaise-api>sk</suitkaise-api>` exists, the call-site modifier pattern, and `_shared_meta` for `<suitkaise-api>Share</suitkaise-api>`
- **How to use** — full API reference for all modifiers
- **Examples** — progressively complex examples into a full script
- **How it works** — AST analysis, `Skfunction` wrappers, execution order (level: intermediate)
"
