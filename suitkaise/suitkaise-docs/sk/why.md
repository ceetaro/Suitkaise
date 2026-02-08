# Why you should use `sk`

## TLDR

- **One decorator, five superpowers** - Add `.retry()`, `.timeout()`, `.background()`, `.rate_limit()`, and `.asynced()` to any function or class
- **Modify at the call site, not the definition** - Define your function once, decide how to call it each time
- **Chain modifiers in any order** - `fn.retry(3).timeout(5.0)` and `fn.timeout(5.0).retry(3)` do the same thing
- **Auto-detects blocking code** - AST analysis identifies I/O, network calls, and sleep patterns automatically
- **`Share` metadata generation** - The kicker. Makes your classes work efficiently inside `Share`
- **Classes too** - Works on entire classes, giving every method the same modifier capabilities, and an async class pattern as well

---

## The problem with retry, timeout, and async libraries

You probably already use something for retry logic. Maybe `tenacity`. Maybe a hand-rolled decorator.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def fetch_data(url):
    return requests.get(url).json()
```

This works. But now your function always retries. Every call. Every time.

What if you want to retry in production but not in tests? What if one call site needs a timeout but another doesn't? What if you want to run it in the background just this once?

You end up with multiple wrapped versions of the same function, or you start passing flags and config around.

## `sk` — modify at the call site, not the definition

`sk` takes a different approach. You define your function once, cleanly. Then you decide how to call it each time.

```python
from suitkaise import sk

@sk
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
data = fetch_data.retry(times=3, delay=1.0, backoff_factor=2.0)("https://api.example.com")

# timeout after 5 seconds
data = fetch_data.timeout(5.0)("https://api.example.com")

# run in background, get a Future
future = fetch_data.background()("https://api.example.com")
result = future.result()

# rate limit to 2 calls per second
data = fetch_data.rate_limit(2.0)("https://api.example.com")

# make it async
data = await fetch_data.asynced()("https://api.example.com")
```

The function definition stays clean. The call site says exactly what's happening. No wrapper functions, no config objects, no multiple versions.

## Chain modifiers

Modifiers can be chained in any order:

```python
# retry 3 times, with a 5-second timeout per attempt
data = fetch_data.retry(3).timeout(5.0)("https://api.example.com")

# same thing, different order — identical behavior
data = fetch_data.timeout(5.0).retry(3)("https://api.example.com")
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
    fetch_data.asynced()
    .retry(times=3, delay=0.5)
    .timeout(10.0)
    .rate_limit(5.0)
)("https://api.example.com")
```

## The double parentheses look a little confusing

They do! But it's actually really simple.

This is intentional. The actual function arguments are always at the end of the chain:

```python
fetch_data.retry(3).timeout(5.0)("https://api.example.com")
#         ^^^^^^^^  ^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^
#         modifier   modifier      actual function args
```

You might notice the pattern: `fn.modifier()("args")`. The first call sets up the modifier. The second call runs the function.

Once you see it, it's easy to read: everything before the last parentheses is configuration, the last parentheses are the call.

But now when reviewing code, you can quickly see how it is being modified without sifting through 5 extra args in the main function call.

## Works on classes too

`@sk` isn't just for functions. Put it on a class and every method gets modifiers:

```python
@sk
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
processor.save.timeout(10.0)("output.json")

# with retry
processor.process.retry(3)(data)

# in background
future = processor.save.background()("output.json")
```

You can even get an async version of the entire class:

```python
AsyncProcessor = DataProcessor.asynced()
processor = AsyncProcessor(config)

# all blocking methods are now async
await processor.process(data)
await processor.save("output.json")
```

## Auto-detects blocking code

`sk` uses AST analysis to inspect your function's source code and detect blocking patterns — `time.sleep()`, `requests.get()`, file I/O, database calls, subprocess calls, and many more.

```python
@sk
def slow_fetch(url):
    return requests.get(url).text

slow_fetch.has_blocking_calls  # True
slow_fetch.blocking_calls      # ['requests.get']
```

This detection controls which modifiers are available. `.asynced()` and `.background()` are only allowed on functions that actually block — preventing you from wrapping pure CPU code in `asyncio.to_thread()` where it wouldn't help.

If the AST can't detect your blocking code (C extensions, custom blocking functions, tight CPU loops), use `@blocking` to explicitly mark it:

```python
@sk
@blocking
def heavy_computation():
    return sum(x**2 for x in range(10_000_000))

# now .asynced() and .background() are available
result = await heavy_computation.asynced()()
```

## The hidden killer feature: `_shared_meta`

This is what makes `sk` essential to the `suitkaise` ecosystem.

When you put `@sk` on a class, it analyzes every method's AST to figure out which instance attributes each method reads and writes. It stores this as `_shared_meta`:

```python
@sk
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

Why does this matter? Because `Share` uses `_shared_meta` to know exactly which attributes to sync after each method call.

Without `_shared_meta`, `Share` would have to sync everything after every operation — slow and wasteful.

With `_shared_meta`, `Share` only syncs the attributes that actually changed. This is what makes `Share` practical at scale: the overhead is proportional to what you actually touch, not to the total size of the shared object.

```python
from suitkaise.processing import Share

@sk
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1

share = Share()
share.counter = Counter()

# works across processes — Share knows to sync only 'value' after increment()
share.counter.increment()
```

If you're using `Share` with custom classes, `@sk` is what makes it efficient. Without it, `Share` still works, but you lose time every time `Share` needs to calculate `_shared_meta` for each object of that class.

## Compared to alternatives

**vs `tenacity`** — Tenacity is a great retry library with more retry strategies and conditions than `sk`. But tenacity only does retry, and it bakes the retry config into the function definition. `sk` gives you retry + timeout + background + rate_limit + async in one decorator, and lets you choose per call site.

**vs `asyncio.to_thread`** — What `.asynced()` uses under the hood. `sk` wraps it in a consistent API and prevents you from using it on non-blocking code.

**vs `concurrent.futures`** — What `.background()` uses under the hood. `sk` wraps it in the same chaining API as everything else.

**vs writing it yourself** — You could absolutely implement retry + timeout + background manually. The value of `sk` is that all five modifiers share a consistent interface, chain naturally, and — most importantly — generate `_shared_meta` for `Share` compatibility, which you would never build yourself.

## Works with the rest of `suitkaise`

- `processing` — `Pool` methods use `sk` modifiers. `Pool.map.timeout(20).asynced()` works because of `sk`.
- `Share` — `_shared_meta` from `sk` is what makes `Share` efficient with custom classes.
- `circuits` — `Circuit.short()` has `.asynced()` because `circuits` uses `sk` internally.
- `timing` — `timing.sleep` has `.asynced()` via `sk`.
- `paths` — `@autopath()` can be combined with `@sk` on the same function.

`sk` is the glue. All `suitkaise` modules use it internally when applicable, and now your own code benefits from the same modifier system.
