/*

synced from suitkaise-docs/paths/examples.md

*/

rows = 2
columns = 1

# 1.1

title = "`paths` examples"

# 1.2

text = "

(start of dropdown "Basic Examples")
## Basic Examples

### Get the current file's path

Getting the path of the file you're currently writing code in - usually a pain with `__file__` and `Path`.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

# Skpath() with no arguments returns the caller's file path
# this is the file where this line of code is written
<suitkaise-api>current_file</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>)

# get the absolute path (always uses forward slashes)
print(<suitkaise-api>current_file.ap</suitkaise-api>)
# "/Users/me/myproject/src/utils/helpers.py"

# get the path relative to project root
# (empty if the caller is outside the detected project root)
print(<suitkaise-api>current_file.rp</suitkaise-api>)
# "src/utils/helpers.py"

# get just the filename
print(current_file.name)
# "helpers.py"
```

### Get the current directory

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

# Skpath().parent gives you the directory containing the current file
<suitkaise-api>current_dir</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>).<suitkaise-api>parent</suitkaise-api>

# now you can access sibling files easily using truediv
config_file = current_dir / "config.json"
data_dir = current_dir / "data"

# check if they exist
if config_file.exists:
    print(f"Config found at: {config_file.rp}")
```

### Alternative: use the helper functions

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>

# get_caller_path() is equivalent to Skpath()
current_file = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_caller_path</suitkaise-api>()

# get_current_dir() is equivalent to Skpath().parent
current_dir = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_current_dir</suitkaise-api>()

# get_cwd() returns the current working directory (where you ran python from)
cwd = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_cwd</suitkaise-api>()

# these are different!
# - current_dir: directory containing THIS file
# - cwd: directory where `python script.py` was run from
```

### Project root detection

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

# get the project root (auto-detected)
root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
print(<suitkaise-api>root</suitkaise-api>.ap)
# "/Users/me/myproject"

# project root is detected by looking for:
# 1. setup.sk (suitkaise marker - highest priority)
# 2. setup.py, setup.cfg, pyproject.toml
# 3. .git, .gitignore
# 4. LICENSE, README files
# 5. requirements.txt

# you can also access root from any Skpath
<suitkaise-api>some_file</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"src/main.py")
print(some_file.<suitkaise-api>root</suitkaise-api>.ap)
# "/Users/me/myproject"
```

### Override project root detection

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>CustomRoot</suitkaise-api>

# set a custom root manually
<suitkaise-api>paths</suitkaise-api>.<suitkaise-api>set_custom_root</suitkaise-api>("/my/custom/root")

# now all Skpath objects use this root
path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
print(<suitkaise-api>path.ap</suitkaise-api>)
# "/my/custom/root"

# clear it to go back to auto-detection
<suitkaise-api>paths</suitkaise-api>.<suitkaise-api>clear_custom_root</suitkaise-api>()

# or use a context manager for temporary override
with <suitkaise-api>CustomRoot(</suitkaise-api>"/temp/project"):
    # inside this block, root is /temp/project
    root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
    print(<suitkaise-api>root</suitkaise-api>.ap)
    # "/temp/project"

# outside the block, root is auto-detected again
```

### Path joining with `/`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

# Skpath supports the / operator like pathlib.Path
<suitkaise-api>root</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>).<suitkaise-api>root</suitkaise-api>
data_file = root / "data" / "users.json"

# the result is always an Skpath
print(type(data_file))
# <class 'suitkaise.paths._int.skpath.Skpath'>

print(data_file.ap)
# "/Users/me/myproject/data/users.json"

print(data_file.rp)
# "data/users.json"
```

### Core properties: `ap`, `rp`, `id`, `platform`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"src/utils/helpers.py")

# ap: absolute path (always forward slashes, even on Windows)
print(<suitkaise-api>path.ap</suitkaise-api>)
# "/Users/me/myproject/src/utils/helpers.py"

# rp: relative path to project root
print(<suitkaise-api>path.rp</suitkaise-api>)
# "src/utils/helpers.py"

