/*

synced from suitkaise-docs/paths/quick-start.md

*/

rows = 2
columns = 1

# 1.1

title = "`<suitkaise-api>paths</suitkaise-api>` quick start guide"

# 1.2

text = "
```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Create a project-relative path

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"data/file.txt")

<suitkaise-api>path.ap</suitkaise-api>   # "/Users/me/project/data/file.txt" — absolute, normalized
<suitkaise-api>path.rp</suitkaise-api>   # "data/file.txt" — relative to project root, same on every machine
<suitkaise-api>path.id</suitkaise-api>   # "ZGF0YS9maWxlLnR4dA" — reversible ID for database storage
<suitkaise-api>path.platform</suitkaise-api>   # platform-specific absolute path
```

## Get the current file's path

```python
<suitkaise-api>here</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>)  # no arguments = caller's file path
print(<suitkaise-api>here.rp</suitkaise-api>)   # "src/my_module.py"
```

## Get the project root

```python
<suitkaise-api>root</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>).<suitkaise-api>root</suitkaise-api>
print(<suitkaise-api>root.ap</suitkaise-api>)  # "/Users/me/project"

# or directly
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
```

## Auto-convert path types with `<suitkaise-api>@autopath</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>

<suitkaise-api>@autopath</suitkaise-api>()
def process(path: <suitkaise-api>AnyPath</suitkaise-api>):
    # path is always an Skpath, no matter what was passed in
    print(<suitkaise-api>path.rp</suitkaise-api>)

process("data/file.txt")                  # str → Skpath
process(Path("data/file.txt"))            # Path → Skpath
process(<suitkaise-api>Skpath(</suitkaise-api>"data/file.txt"))          # Skpath → Skpath
```

## Use `<suitkaise-api>Skpath</suitkaise-api>` like `pathlib.Path`

Everything `pathlib` does, `<suitkaise-api>Skpath</suitkaise-api>` does too:

```python
<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"src")

# join paths
config = path / "config" / "settings.yaml"

# read/write
config.write_text('{"debug": true}')
data = config.read_text()

# iterate
for py_file in <suitkaise-api>path.rglob(</suitkaise-api>"*.py"):
    print(<suitkaise-api>py_file.rp</suitkaise-api>)

# check existence
if config.exists:
    print(config.name)
```

## Path IDs for database storage (reversible IDs)

```python
<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"data/reports/q1.csv")

# store a compact, reversible ID
db.execute("INSERT INTO files (path_id) VALUES (?)", (<suitkaise-api>path.id</suitkaise-api>,))

# reconstruct later
<suitkaise-api>same_path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"ZGF0YS9yZXBvcnRzL3ExLmNzdg")
print(<suitkaise-api>same_path.rp</suitkaise-api>)  # "data/reports/q1.csv"
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

with <suitkaise-api>CustomRoot(</suitkaise-api>"/tmp/test_project"):
    <suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"config/settings.yaml")
    assert path.root_str == "/tmp/test_project"
```

## Want to learn more?

- **Why page** — why `<suitkaise-api>paths</suitkaise-api>` exists, cross-platform pitfalls, `<suitkaise-api>@autopath</suitkaise-api>`, and more
- **How to use** — full API reference for `<suitkaise-api>Skpath</suitkaise-api>`, `<suitkaise-api>@autopath</suitkaise-api>`, and all utility functions
- **Examples** — progressively complex examples into a full script
- **How it works** — project root detection, caller detection, path normalization (level: intermediate)
"
