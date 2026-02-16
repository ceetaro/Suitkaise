/*

synced from suitkaise-docs/paths/quick-start.md

*/

rows = 2
columns = 1

# 1.1

title = "Quick Start: `<suitkaise-api>paths</suitkaise-api>`"

# 1.2

text = "
```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Create a project-relative path

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

path = <suitkaise-api>Skpath</suitkaise-api>("data/file.txt")

path.ap   # "/Users/me/project/data/file.txt" — absolute, normalized
path.rp   # "data/file.txt" — relative to project root, same on every machine
path.<suitkaise-api>id</suitkaise-api>   # "ZGF0YS9maWxlLnR4dA" — reversible ID for database storage
```

## Get the current file's path

```python
here = <suitkaise-api>Skpath</suitkaise-api>()  # no arguments = caller's file path
print(here.rp)   # "src/my_module.py"
```

## Get the project root

```python
root = <suitkaise-api>Skpath</suitkaise-api>().<suitkaise-api>root</suitkaise-api>
print(<suitkaise-api>root</suitkaise-api>.ap)  # "/Users/me/project"

# or directly
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
```

## Auto-convert path types with `@<suitkaise-api>autopath</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>

@<suitkaise-api>autopath</suitkaise-api>()
def process(path: <suitkaise-api>AnyPath</suitkaise-api>):
    # path is always an <suitkaise-api>Skpath</suitkaise-api>, no matter what was passed in
    print(path.rp)

process("data/file.txt")                  # str → <suitkaise-api>Skpath</suitkaise-api>
process(Path("data/file.txt"))            # Path → <suitkaise-api>Skpath</suitkaise-api>
process(<suitkaise-api>Skpath</suitkaise-api>("data/file.txt"))          # <suitkaise-api>Skpath</suitkaise-api> → <suitkaise-api>Skpath</suitkaise-api>
```

## Use `<suitkaise-api>Skpath</suitkaise-api>` like `pathlib.Path`

Everything `pathlib` does, `<suitkaise-api>Skpath</suitkaise-api>` does too:

```python
path = <suitkaise-api>Skpath</suitkaise-api>("src")

# join <suitkaise-api>paths</suitkaise-api>
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
path = <suitkaise-api>Skpath</suitkaise-api>("data/reports/q1.csv")

# store a compact, reversible ID
db.execute("INSERT INTO files (path_id) VALUES (?)", (path.<suitkaise-api>id</suitkaise-api>,))

# reconstruct later
same_path = <suitkaise-api>Skpath</suitkaise-api>("ZGF0YS9yZXBvcnRzL3ExLmNzdg")
print(same_path.rp)  # "data/reports/q1.csv"
```

## Validate and sanitize filenames

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>is_valid_filename</suitkaise-api>, <suitkaise-api>streamline_path_quick</suitkaise-api>

<suitkaise-api>is_valid_filename</suitkaise-api>("report.pdf")        # True
<suitkaise-api>is_valid_filename</suitkaise-api>("file<name>.txt")    # False
<suitkaise-api>is_valid_filename</suitkaise-api>("CON")               # False (Windows reserved)

<suitkaise-api>streamline_path_quick</suitkaise-api>("My File (1).txt")  # "My_File__1_.txt"
```

## Temporary root override for testing

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>CustomRoot</suitkaise-api>, <suitkaise-api>Skpath</suitkaise-api>

with <suitkaise-api>CustomRoot</suitkaise-api>("/tmp/test_project"):
    path = <suitkaise-api>Skpath</suitkaise-api>("config/settings.yaml")
    assert path.root_str == "/tmp/test_project"
```

## Want to learn more?

- **Why page** — why `<suitkaise-api>paths</suitkaise-api>` exists, cross-platform pitfalls, `@<suitkaise-api>autopath</suitkaise-api>`, and more
- **How to use** — full API reference for `<suitkaise-api>Skpath</suitkaise-api>`, `@<suitkaise-api>autopath</suitkaise-api>`, and all utility functions
- **Examples** — progressively complex examples into a full script
- **How it works** — project root detection, caller detection, path normalization (level: intermediate)
"
