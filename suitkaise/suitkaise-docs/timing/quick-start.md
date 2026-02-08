# Quick Start: `timing`

```bash
pip install suitkaise
```

## Time a function

```python
from suitkaise.timing import timethis

@timethis()
def process_data():
    do_work()

process_data()
print(process_data.timer.most_recent)  # time for the last call
```

## Get statistics over multiple calls

```python
for _ in range(100):
    process_data()

print(process_data.timer.mean)
print(process_data.timer.median)
print(process_data.timer.stdev)
print(process_data.timer.percentile(95))
print(process_data.timer.min)
print(process_data.timer.max)
```

## Time a code block

```python
from suitkaise.timing import TimeThis

with TimeThis() as timer:
    do_work()

print(timer.most_recent)
```

## Use a timer directly

```python
from suitkaise.timing import Sktimer

timer = Sktimer()

timer.start()
do_work()
elapsed = timer.stop()

print(elapsed)
print(timer.mean)
```

## Pause timing (exclude user input, delays, etc.)

```python
timer = Sktimer()
timer.start()

results = database.query("SELECT * FROM users")

timer.pause()
answer = input("Export? (y/n): ")
timer.resume()

if answer == 'y':
    export(results)

timer.stop()  # user input time excluded
```

## Discard failed measurements

```python
timer = Sktimer()

for _ in range(100):
    timer.start()
    try:
        result = unreliable_operation()
        timer.stop()
    except Exception:
        timer.discard()  # don't pollute stats with failures
```

## Rolling window for long-running processes

```python
timer = Sktimer(max_times=1000)  # keep only last 1000 measurements
```

## Only record slow operations

```python
@timethis(threshold=0.1)
def handle_request():
    # only records times >= 0.1 seconds
    process_request()
```

## Want to learn more?

- **Why page** — why `timing` exists and what it does better than `timeit`
- **How to use** — full API reference for `Sktimer`, `timethis`, `TimeThis`
- **Examples** — progressively complex examples into a full script
- **How it works** — internal architecture (per-thread sessions, statistics) (level: intermediate)