# platform: absolute path with platform-native separators
print(<suitkaise-api>path.platform</suitkaise-api>)
# "C:\\Users\\me\\project\\src\\utils\\helpers.py" on Windows 
# "/Users/me/project/src/utils/helpers.py" on Mac/Linux

# id: reversible base64url encoded ID
print(path.<suitkaise-api>id</suitkaise-api>)
# "c3JjL3V0aWxzL2hlbHBlcnMucHk"

# you can recreate the path from its ID!
<suitkaise-api>same_path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>path.<suitkaise-api>id</suitkaise-api>)
print(<suitkaise-api>same_path.rp</suitkaise-api>)
# "src/utils/helpers.py"
```

### `pathlib` compatibility

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"src/main.py")

# all the familiar pathlib properties work
print(path.name)      # "main.py"
print(path.stem)      # "main"
print(path.suffix)    # ".py"
print(<suitkaise-api>path.parent</suitkaise-api>)    # Skpath("src")
print(path.exists)    # True or False

# pathlib methods work too
for py_file in <suitkaise-api>path.parent</suitkaise-api>.glob("*.py"):
    print(py_file.name)

# recursive glob
for py_file in <suitkaise-api>Skpath(</suitkaise-api>).<suitkaise-api>root</suitkaise-api>.rglob("*.py"):
    print(<suitkaise-api>py_file.rp</suitkaise-api>)
```

### File operations

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

<suitkaise-api>root</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>).<suitkaise-api>root</suitkaise-api>

# create directories
new_dir = root / "output/reports"
new_dir.mkdir(parents=True, exist_ok=True)

# create files
new_file = new_dir / "report.txt"
new_file.touch()

# copy files
source = root / "data/input.csv"
dest = source.copy_to(root / "backup/input.csv", parents=True)
# dest is an Skpath pointing to the copied file

# move files
temp_file = root / "temp/data.json"
final = temp_file.move_to(root / "data/final.json", overwrite=True)

# delete files
old_file = root / "temp/old.txt"
old_file.unlink(missing_ok=True)

# delete empty directories
empty_dir = root / "temp/empty"
empty_dir.rmdir()
```

### Cross-platform compatibility

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

# Skpath always uses forward slashes internally
# this works on Windows, Mac, and Linux
<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"data\\subdir\\file.txt")  # Windows-style input
print(<suitkaise-api>path.ap</suitkaise-api>)
# "/Users/me/project/data/subdir/file.txt" (forward slashes)

# when you need OS-native separators (ex. for subprocess calls)
print(<suitkaise-api>path.platform</suitkaise-api>)
# Windows: "C:\\Users\\me\\project\\data\\subdir\\file.txt"
# Mac/Linux: "/Users/me/project/data/subdir/file.txt"

# works with open() and os functions automatically
with open(path, "r") as f:  # uses __fspath__()
    content = f.read()
```

### Path validation

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>is_valid_filename</suitkaise-api>, <suitkaise-api>streamline_path</suitkaise-api>, <suitkaise-api>streamline_path_quick</suitkaise-api>

# check if a filename is valid on all platforms
print(<suitkaise-api>is_valid_filename</suitkaise-api>("my_file.txt"))      # True
print(<suitkaise-api>is_valid_filename</suitkaise-api>("file<name>.txt"))   # False (< and > are invalid)
print(<suitkaise-api>is_valid_filename</suitkaise-api>("CON"))              # False (Windows reserved name)
print(<suitkaise-api>is_valid_filename</suitkaise-api>(""))                 # False (empty)

# sanitize a filename
clean = <suitkaise-api>streamline_path</suitkaise-api>("My File<1>.txt", chars_to_replace=" ")
print(clean)
# "My_File_1_.txt"

# streamline_path_quick: simple version with common defaults
# - strips whitespace
# - replaces spaces
# - removes unicode
clean = <suitkaise-api>streamline_path_quick</suitkaise-api>("My File наме.txt")
print(clean)
# "My_File_____.txt"

