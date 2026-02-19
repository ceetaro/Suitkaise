/*

synced from suitkaise-docs/sk/why.md

*/

rows = 2
columns = 1

# 1.1

title = "Why you should use `sk`"

# 1.2

text = "
## TLDR

- **One decorator, five superpowers** - Add `<suitkaise-api>.retry()</suitkaise-api>`, `<suitkaise-api>.timeout()</suitkaise-api>`, `<suitkaise-api>.background()</suitkaise-api>`, `<suitkaise-api>.rate_limit()</suitkaise-api>`, and `<suitkaise-api>.asynced()</suitkaise-api>` to any function or class
- **Modify at the call site, not the definition** - Define your function once, decide how to call it each time
- **Chain modifiers in any order** - `<suitkaise-api>fn.retry(3).timeout(5.0)</suitkaise-api>` and `<suitkaise-api>fn.timeout(5.0).retry(3)</suitkaise-api>` do the same thing
- **Auto-detects blocking code** - AST analysis identifies I/O, network calls, and sleep patterns automatically
- **`<suitkaise-api>Share</suitkaise-api>` metadata generation** - The kicker. Makes your classes work efficiently inside `<suitkaise-api>Share</suitkaise-api>`
- **Classes too** - Works on entire classes, giving every method the same modifier capabilities, and an async class pattern as well

---

## The problem with retry, timeout, and async libraries

You probably already use something for retry logic. Maybe `tenacity`. Maybe a hand-rolled decorator.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

<suitkaise-api>@retry</suitkaise-api>(stop=stop_after_attempt(3), wait=wait_exponential())
def fetch_data(url):
    return requests.get(url).json()
```

This works. But now your function always retries. Every call. Every time.

What if you want to retry in production but not in tests? What if one call site needs a timeout but another doesn't? What if you want to run it in the background just this once?

You end up with multiple wrapped versions of the same function, or you start passing flags and config around.

## `<suitkaise-api>sk</suitkaise-api>` — modify at the call site, not the definition

`<suitkaise-api>sk</suitkaise-api>` takes a different approach. You define your function once, cleanly. Then you decide how to call it each time.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>

<suitkaise-api>@sk</suitkaise-api>
def fetch_data(url):
    return requests.get(url).json()
```

The function works exactly like before:

```python
data = fetch_data("https://api.example.com")
```

But now you have modifiers available at every call site:

```python
# retry 3 times with exponential backoff
data = fetch_data.<suitkaise-api>retry</suitkaise-api>(times=3, delay=1.0, backoff_factor=2.0)("https://api.example.com")

# timeout after 5 seconds
data = fetch_data.<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com")

# run in background, get a Future
future = fetch_data.<suitkaise-api>background</suitkaise-api>()("https://api.example.com")
result = future.<suitkaise-api>result</suitkaise-api>()

# rate limit to 2 calls per second
data = fetch_data.rate_limit(2.0)("https://api.example.com")

# make it async
data = await fetch_data.<suitkaise-api>asynced</suitkaise-api>()("https://api.example.com")
```

The function definition stays clean. The call site says exactly what's happening. No wrapper functions, no config objects, no multiple versions.

## Chain modifiers

Modifiers can be chained in any order:

```python
# retry 3 times, with a 5-second timeout per attempt
data = fetch_data.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com")

# same thing, different order — identical behavior
data = fetch_data.<suitkaise-api>timeout</suitkaise-api>(5.0).<suitkaise-api>retry</suitkaise-api>(3)("https://api.example.com")
```

The execution order is always consistent regardless of how you chain them:
1. Rate limit (outermost) — throttle before each attempt
2. Retry — retry loop
3. Timeout — per-attempt timeout
4. Function call (innermost)

This means you don't have to think about ordering. Just add what you need.

```python
# all five modifiers, chained
result = await (
    fetch_data.<suitkaise-api>asynced</suitkaise-api>()
    .<suitkaise-api>retry</suitkaise-api>(times=3, delay=0.5)
    .<suitkaise-api>timeout</suitkaise-api>(10.0)
    .rate_limit(5.0)
)("https://api.example.com")
```

## The double parentheses look a little confusing

They do! But it's actually really simple.

