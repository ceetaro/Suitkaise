# Quick Start: `processing`

```bash
pip install suitkaise
```

## Run a process

```python
from suitkaise.processing import Skprocess

class Doubler(Skprocess):
    def __init__(self, value):
        self.value = value

    def __run__(self):
        self.value *= 2

    def __result__(self):
        return self.value

process = Doubler(5)
result = process.run() # start, wait, return result
print(result) # 10
```

## Run it multiple times

```python
class Doubler(Skprocess):
    def __init__(self, value):
        self.value = value
        self.process_config.runs = 3 # loop 3 times

    def __run__(self):
        self.value *= 2

    def __result__(self):
        return self.value

result = Doubler(5).run()
print(result) # 40 (5 → 10 → 20 → 40)
```

## Batch processing with Pool

```python
from suitkaise.processing import Pool

def double(x):
    return x * 2

pool = Pool(workers=4)
results = pool.map(double, [1, 2, 3, 4, 5])
print(results) # [2, 4, 6, 8, 10]
```

## Share state across processes

```python
from suitkaise.processing import Share, Pool, Skprocess

share = Share()
share.counter = 0
share.results = []

class Worker(Skprocess):
    def __init__(self, share, item):
        self.share = share
        self.item = item

    def __run__(self):
        self.share.results.append(self.item * 2)
        self.share.counter += 1

pool = Pool(workers=4)
pool.star().map(Worker, [(share, x) for x in range(10)])

print(share.counter) # 10
print(share.results) # [0, 2, 4, ..., 18]
```

## Communicate between parent and process

```python
from suitkaise.processing import Skprocess

class Echo(Skprocess):
    def __prerun__(self):
        self.msg = self.listen(timeout=1.0)

    def __run__(self):
        if self.msg:
            self.tell(f"echo: {self.msg}")

process = Echo()
process.start()

process.tell("hello")
response = process.listen(timeout=2.0)
print(response) # "echo: hello"

process.stop()
process.wait()
```

## Add retries and timeouts

```python
class ReliableWorker(Skprocess):
    def __init__(self):
        self.process_config.lives = 3 # retry up to 2 times on crash
        self.process_config.timeouts.run = 10.0 # 10 second timeout per run

    def __run__(self):
        do_work()
```

## Want to learn more?

- **Why page** — why `processing` exists and what problems it solves
- **How to use** — full API reference for `Skprocess`, `Pool`, `Share`, `Pipe`
- **Examples** — progressively complex examples into a full script
- **How it works** — internal architecture (level: advanced)