# limit length (preserves file extension)
short = <suitkaise-api>streamline_path</suitkaise-api>("Very Long Filename That Needs Truncating.txt", max_len=10, chars_to_replace=" ")
print(short)
# "Very_Long_.txt"
```

### Get project structure

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>

# get all paths in the project (respects .gitignore)
all_paths = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>()
for p in all_paths[:5]:
    print(<suitkaise-api>p.rp</suitkaise-api>)

# get as strings (more memory efficient for large projects)
all_paths_str = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>(as_strings=True)

# exclude certain directories
paths_filtered = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>(exclude=["node_modules", "dist", ".git"])

# get nested dictionary structure for something like a UI tree
structure = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_structure</suitkaise-api>()
# {
#     "myproject": {
#         "src": {
#             "main.py": {},
#             "utils": {
#                 "helpers.py": {}
#             }
#         }
#     }
# }

# get formatted tree string for something like a README
tree = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_formatted_project_tree</suitkaise-api>(depth=2)
print(tree)
# myproject/
# ├── src/
# │   ├── main.py
# │   └── utils/
# └── tests/
```

### Get module path

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
import json

# get the file path where a module is defined
json_path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_module_path</suitkaise-api>(json)
print(json_path.ap)
# "/usr/lib/python3.11/json/__init__.py"

# works with classes too
from collections import OrderedDict
od_path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_module_path</suitkaise-api>(OrderedDict)
print(od_path.ap)

# works with your own modules
from myapp.utils import MyClass
my_path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_module_path</suitkaise-api>(MyClass)
print(my_path.rp)
# "myapp/utils.py"
```

### Thread safety

```python
import threading
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>, <suitkaise-api>CustomRoot</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>

# Skpath and root management functions are thread-safe
# multiple threads can safely:
# - create Skpath objects
# - access project root
# - use CustomRoot context manager

results = []

def worker(worker_id: int):
    # each thread can safely create paths
    <suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>f"data/file_{worker_id}.txt")
    
    # thread-safe access to properties
    results.append({
        "id": worker_id,
        "ap": <suitkaise-api>path.ap</suitkaise-api>,
        "rp": <suitkaise-api>path.rp</suitkaise-api>,
    })

