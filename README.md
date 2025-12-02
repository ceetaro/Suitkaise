# Suitkaise

Making things easier for developers of all skill levels to develop complex applications.

## Installation

```bash
pip install suitkaise
```

## Modules

### cerial - Serialization for the Unpicklable

Serialize objects that standard pickle can't handle: locks, loggers, file handles, circular references, and more.

```python
from suitkaise import cerial

# Serialize any object - even with locks and loggers
data = cerial.serialize(complex_object)

# Deserialize back
restored = cerial.deserialize(data)
```

### circuit - Circuit Breaker Pattern

Controlled failure handling and resource management in loops.

```python
from suitkaise import circuit

breaker = circuit.Circuit(shorts=3, break_sleep=1.0)

while breaker.flowing:
    try:
        result = risky_operation()
        break
    except SomeError:
        breaker.short()  # Break after 3 failures
```

### skpath - Smart Path Operations

Intelligent path handling with dual-path architecture and automatic project root detection.

```python
from suitkaise import skpath

# Auto-detects caller file path
path = skpath.SKPath()

# Dual paths: absolute and project-relative
print(path.ap)  # /Users/you/MyProject/src/main.py
print(path.np)  # MyProject/src/main.py

# Get project root automatically
root = skpath.get_project_root()
```

### sktime - Smart Timing Operations

Intuitive timing with statistical analysis.

```python
from suitkaise import sktime

# Simple timing
start = sktime.now()
sktime.sleep(1)
elapsed = sktime.elapsed(start)

# Statistical timer
timer = sktime.Timer()
timer.start()
# ... work ...
timer.stop()
print(f"Mean: {timer.mean}, Stdev: {timer.stdev}")

# Decorator for automatic timing
@sktime.timethis()
def my_function():
    pass

my_function()
print(my_function.timer.most_recent)
```

## Requirements

- Python 3.11+
- No external dependencies (standard library only)

## License

MIT License - see [LICENSE](LICENSE) for details.
