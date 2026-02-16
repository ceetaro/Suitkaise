# Quick Start: `<suitkaise-api>timing</suitkaise-api>`

```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Time a function

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>timethis</suitkaise-api>

@<suitkaise-api>timethis</suitkaise-api>()
def process_data():
    do_work()

process_data()
print(process_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>)  # time for the last call
```

## Get statistics over multiple calls

```python
for _ in range(100):
    process_data()

print(process_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
print(process_data.<suitkaise-api>timer</suitkaise-api>.median)
print(process_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>)
print(process_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95))
print(process_data.<suitkaise-api>timer</suitkaise-api>.min)
print(process_data.<suitkaise-api>timer</suitkaise-api>.max)
```

## Time a code block

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>TimeThis</suitkaise-api>

with <suitkaise-api>TimeThis</suitkaise-api>() as timer:
    do_work()

print(<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>)
```

## Use a timer directly

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>

timer = <suitkaise-api>Sktimer</suitkaise-api>()

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
do_work()
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

print(<suitkaise-api>elapsed</suitkaise-api>)
print(<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
```

## Pause timing (exclude user input, delays, etc.)

```python
timer = <suitkaise-api>Sktimer</suitkaise-api>()
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

results = database.query("SELECT * FROM users")

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>pause</suitkaise-api>()
answer = input("Export? (y/n): ")
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>resume</suitkaise-api>()

if answer == 'y':
    export(results)

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()  # user input time excluded
```

## Discard failed measurements

```python
timer = <suitkaise-api>Sktimer</suitkaise-api>()

for _ in range(100):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    try:
        <suitkaise-api>result</suitkaise-api> = unreliable_operation()
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()
    except Exception:
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()  # don't pollute stats with failures
```

## Rolling window for long-running processes

```python
timer = <suitkaise-api>Sktimer</suitkaise-api>(max_times=1000)  # keep only last 1000 measurements
```

## Only record slow operations

```python
@<suitkaise-api>timethis</suitkaise-api>(threshold=0.1)
def handle_request():
    # only records times >= 0.1 seconds
    process_request()
```

## Want to learn more?

- **Why page** — why `<suitkaise-api>timing</suitkaise-api>` exists and what it does better than `timeit`
- **How to use** — full API reference for `<suitkaise-api>Sktimer</suitkaise-api>`, `<suitkaise-api>timethis</suitkaise-api>`, `<suitkaise-api>TimeThis</suitkaise-api>`
- **Examples** — progressively complex examples into a full script
- **How it works** — internal architecture (per-thread sessions, statistics) (level: intermediate)