# start multiple threads
threads = []
for i in range(10):
    t = threading.Thread(target=worker, args=(i,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print(f"Processed {len(results)} paths safely")
```
(end of dropdown "Basic Examples")

(start of dropdown "Advanced Examples")
## Advanced Examples

### Using `<suitkaise-api>autopath</suitkaise-api>` decorator

The `<suitkaise-api>autopath</suitkaise-api>` decorator automatically converts path parameters based on type hints.

```python
# WITHOUT autopath - you have to handle type conversion manually
def process_file_manual(path):
    if isinstance(path, str):
        path = Path(path)
    elif isinstance(path, <suitkaise-api>Skpath</suitkaise-api>):
        path = Path(<suitkaise-api>path.ap</suitkaise-api>)
    # ... now path is a Path
    return path.read_text()
```

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>Skpath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>
from pathlib import Path

# WITH autopath - conversion is automatic based on type hints
<suitkaise-api>@autopath</suitkaise-api>()
def process_file(path: <suitkaise-api>Skpath</suitkaise-api>) -> str:
    # path is guaranteed to be an Skpath
    # you can pass str, Path, or Skpath - all get converted
    return <suitkaise-api>path.ap</suitkaise-api>

# all of these work:
process_file("src/main.py")            # str → Skpath
process_file(Path("src/main.py"))      # Path → Skpath
process_file(<suitkaise-api>Skpath(</suitkaise-api>"src/main.py"))    # Skpath → Skpath (no conversion needed)
```

### `<suitkaise-api>autopath</suitkaise-api>` with different target types

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>Skpath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>
from pathlib import Path

<suitkaise-api>@autopath</suitkaise-api>()
def needs_skpath(path: <suitkaise-api>Skpath</suitkaise-api>) -> str:
    # input is converted to Skpath
    return <suitkaise-api>path.rp</suitkaise-api>

<suitkaise-api>@autopath</suitkaise-api>()
def needs_path(path: Path) -> str:
    # input is normalized through Skpath, then converted to Path
    return str(path)

<suitkaise-api>@autopath</suitkaise-api>()
def needs_string(path: str) -> str:
    # input is normalized through Skpath, returns absolute path string
    return path

<suitkaise-api>@autopath</suitkaise-api>()
def needs_anypath(path: <suitkaise-api>AnyPath</suitkaise-api>) -> str:
    # AnyPath is a union of str | Path | Skpath
    # autopath converts to Skpath (the richest type in the union)
    return <suitkaise-api>path.rp</suitkaise-api>  # path is Skpath
```

### `<suitkaise-api>autopath</suitkaise-api>` with lists

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>Skpath</suitkaise-api>
from pathlib import Path

<suitkaise-api>@autopath</suitkaise-api>()
def process_files(<suitkaise-api>paths</suitkaise-api>: list[<suitkaise-api>Skpath</suitkaise-api>]) -> list[str]:
    # each element in the list is converted to Skpath
    return [<suitkaise-api>p.rp</suitkaise-api> for p in <suitkaise-api>paths</suitkaise-api>]

# works with mixed input types
result = process_files([
    "src/a.py",              # str
    Path("src/b.py"),        # Path
    <suitkaise-api>Skpath(</suitkaise-api>"src/c.py"),      # Skpath
])
print(result)
# ["src/a.py", "src/b.py", "src/c.py"]

# also works with tuple, set, frozenset
<suitkaise-api>@autopath</suitkaise-api>()
def process_set(<suitkaise-api>paths</suitkaise-api>: set[<suitkaise-api>Skpath</suitkaise-api>]) -> int:
    return len(<suitkaise-api>paths</suitkaise-api>)
```

### `<suitkaise-api>autopath</suitkaise-api>` with `use_caller` option

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>Skpath</suitkaise-api>

# use_caller=True fills in missing path arguments with caller's file
<suitkaise-api>@autopath</suitkaise-api>(use_caller=True)
def log_location(message: str, path: <suitkaise-api>Skpath</suitkaise-api> = None):
    # if path is not provided, it becomes the file where log_location() was called
    print(f"[{<suitkaise-api>path.rp</suitkaise-api>}] {message}")

# called without path argument
log_location("Starting process")
# prints: [src/main.py] Starting process

# called with explicit path
log_location("Found file", <suitkaise-api>Skpath(</suitkaise-api>"data/input.csv"))
# prints: [data/input.csv] Found file
```

### `<suitkaise-api>autopath</suitkaise-api>` with `only` option

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>Skpath</suitkaise-api>

# only convert specific parameters (faster for large lists)
<suitkaise-api>@autopath</suitkaise-api>(only="file_path")
def process(file_path: str, tags: list[str], ids: list[str]):
    # only file_path is normalized
    # tags and ids are left unchanged (no conversion overhead)
    return file_path

# useful when you have list[str] that aren't paths
result = process(
    file_path="src/main.py",
    tags=["python", "backend"],
    ids=["abc123", "def456"]
)
```

### Storing paths as IDs in a database

Path IDs are perfect for database storage - they're URL-safe, reversible, and cross-platform.

```python
import sqlite3
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>

# SETUP

conn = sqlite3.connect(":memory:")
conn.execute("""
    CREATE TABLE files (
        id TEXT PRIMARY KEY,  -- path ID (base64url encoded)
        name TEXT,
        size INTEGER,
        processed BOOLEAN
    )
""")

# STORING PATHS

def store_file(path: <suitkaise-api>Skpath</suitkaise-api>, size: int):
    """Store a file record using its path ID."""
    conn.execute(
        "INSERT INTO files (id, name, size, processed) VALUES (?, ?, ?, ?)",
        (path.<suitkaise-api>id</suitkaise-api>, path.name, size, False)
    )

# store some files
for file_path in <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>():
    if file_path.is_file and file_path.suffix == ".py":
        store_file(file_path, file_path.stat.st_size)

conn.commit()

# RETRIEVING PATHS

def get_unprocessed_files() -> list[<suitkaise-api>Skpath</suitkaise-api>]:
    """Get all unprocessed files as <suitkaise-api>Skpath</suitkaise-api> objects."""
    cursor = conn.execute(
        "SELECT id FROM files WHERE processed = 0"
    )
    
    # reconstruct Skpath from stored ID
    return [<suitkaise-api>Skpath(</suitkaise-api>row[0]) for row in cursor.fetchall()]

# get files and process them
for file_path in get_unprocessed_files():
    print(f"Processing: {file_path.rp}")
    
    # mark as processed
    conn.execute(
        "UPDATE files SET processed = 1 WHERE id = ?",
        (file_path.<suitkaise-api>id</suitkaise-api>,)
    )

conn.commit()
```

### Caching with path IDs

```python
import json
from pathlib import Path
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

def get_cached_result(source_path: <suitkaise-api>Skpath</suitkaise-api>) -> dict | None:
    """Get cached result for a file, or None if not cached."""
    
    # use <suitkaise-api>path.id</suitkaise-api> as cache key - it's safe for filenames
    cache_file = CACHE_DIR / f"{source_path.<suitkaise-api>id</suitkaise-api>}.json"
    
    if cache_file.exists():
        # check if cache is still valid (source hasn't changed)
        cache_mtime = cache_file.stat().st_mtime
        source_mtime = source_path.stat.st_mtime
        
        if cache_mtime > source_mtime:
            # cache is newer than source - use it
            return json.loads(cache_file.read_text())
    
    return None

def save_cached_result(source_path: <suitkaise-api>Skpath</suitkaise-api>, result: dict):
    """Save result to cache."""
    cache_file = CACHE_DIR / f"{source_path.<suitkaise-api>id</suitkaise-api>}.json"
    cache_file.write_text(json.dumps(result))

def process_with_cache(path: <suitkaise-api>Skpath</suitkaise-api>) -> dict:
    """Process a file with caching."""
    
    # try cache first
    cached = get_cached_result(path)
    if cached is not None:
        print(f"Cache hit: {<suitkaise-api>path.rp</suitkaise-api>}")
        return cached
    
    # cache miss - do expensive processing
    print(f"Processing: {<suitkaise-api>path.rp</suitkaise-api>}")
    result = expensive_processing(path)
    
    # save to cache
    save_cached_result(path, result)
    return result
```

### Building a file index

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FileInfo:
    path: <suitkaise-api>Skpath</suitkaise-api>
    size: int
    modified: datetime
    
    def to_dict(self) -> dict:
        return {
            "id": self.path.<suitkaise-api>id</suitkaise-api>,
            "rp": self.<suitkaise-api>path.rp</suitkaise-api>,
            "name": self.path.name,
            "size": self.size,
            "modified": self.modified.isoformat(),
        }
    
    @classmethod
    def from_path(cls, path: <suitkaise-api>Skpath</suitkaise-api>) -> "FileInfo":
        stat = path.stat
        return cls(
            path=path,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
        )

def build_index(root: <suitkaise-api>Skpath</suitkaise-api> = None, extensions: list[str] = None) -> list[FileInfo]:
    """Build an index of files in the project."""
    
    # use provided root or auto-detect
    if root is None:
        root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
    
    index = []
    
    # get all project paths (respects .gitignore)
    for file_path in <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>(root=root):
        # skip directories
        if not file_path.is_file:
            continue
        
        # filter by extension if specified
        if extensions and file_path.suffix not in extensions:
            continue
        
        # add to index
        index.append(FileInfo.from_path(file_path))
    
    return index

# build index of Python files
py_index = build_index(extensions=[".py"])
for info in py_index[:5]:
    print(f"{info.<suitkaise-api>path.rp</suitkaise-api>}: {info.size} bytes")
```

### Config file loader with relative paths

```python
import json
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>, <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>

class ConfigLoader:
    """Load config files with paths relative to config location."""
    
    def __init__(self, config_path: <suitkaise-api>AnyPath</suitkaise-api>):
        # convert to Skpath for easy path manipulation
        self.<suitkaise-api>config_path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>config_path)
        self.config_dir = self.<suitkaise-api>config_path.parent</suitkaise-api>
        self.config = self._load()
    
    def _load(self) -> dict:
        """Load the config file."""
        with open(self.config_path, "r") as f:
            return json.load(f)
    
    def resolve_path(self, relative_path: str) -> <suitkaise-api>Skpath</suitkaise-api>:
        """Resolve a path relative to the config file location."""
        return self.config_dir / relative_path
    
    def get_data_dir(self) -> <suitkaise-api>Skpath</suitkaise-api>:
        """Get the data directory from config."""
        # config might specify: "data_dir": "./data"
        # we need to resolve it relative to config location
        data_dir = self.config.get("data_dir", "data")
        return self.resolve_path(data_dir)
    
    def get_input_files(self) -> list[<suitkaise-api>Skpath</suitkaise-api>]:
        """Get input file paths from config."""
        # config might specify: "input_files": ["input1.csv", "input2.csv"]
        input_files = self.config.get("input_files", [])
        data_dir = self.get_data_dir()
        return [data_dir / f for f in input_files]


# usage
config = ConfigLoader("configs/production.json")
print(f"Data dir: {config.get_data_dir().rp}")
for input_file in config.get_input_files():
    print(f"Input: {input_file.rp}")
```

(end of dropdown "Advanced Examples")

(no dropdown for the full script needed)
## Full Script Using `<suitkaise-api>paths</suitkaise-api>`

A complete file organizer that demonstrates cross-platform compatibility, advanced Skpath usage, `<suitkaise-api>autopath</suitkaise-api>`, and `<suitkaise-api>AnyPath</suitkaise-api>`.

```python
"""
File Organizer

Organizes files by type into categorized directories.
Demonstrates:
- Cross-platform path handling
- <suitkaise-api>autopath</suitkaise-api> decorator
- <suitkaise-api>AnyPath</suitkaise-api> type hints
- Project root detection
- Path ID encoding
- File operations
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import (
    <suitkaise-api>Skpath</suitkaise-api>,
    <suitkaise-api>AnyPath</suitkaise-api>,
    <suitkaise-api>autopath</suitkaise-api>,
    <suitkaise-api>PathDetectionError</suitkaise-api>,
    <suitkaise-api>streamline_path_quick</suitkaise-api>,
)


# CONFIGURATION

# file type categories
FILE_CATEGORIES = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"],
    "documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".rst"],
    "code": [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml"],
    "data": [".csv", ".xlsx", ".xls", ".sql", ".db"],
    "archives": [".zip", ".tar", ".gz", ".rar", ".7z"],
}


# DATA CLASSES

@dataclass
class OrganizedFile:
    """Record of a file that was organized."""
    original_path: str      # original relative path
    new_path: str           # new relative path
    category: str           # file category
    size: int               # file size in bytes
    organized_at: str       # ISO timestamp
    path_id: str            # reversible path ID


@dataclass
class OrganizeResult:
    """Result of an organize operation."""
    source_dir: str
    output_dir: str
    files_organized: int = 0
    files_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    organized_files: list[OrganizedFile] = field(default_factory=list)


# HELPER FUNCTIONS
<suitkaise-api>@autopath</suitkaise-api>()
def get_category(file_path: <suitkaise-api>Skpath</suitkaise-api>) -> str | None:
    """
    Get the category for a file based on its extension.
    Returns None if file doesn't match any category.
    """
    suffix = file_path.suffix.lower()
    
    for category, extensions in FILE_CATEGORIES.items():
        if suffix in extensions:
            return category
    
    return None


<suitkaise-api>@autopath</suitkaise-api>()
def ensure_directory(path: <suitkaise-api>Skpath</suitkaise-api>) -> <suitkaise-api>Skpath</suitkaise-api>:
    """
    Ensure a directory exists, creating it if necessary.
    Uses <suitkaise-api>autopath</suitkaise-api> so you can pass str, Path, or <suitkaise-api>Skpath</suitkaise-api>.
    """
    if not path.exists:
        path.mkdir(parents=True, exist_ok=True)
    return path


<suitkaise-api>@autopath</suitkaise-api>()
def safe_copy(source: <suitkaise-api>Skpath</suitkaise-api>, dest: <suitkaise-api>Skpath</suitkaise-api>, overwrite: bool = False) -> <suitkaise-api>Skpath</suitkaise-api> | None:
    """
    Safely copy a file, handling name conflicts.
    Returns the destination path, or None if skipped.
    """
    # check if destination already exists
    if dest.exists and not overwrite:
        # generate unique name
        stem = dest.stem
        suffix = dest.suffix
        parent = dest.parent
        counter = 1
        
        while dest.exists:
            new_name = f"{stem}_{counter}{suffix}"
            dest = parent / new_name
            counter += 1
    
    # ensure parent directory exists
    ensure_directory(dest.parent)
    
    # copy the file
    return source.copy_to(dest, overwrite=overwrite)


# MAIN ORGANIZER CLASS

class FileOrganizer:
    """
    Organizes files from a source directory into categorized folders.
    
    Cross-platform compatible:
    - Uses <suitkaise-api>Skpath</suitkaise-api> for normalized path handling
    - Works on Windows, Mac, and Linux
    - Stores path IDs for database compatibility
    """
    
    def __init__(self, output_dir: <suitkaise-api>AnyPath</suitkaise-api> = None):
        """
        Initialize the organizer.
        
        Args:
            output_dir: Where to organize files to.
                       If None, uses "organized" in project root.
        """
        # get project root for default paths
        try:
            self.project_root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
        except <suitkaise-api>PathDetectionError</suitkaise-api>:
            # no project root found - use current directory
            self.project_root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_cwd</suitkaise-api>()
        
        # set output directory
        if output_dir is None:
            self.output_dir = self.project_root / "organized"
        else:
            self.<suitkaise-api>output_dir</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>output_dir)
        
        # ensure output directory exists
        ensure_directory(self.output_dir)
        
        # manifest file to track organized files
        self.manifest_path = self.output_dir / "manifest.json"
        self.manifest: list[OrganizedFile] = []
        
        # load existing manifest if present
        self._load_manifest()
    
    def _load_manifest(self):
        """Load the manifest file if it exists."""
        if self.manifest_path.exists:
            with open(self.manifest_path, "r") as f:
                data = json.load(f)
                self.manifest = [
                    OrganizedFile(**item) for item in data
                ]
    
    def _save_manifest(self):
        """Save the manifest file."""
        with open(self.manifest_path, "w") as f:
            json.dump(
                [vars(item) for item in self.manifest],
                f,
                indent=2
            )
    
    <suitkaise-api>@autopath</suitkaise-api>()
    def organize(
        self,
        source_dir: <suitkaise-api>Skpath</suitkaise-api>,
        recursive: bool = True,
        dry_run: bool = False
    ) -> OrganizeResult:
        """
        Organize files from source directory into categories.
        
        Args:
            source_dir: Directory to organize files from.
                       Accepts str, Path, or <suitkaise-api>Skpath</suitkaise-api> (via <suitkaise-api>autopath</suitkaise-api>).
            recursive: Whether to process subdirectories.
            dry_run: If True, don't actually move files.
        
        Returns:
            OrganizeResult with summary of operations.
        """
        result = OrganizeResult(
            source_dir=source_dir.rp,
            output_dir=self.output_dir.rp,
        )
        
        # get files to organize
        if recursive:
            files = list(source_dir.rglob("*"))
        else:
            files = list(source_dir.iterdir())
        
        for file_path in files:
            # skip directories
            if not file_path.is_file:
                continue
            
            # skip hidden files
            if file_path.name.startswith("."):
                result.files_skipped += 1
                continue
            
            # get category
            category = get_category(file_path)
            if category is None:
                result.files_skipped += 1
                continue
            
            # build destination path
            # sanitize filename for cross-platform compatibility
            safe_name = <suitkaise-api>streamline_path_quick</suitkaise-api>(file_path.name)
            dest_path = self.output_dir / category / safe_name
            
            if dry_run:
                # just record what would happen
                print(f"Would organize: {file_path.rp} → {dest_path.rp}")
                result.files_organized += 1
                continue
            
            # actually copy the file
            try:
                copied = safe_copy(file_path, dest_path)
                
                if copied:
                    # record the operation
                    record = OrganizedFile(
                        original_path=file_path.rp,
                        new_path=copied.rp,
                        category=category,
                        size=file_path.stat.st_size,
                        organized_at=datetime.now().isoformat(),
                        path_id=copied.<suitkaise-api>id</suitkaise-api>,  # store path ID for database
                    )
                    self.manifest.append(record)
                    result.organized_files.append(record)
                    result.files_organized += 1
                else:
                    result.files_skipped += 1
                    
            except Exception as e:
                result.errors.append(f"{file_path.rp}: {str(e)}")
        
        # save manifest
        if not dry_run:
            self._save_manifest()
        
        return result
    
    def get_file_by_id(self, path_id: str) -> <suitkaise-api>Skpath</suitkaise-api> | None:
        """
        Get an organized file by its path ID.
        
        Path IDs are reversible - you can reconstruct the full path.
        This is useful for database storage.
        """
        # find in manifest
        for record in self.manifest:
            if record.path_id == path_id:
                return <suitkaise-api>Skpath(</suitkaise-api>path_id)
        return None
    
    def get_files_by_category(self, category: str) -> list[<suitkaise-api>Skpath</suitkaise-api>]:
        """Get all organized files in a category."""
        return [
            <suitkaise-api>Skpath(</suitkaise-api>record.path_id)
            for record in self.manifest
            if record.category == category
        ]
    
    def print_summary(self):
        """Print a summary of organized files."""
        print(f"\n{'='*50}")
        print("File Organizer Summary")
        print(f"{'='*50}")
        print(f"Output directory: {self.output_dir.rp}")
        print(f"Total files: {len(self.manifest)}")
        print()
        
        # count by category
        by_category = {}
        for record in self.manifest:
            by_category[record.category] = by_category.get(record.category, 0) + 1
        
        print("By category:")
        for category, count in sorted(by_category.items()):
            print(f"  {category}: {count} files")
        
        # show directory tree
        print()
        print("Directory structure:")
        tree = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_formatted_project_tree</suitkaise-api>(
            root=self.output_dir,
            depth=2,
            include_files=False
        )
        print(tree)


# MAIN

def main():
    """Main entry point (self-contained)."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        <suitkaise-api>tmp_root</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>tmpdir)
        source_dir = tmp_root / "downloads"
        output_dir = tmp_root / "organized"
        
        # seed some sample files
        (source_dir / "notes.txt").write_text("notes\n" * 10)
        (source_dir / "script.py").write_text("print('hello')\n")
        (source_dir / "data.json").write_text('{"ok": true}\n')
        (source_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        
        # create organizer with temp output directory
        organizer = FileOrganizer(output_dir=output_dir)
        
        print(f"Organizing files from: {source_dir.rp}")
        print(f"Output directory: {organizer.output_dir.rp}")
        print()
        
        # dry run
        print("Dry run:")
        result = organizer.organize(source_dir, dry_run=True)
        print(f"Would organize {result.files_organized} files")
        print(f"Would skip {result.files_skipped} files")
        print()
        
        # actually organize
        print("Organizing...")
        result = organizer.organize(source_dir, dry_run=False)
    
    # print results
        print(f"Organized: {result.files_organized} files")
        print(f"Skipped: {result.files_skipped} files")
        
        if result.errors:
            print(f"Errors: {len(result.errors)}")
            for error in result.errors[:5]:
                print(f"  - {error}")
        
        # show summary
        organizer.print_summary()
        
        # demonstrate path ID retrieval
        if organizer.manifest:
            print()
            print("Path ID demonstration:")
            record = organizer.manifest[0]
            print(f"  Original: {record.original_path}")
            print(f"  Path ID: {record.path_id}")
            
            # reconstruct path from ID
            <suitkaise-api>reconstructed</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>record.path_id)
            print(f"  Reconstructed: {reconstructed.rp}")


if __name__ == "__main__":
    main()
```
"
