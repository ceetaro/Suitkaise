/*

synced from suitkaise-docs/processing/quick-start.md

*/

rows = 2
columns = 1

# 1.1

title = "`<suitkaise-api>processing</suitkaise-api>` quick start guide"

# 1.2

text = "
```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Run a process

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class Doubler(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, value):
        self.value = value

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.value *= 2

    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.value

process = Doubler(5)
result = <suitkaise-api>process.run()</suitkaise-api> # start, wait, return result
print(result) # 10
```

## Run it multiple times

```python
class Doubler(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, value):
        self.value = value
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 3 # loop 3 times

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.value *= 2

    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.value

result = Doubler(5).<suitkaise-api>run</suitkaise-api>()
print(result) # 40 (5 → 10 → 20 → 40)
```

## Batch processing with Pool

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>

def double(x):
    return x * 2

<suitkaise-api>pool</suitkaise-api> = <suitkaise-api>Pool(</suitkaise-api>workers=4)
results = <suitkaise-api>pool.map(</suitkaise-api>double, [1, 2, 3, 4, 5])
print(results) # [2, 4, 6, 8, 10]
```

## Share state across processes

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

<suitkaise-api>share</suitkaise-api> = <suitkaise-api>Share(</suitkaise-api>)
share.counter = 0
share.results = []

class Worker(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, share, item):
        self.share = share
        self.item = item

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.share.results.append(self.item * 2)
        self.share.counter += 1

<suitkaise-api>pool</suitkaise-api> = <suitkaise-api>Pool(</suitkaise-api>workers=4)
<suitkaise-api>pool.star()</suitkaise-api>.<suitkaise-api>map</suitkaise-api>(Worker, [(share, x) for x in range(10)])

print(share.counter) # 10
print(share.results) # [0, 2, 4, ..., 18]
```

## Communicate between parent and process

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class Echo(<suitkaise-api>Skprocess</suitkaise-api>):
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        self.msg = self.<suitkaise-api>listen</suitkaise-api>(timeout=1.0)

    def <suitkaise-api>__run__</suitkaise-api>(self):
        if self.msg:
            self.<suitkaise-api>tell</suitkaise-api>(f"echo: {self.msg}")

process = Echo()
<suitkaise-api>process.start()</suitkaise-api>

<suitkaise-api>process.tell(</suitkaise-api>"hello")
response = <suitkaise-api>process.listen(</suitkaise-api>timeout=2.0)
print(response) # "echo: hello"

<suitkaise-api>process.stop()</suitkaise-api>
<suitkaise-api>process.wait()</suitkaise-api>
```

## Add retries and timeouts

```python
class ReliableWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self):
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>lives</suitkaise-api> = 3 # retry up to 2 times on crash
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>run</suitkaise-api> = 10.0 # 10 second timeout per run

    def <suitkaise-api>__run__</suitkaise-api>(self):
        do_work()
```

## Want to learn more?

- **Why page** — why `<suitkaise-api>processing</suitkaise-api>` exists and what problems it solves
- **How to use** — full API reference for `<suitkaise-api>Skprocess</suitkaise-api>`, `<suitkaise-api>Pool</suitkaise-api>`, `<suitkaise-api>Share</suitkaise-api>`, `<suitkaise-api>Pipe</suitkaise-api>`
- **Examples** — progressively complex examples into a full script
- **How it works** — internal architecture (level: advanced)
"
