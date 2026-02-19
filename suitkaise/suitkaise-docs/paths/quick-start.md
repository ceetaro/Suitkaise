# `paths` quick start guide

```bash
pip install suitkaise
```

## Create a project-relative path

```python
from suitkaise.paths import Skpath

path = Skpath("data/file.txt")

path.ap   # "/Users/me/project/data/file.txt" — absolute, normalized
path.rp   # "data/file.txt" — relative to project root, same on every machine
path.id   # "ZGF0YS9maWxlLnR4dA" — reversible ID for database storage
path.platform   # platform-specific absolute path
```

## Get the current file's path

```python
here = Skpath()  # no arguments = caller's file path
print(here.rp)   # "src/my_module.py"
```

## Get the project root

```python
root = Skpath().root
print(root.ap)  # "/Users/me/project"

# or directly
from suitkaise import paths
root = paths.get_project_root()
```

## Auto-convert path types with `@autopath`

```python
from suitkaise.paths import autopath, AnyPath

@autopath()
def process(path: AnyPath):
    # path is always an Skpath, no matter what was passed in
    print(path.rp)

process("data/file.txt")                  # str → Skpath
process(Path("data/file.txt"))            # Path → Skpath
process(Skpath("data/file.txt"))          # Skpath → Skpath
```

## Use `Skpath` like `pathlib.Path`

Everything `pathlib` does, `Skpath` does too:

```python
path = Skpath("src")

# join paths
config = path / "config" / "settings.yaml"

# read/write
config.write_text('{"debug": true}')
data = config.read_text()

# iterate
for py_file in path.rglob("*.py"):
    print(py_file.rp)

# check existence
if config.exists:
    print(config.name)
```

## Path IDs for database storage (reversible IDs)

```python
path = Skpath("data/reports/q1.csv")

# store a compact, reversible ID
db.execute("INSERT INTO files (path_id) VALUES (?)", (path.id,))

# reconstruct later
same_path = Skpath("ZGF0YS9yZXBvcnRzL3ExLmNzdg")
print(same_path.rp)  # "data/reports/q1.csv"
```

## Validate and sanitize filenames

```python
from suitkaise.paths import is_valid_filename, streamline_path_quick

is_valid_filename("report.pdf")        # True
is_valid_filename("file<name>.txt")    # False
is_valid_filename("CON")               # False (Windows reserved)

streamline_path_quick("My File (1).txt")  # "My_File__1_.txt"
```

## Temporary root override for testing

```python
from suitkaise.paths import CustomRoot, Skpath

with CustomRoot("/tmp/test_project"):
    path = Skpath("config/settings.yaml")
    assert path.root_str == "/tmp/test_project"
```

## Want to learn more?

- **Why page** — why `paths` exists, cross-platform pitfalls, `@autopath`, and more
- **How to use** — full API reference for `Skpath`, `@autopath`, and all utility functions
- **Examples** — progressively complex examples into a full script
- **How it works** — project root detection, caller detection, path normalization (level: intermediate)