This is intentional. The actual function arguments are always at the end of the chain:

```python
fetch_data.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com")
#         ^^^^^^^^  ^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^
#         modifier   modifier      actual function args
```

You might notice the pattern: `fn.modifier()("args")`. The first call sets up the modifier. The second call runs the function.

Once you see it, it's easy to read: everything before the last parentheses is configuration, the last parentheses are the call.

But now when reviewing code, you can quickly see how it is being modified without sifting through 5 extra args in the main function call.

## Works on classes too

`<suitkaise-api>@sk</suitkaise-api>` isn't just for functions. Put it on a class and every method gets modifiers:

```python
<suitkaise-api>@sk</suitkaise-api>
class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.results = []

    def process(self, data):
        return transform(data)

    def save(self, path):
        with open(path, 'w') as f:
            f.write(json.dumps(self.results))

processor = DataProcessor(config)

# normal call
processor.process(data)

# with timeout
processor.save.<suitkaise-api>timeout</suitkaise-api>(10.0)("output.json")

# with retry
processor.<suitkaise-api>process.retry(</suitkaise-api>3)(data)

# in background
future = processor.save.<suitkaise-api>background</suitkaise-api>()("output.json")
```

You can even get an async version of the entire class:

```python
AsyncProcessor = DataProcessor.<suitkaise-api>asynced</suitkaise-api>()
processor = AsyncProcessor(config)

# all blocking methods are now async
await processor.process(data)
await processor.save("output.json")
```

## Auto-detects blocking code

`<suitkaise-api>sk</suitkaise-api>` uses AST analysis to inspect your function's source code and detect blocking patterns — `time.sleep()`, `requests.get()`, file I/O, database calls, subprocess calls, and many more.

```python
<suitkaise-api>@sk</suitkaise-api>
def slow_fetch(url):
    return requests.get(url).text

slow_fetch.<suitkaise-api>has_blocking_calls</suitkaise-api>  # True
slow_fetch.<suitkaise-api>blocking_calls</suitkaise-api>      # ['requests.get']
```

This detection controls which modifiers are available. `<suitkaise-api>.asynced()</suitkaise-api>` and `<suitkaise-api>.background()</suitkaise-api>` are only allowed on functions that actually block — preventing you from wrapping pure CPU code in `asyncio.to_thread()` where it wouldn't help.

If the AST can't detect your blocking code (C extensions, custom blocking functions, tight CPU loops), use `<suitkaise-api>@blocking</suitkaise-api>` to explicitly mark it:

```python
<suitkaise-api>@sk</suitkaise-api>
<suitkaise-api>@blocking</suitkaise-api>
def heavy_computation():
    return sum(x**2 for x in range(10_000_000))

# now .asynced() and .background() are available
result = await heavy_computation.<suitkaise-api>asynced</suitkaise-api>()()
```

## The hidden killer feature: `_shared_meta`

This is what makes `<suitkaise-api>sk</suitkaise-api>` essential to the `<suitkaise-api>suitkaise</suitkaise-api>` ecosystem.

When you put `<suitkaise-api>@sk</suitkaise-api>` on a class, it analyzes every method's AST to figure out which instance attributes each method reads and writes. It stores this as `_shared_meta`:

```python
<suitkaise-api>@sk</suitkaise-api>
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1

print(Counter._shared_meta)
# {
#     'methods': {
#         'increment': {'reads': ['value'], 'writes': ['value']}
#     },
#     'properties': {}
# }
```

Why does this matter? Because `<suitkaise-api>Share</suitkaise-api>` uses `_shared_meta` to know exactly which attributes to sync after each method call.

Without `_shared_meta`, `<suitkaise-api>Share</suitkaise-api>` would have to sync everything after every operation — slow and wasteful.

With `_shared_meta`, `<suitkaise-api>Share</suitkaise-api>` only syncs the attributes that actually changed. This is what makes `<suitkaise-api>Share</suitkaise-api>` practical at scale: the overhead is proportional to what you actually touch, not to the total size of the shared object.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>

<suitkaise-api>@sk</suitkaise-api>
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1

<suitkaise-api>share</suitkaise-api> = <suitkaise-api>Share(</suitkaise-api>)
share.counter = Counter()

# works across processes — Share knows to sync only 'value' after increment()
share.counter.increment()
```

If you're using `<suitkaise-api>Share</suitkaise-api>` with custom classes, `<suitkaise-api>@sk</suitkaise-api>` is what makes it efficient. Without it, `<suitkaise-api>Share</suitkaise-api>` still works, but you lose time every time `<suitkaise-api>Share</suitkaise-api>` needs to calculate `_shared_meta` for each object of that class.

## Compared to alternatives

### vs `tenacity`

Tenacity is a great retry library with more retry strategies and conditions than `<suitkaise-api>sk</suitkaise-api>`.

But tenacity bakes retry config into the function definition:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

<suitkaise-api>@retry</suitkaise-api>(stop=stop_after_attempt(3), wait=wait_exponential())
def fetch_data(url):
    return requests.get(url).json()

# every call retries. always. even in tests.
# want a timeout too? add another library or wrap it yourself.
```

With `<suitkaise-api>sk</suitkaise-api>`, you decide per call site:

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>

<suitkaise-api>@sk</suitkaise-api>
def fetch_data(url):
    return requests.get(url).json()

# production: retry with timeout
data = fetch_data.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com")

# tests: no retry, no timeout — just a normal call
data = fetch_data("https://api.example.com")

# one-off background fetch
future = fetch_data.<suitkaise-api>background</suitkaise-api>()("https://api.example.com")
```

Tenacity only does retry. `<suitkaise-api>sk</suitkaise-api>` gives you retry + timeout + background + rate_limit + async in one decorator, and lets you choose per call site.

### vs `asyncio.to_thread`

What `<suitkaise-api>.asynced()</suitkaise-api>` uses under the hood. `<suitkaise-api>sk</suitkaise-api>` wraps it in a consistent API and prevents you from using it on non-blocking code.

### vs `concurrent.futures`

What `<suitkaise-api>.background()</suitkaise-api>` uses under the hood. `<suitkaise-api>sk</suitkaise-api>` wraps it in the same chaining API as everything else.

### vs writing it yourself

You could absolutely implement retry + timeout + background manually. The value of `<suitkaise-api>sk</suitkaise-api>` is that all five modifiers share a consistent interface, chain naturally, and — most importantly — generate `_shared_meta` for `<suitkaise-api>Share</suitkaise-api>` compatibility, which you would never build yourself.

## Works with the rest of `<suitkaise-api>suitkaise</suitkaise-api>`

- `<suitkaise-api>processing</suitkaise-api>` — `<suitkaise-api>Pool</suitkaise-api>` methods use `<suitkaise-api>sk</suitkaise-api>` modifiers. `<suitkaise-api>Pool</suitkaise-api>.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(20).<suitkaise-api>asynced</suitkaise-api>()` works because of `<suitkaise-api>sk</suitkaise-api>`.
- `<suitkaise-api>Share</suitkaise-api>` — `_shared_meta` from `<suitkaise-api>sk</suitkaise-api>` is what makes `<suitkaise-api>Share</suitkaise-api>` efficient with custom classes.
- `<suitkaise-api>circuits</suitkaise-api>` — `<suitkaise-api>Circuit</suitkaise-api>.<suitkaise-api>short</suitkaise-api>()` has `<suitkaise-api>.asynced()</suitkaise-api>` because `<suitkaise-api>circuits</suitkaise-api>` uses `<suitkaise-api>sk</suitkaise-api>` internally.
- `<suitkaise-api>timing</suitkaise-api>` — `<suitkaise-api>timing</suitkaise-api>.sleep` has `<suitkaise-api>.asynced()</suitkaise-api>` via `<suitkaise-api>sk</suitkaise-api>`.
- `<suitkaise-api>paths</suitkaise-api>` — `<suitkaise-api>@autopath</suitkaise-api>()` can be combined with `<suitkaise-api>@sk</suitkaise-api>` on the same function.

`<suitkaise-api>sk</suitkaise-api>` is the glue. All `<suitkaise-api>suitkaise</suitkaise-api>` modules use it internally when applicable, and now your own code benefits from the same modifier system.
"
