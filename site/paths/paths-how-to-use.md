/*

synced from suitkaise-docs/paths/how-to-use.md

*/

rows = 2
columns = 1

# 1.1

title = "How to use `<suitkaise-api>paths</suitkaise-api>`"

# 1.2

text = "
`<suitkaise-api>paths</suitkaise-api>` provides project-aware path handling, streamlining how you handle paths and ensuring cross-platform compatibility.

Use it to work with paths relative to your project root, regardless of where your code is executed from.

- `<suitkaise-api>Skpath</suitkaise-api>`
Enhanced path object that detects your project root. Cross-platform compatible.

- `<suitkaise-api>autopath</suitkaise-api>`
Decorator for automatic path type conversion. Smack it on all of your functions that work with paths, and no more type mismatches will ever happen again.

- other super useful functions
There are a lot of other random annoying things you might come across when working with paths. Many of them are packed in here.

## Importing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
```

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>, <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>, <suitkaise-api>PathDetectionError</suitkaise-api>, <suitkaise-api>NotAFileError</suitkaise-api>, <suitkaise-api>CustomRoot</suitkaise-api>, <suitkaise-api>set_custom_root</suitkaise-api>, <suitkaise-api>get_custom_root</suitkaise-api>, <suitkaise-api>clear_custom_root</suitkaise-api>, <suitkaise-api>get_project_root</suitkaise-api>, <suitkaise-api>get_caller_path</suitkaise-api>, <suitkaise-api>get_current_dir</suitkaise-api>, <suitkaise-api>get_cwd</suitkaise-api>, <suitkaise-api>get_module_path</suitkaise-api>, <suitkaise-api>get_id</suitkaise-api>, <suitkaise-api>get_project_paths</suitkaise-api>, <suitkaise-api>get_project_structure</suitkaise-api>, <suitkaise-api>get_formatted_project_tree</suitkaise-api>, <suitkaise-api>is_valid_filename</suitkaise-api>, <suitkaise-api>streamline_path</suitkaise-api>, <suitkaise-api>streamline_path_quick</suitkaise-api>
```

## `<suitkaise-api>Skpath</suitkaise-api>`

Enhanced path object with automatic project root detection.

All paths use normalized separators (`/`) for cross-platform consistency.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

# create from caller's file path
path = <suitkaise-api>Skpath</suitkaise-api>()

# create from string
path = <suitkaise-api>Skpath</suitkaise-api>("myproject/feature/file.txt")

# create from Path object
from pathlib import Path
path = Path("myproject/feature/file.txt")
path = <suitkaise-api>Skpath</suitkaise-api>(path)

# create from encoded ID
path = <suitkaise-api>Skpath</suitkaise-api>("bXlwcm9qZWN0L2ZlYXR1cmUvZmlsZS50eHQ")
```

### Constructor

Arguments
`path`: Path to wrap.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None`
- If `None`, uses the caller's file path

### Core Properties

`ap`: Absolute path with normalized separators (`/`).
- `str`
- read-only
- always available

`rp`: Relative path to project root.
- `str`
- read-only
- returns empty string if path is outside project root

`id`: Reversible base64url encoded ID.
- `str`
- read-only
- can be used to reconstruct the path: `<suitkaise-api>Skpath</suitkaise-api>(encoded_id)`

`root`: Project root as Skpath object.
- `<suitkaise-api>Skpath</suitkaise-api>`
- read-only

`root_str`: Project root as string with normalized separators.
- `str`
- read-only

`root_path`: Project root as pathlib.Path object.
- `Path`
- read-only

```python
path = <suitkaise-api>Skpath</suitkaise-api>("src/main.py")

path.ap      # "/Users/me/myproject/src/main.py"
path.rp      # "src/main.py"
path.<suitkaise-api>id</suitkaise-api>      # "c3JjL21haW4ucHk"
path.<suitkaise-api>root</suitkaise-api>    # <suitkaise-api>Skpath</suitkaise-api>('/Users/me/myproject')
```

(start of dropdown "Properties")
### Properties

`name`: Final component (filename with extension).
- `str`

`stem`: Final component without suffix.
- `str`

`suffix`: File extension.
- `str`

`suffixes`: All file extensions.
- `list[str]`

`parent`: Parent directory as Skpath.
- `<suitkaise-api>Skpath</suitkaise-api>`

`parents`: All parent directories as Skpath objects.
- `tuple[<suitkaise-api>Skpath</suitkaise-api>, ...]`

`parts`: Path components as tuple.
- `tuple[str, ...]`

`exists`: Whether the path exists.
- `bool`

`is_file`: Whether the path is a file.
- `bool`

`is_dir`: Whether the path is a directory.
- `bool`

`is_symlink`: Whether the path is a symbolic link.
- `bool`

`stat`: Stat info for the path.
- `os.stat_result`

`lstat`: Stat info for the path (don't follow symlinks).
- `os.stat_result`

`is_empty`: Whether the path is an empty directory.
- `bool`
- raises `NotADirectoryError` if path is not a directory

`as_dict`: Dictionary representation of the path.
- `dict[str, Any]`
- contains `ap`, `rp`, `root`, `name`, `exists`

`platform`: Absolute path with OS-native separators.
- `str`
- backslashes on Windows, forward slashes elsewhere

(end of dropdown "Properties")

### Path Joining

Use the `/` operator to join paths:

```python
root = <suitkaise-api>Skpath</suitkaise-api>()
data_file = root / "data" / "file.txt"
```

(start of dropdown "Methods")
### Methods

#### `iterdir()`

Iterate over directory contents.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("src")
for item in path.iterdir():
    print(item.name)
```

Returns
`Generator[<suitkaise-api>Skpath</suitkaise-api>]`: Each item in the directory.

Raises
`NotADirectoryError`: If path is not a directory.

#### `glob()`

Find paths matching a pattern.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("src")
for py_file in path.glob("*.py"):
    print(py_file.name)
```

Arguments
`pattern`: Glob pattern (ex. `'*.txt'`).
- `str`
- required

Returns
`Generator[<suitkaise-api>Skpath</suitkaise-api>]`: Matching paths.

#### `rglob()`

Recursively find paths matching a pattern.

```python
root = <suitkaise-api>Skpath</suitkaise-api>()
for py_file in <suitkaise-api>root</suitkaise-api>.rglob("*.py"):
    print(py_file.rp)
```

Arguments
`pattern`: Glob pattern (ex. `'*.py'`).
- `str`
- required

Returns
`Generator[<suitkaise-api>Skpath</suitkaise-api>]`: Matching paths in all subdirectories.

#### `relative_to()`

Get path relative to another path.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("src/utils/helpers.py")
rel = path.relative_to("src")
# <suitkaise-api>Skpath</suitkaise-api>("utils/helpers.py")
```

Arguments
`other`: Base path.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api>`
- required

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Relative path.

Raises
`ValueError`: If path is not relative to other.

#### `with_name()`

Return path with changed name.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("data/file.txt")
new_path = path.with_name("other.txt")
# <suitkaise-api>Skpath</suitkaise-api>("data/other.txt")
```

Arguments
`name`: New name.
- `str`
- required

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Path with new name.

#### `read_text()` / `write_text()`

Read and write text files (mirrors `pathlib.Path`).

```python
path = <suitkaise-api>Skpath</suitkaise-api>("data/config.json")
path.write_text("{}")
contents = path.read_text()
```

Arguments
`write_text(data, encoding=None, errors=None, newline=None)`

Returns
`int`: Number of characters written.

#### `read_bytes()` / `write_bytes()`

Read and write binary files (mirrors `pathlib.Path`).

```python
path = <suitkaise-api>Skpath</suitkaise-api>("data/blob.bin")
path.write_bytes(b"\x00\x01")
data = path.read_bytes()
```

Returns
`bytes`: File contents.

#### `with_stem()`

Return path with changed stem (filename without suffix).

```python
path = <suitkaise-api>Skpath</suitkaise-api>("data/file.txt")
new_path = path.with_stem("other")
# <suitkaise-api>Skpath</suitkaise-api>("data/other.txt")
```

Arguments
`stem`: New stem.
- `str`
- required

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Path with new stem.

#### `with_suffix()`

Return path with changed suffix.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("data/file.txt")
new_path = path.with_suffix(".json")
# <suitkaise-api>Skpath</suitkaise-api>("data/file.json")
```

Arguments
`suffix`: New suffix (including dot).
- `str`
- required

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Path with new suffix.

#### `mkdir()`

Create directory.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("new_dir")
path.mkdir()

# create parent directories
path = <suitkaise-api>Skpath</suitkaise-api>("parent/child/grandchild")
path.mkdir(parents=True)
```

Arguments
`mode`: Directory permissions.
- `int = 0o777`
- keyword only

`parents`: Create parent directories.
- `bool = False`
- keyword only

`exist_ok`: Don't raise if directory exists.
- `bool = False`
- keyword only

Raises
`FileExistsError`: If directory exists and `exist_ok=False`.
`FileNotFoundError`: If parent doesn't exist and `parents=False`.

#### `touch()`

Create file or update timestamp.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("new_file.txt")
path.touch()
```

Arguments
`mode`: File permissions.
- `int = 0o666`
- keyword only

`exist_ok`: Don't raise if file exists.
- `bool = True`
- keyword only

#### `rmdir()`

Remove empty directory.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("empty_dir")
path.rmdir()
```

Raises
`OSError`: If directory is not empty.
`NotADirectoryError`: If path is not a directory.

#### `unlink()`

Remove file or symbolic link.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("file.txt")
path.unlink()

# don't raise if file doesn't exist
path.unlink(missing_ok=True)
```

Arguments
`missing_ok`: Don't raise if file doesn't exist.
- `bool = False`
- keyword only

Raises
`FileNotFoundError`: If file doesn't exist and `missing_ok=False`.
`IsADirectoryError`: If path is a directory.

#### `resolve()`

Return absolute path, resolving symlinks.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("./relative/path")
resolved = path.resolve()
```

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Absolute path with symlinks resolved.

#### `absolute()`

Return absolute version of path.

```python
path = <suitkaise-api>Skpath</suitkaise-api>("relative/path")
abs_path = path.absolute()
```

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Absolute path.

#### `copy_to()`

Copy path to destination.

```python
source = <suitkaise-api>Skpath</suitkaise-api>("data/file.txt")
dest = source.copy_to("backup/file.txt")

# with options
dest = source.copy_to("backup/", overwrite=True, parents=True)
```

Arguments
`destination`: Target path or directory.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api>`
- required

`overwrite`: Remove existing destination.
- `bool = False`
- keyword only

`parents`: Create parent directories.
- `bool = True`
- keyword only

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Path to the copied file/directory.

Raises
`FileNotFoundError`: If source path doesn't exist.
`FileExistsError`: If destination exists and `overwrite=False`.

#### `move_to()`

Move path to destination.

```python
source = <suitkaise-api>Skpath</suitkaise-api>("temp/file.txt")
dest = source.move_to("data/file.txt")

# with options
dest = source.move_to("archive/", overwrite=True, parents=True)
```

Arguments
`destination`: Target path or directory.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api>`
- required

`overwrite`: Remove existing destination.
- `bool = False`
- keyword only

`parents`: Create parent directories.
- `bool = True`
- keyword only

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Path to the moved file/directory.

Raises
`FileNotFoundError`: If source path doesn't exist.
`FileExistsError`: If destination exists and `overwrite=False`.

(end of dropdown "Methods")


### os.fspath Compatibility

`<suitkaise-api>Skpath</suitkaise-api>` works with `open()`, `os.path`, and other functions that accept paths:

```python
path = <suitkaise-api>Skpath</suitkaise-api>("data/file.txt")

# works directly with open()
with open(path, 'r') as f:
    content = f.read()

# works with os.path functions
import os
os.path.exists(path)
```

## `<suitkaise-api>autopath</suitkaise-api>` Decorator

Automatically converts path parameters based on type annotations.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>, <suitkaise-api>Skpath</suitkaise-api>

@<suitkaise-api>autopath</suitkaise-api>()
def process(path: <suitkaise-api>AnyPath</suitkaise-api>):
    # path is guaranteed to be <suitkaise-api>Skpath</suitkaise-api>
    return path.<suitkaise-api>id</suitkaise-api>

# works with any input type
process("src/main.py")
process(Path("src/main.py"))
process(<suitkaise-api>Skpath</suitkaise-api>("src/main.py"))
```

Arguments
`use_caller`: Use caller's file path for missing parameters.
- `bool = False`
- keyword only

`debug`: Print conversion messages.
- `bool = False`
- keyword only

`only`: Only convert specific parameters.
- `str | list[str] | None = None`
- keyword only

### Type Annotations

The decorator converts parameters based on their type annotations.

Supported types:
- `<suitkaise-api>Skpath</suitkaise-api>` → converted to Skpath
- `Path` → normalized through Skpath, converted to Path
- `str` → normalized through Skpath, returns absolute path string
- `<suitkaise-api>AnyPath</suitkaise-api>` (or any union containing Skpath) → converted to Skpath (richest type)
- `str | Path` (union without Skpath) → converted to Path

Supported iterables:
- `list[<suitkaise-api>Skpath</suitkaise-api>]`, `list[Path]`, `list[str]`
- `tuple[<suitkaise-api>Skpath</suitkaise-api>, ...]`, `tuple[Path, ...]`, `tuple[str, ...]`
- `set[<suitkaise-api>Skpath</suitkaise-api>]`, `set[Path]`, `set[str]`
- `frozenset[<suitkaise-api>Skpath</suitkaise-api>]`, `frozenset[Path]`, `frozenset[str]`
- `Iterable[<suitkaise-api>Skpath</suitkaise-api>]`, `Iterable[Path]`, `Iterable[str]` (converted to list)

```python
@<suitkaise-api>autopath</suitkaise-api>()
def process(
    path: <suitkaise-api>Skpath</suitkaise-api>,
    files: list[Path],
    names: set[str],
):
    ...
```

### `use_caller` Option

Fill missing path parameters with the caller's file path.

```python
@<suitkaise-api>autopath</suitkaise-api>(use_caller=True)
def log_from(path: <suitkaise-api>Skpath</suitkaise-api> = None):
    print(f"Logging from: {path.rp}")

# called without argument - uses caller's file
log_from()  # prints the file that called log_from()
```

### `only` Option

Restrict conversion to specific parameters (faster for large lists).

```python
@<suitkaise-api>autopath</suitkaise-api>(only="file_path")
def process(file_path: str, names: list[str], ids: list[str]):
    # only file_path is normalized
    # names and ids are left unchanged
    return file_path
```

### `debug` Option

Print conversion messages.

```python
@<suitkaise-api>autopath</suitkaise-api>(debug=True)
def process(path: <suitkaise-api>Skpath</suitkaise-api>):
    return path

process("src/main.py")
# @<suitkaise-api>autopath</suitkaise-api>: Converted path: str → <suitkaise-api>Skpath</suitkaise-api>
```

(start of dropdown "Project Root")
## Project Root

### `<suitkaise-api>get_project_root</suitkaise-api>()`

Get the project root directory.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>

root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
# <suitkaise-api>Skpath</suitkaise-api>('/Users/me/myproject')
```

Arguments
`expected_name`: If provided, detected root must have this name.
- `str | None = None`
- positional or keyword

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Project root directory.

Raises
`<suitkaise-api>PathDetectionError</suitkaise-api>`: If root cannot be detected or doesn't match expected name.

### `<suitkaise-api>set_custom_root</suitkaise-api>()`

Override automatic root detection.

```python
<suitkaise-api>paths</suitkaise-api>.<suitkaise-api>set_custom_root</suitkaise-api>("/my/project")
```

Arguments
`path`: Path to use as project root.
- `str | Path`
- required

Raises
`<suitkaise-api>PathDetectionError</suitkaise-api>`: If path doesn't exist or isn't a directory.

### `<suitkaise-api>get_custom_root</suitkaise-api>()`

Get the current custom root.

```python
current = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_custom_root</suitkaise-api>()
# "/my/project" or None
```

Returns
`str | None`: Custom root path or None.

### `<suitkaise-api>clear_custom_root</suitkaise-api>()`

Revert to automatic root detection.

```python
<suitkaise-api>paths</suitkaise-api>.<suitkaise-api>clear_custom_root</suitkaise-api>()
```

### `<suitkaise-api>CustomRoot</suitkaise-api>` Context Manager

Temporarily set a custom root:

```python
with <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>CustomRoot</suitkaise-api>("/my/project"):
    root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
    # <suitkaise-api>Skpath</suitkaise-api>('/my/project')

# reverts to automatic detection after the block
```

(end of dropdown "Project Root")

(start of dropdown "Caller Path Functions")
## Caller Path Functions

### `<suitkaise-api>get_caller_path</suitkaise-api>()`

Get the file path of the caller.

```python
caller = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_caller_path</suitkaise-api>()
```

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Caller's file path.

### `<suitkaise-api>get_current_dir</suitkaise-api>()`

Get the directory containing the caller's file.

```python
current_dir = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_current_dir</suitkaise-api>()
```

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Caller's directory.

### `<suitkaise-api>get_cwd</suitkaise-api>()`

Get the current working directory.

```python
cwd = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_cwd</suitkaise-api>()
```

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Current working directory.

### `<suitkaise-api>get_module_path</suitkaise-api>()`

Get the file path where an object is defined.

```python
from myapp import MyClass

path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_module_path</suitkaise-api>(MyClass)
# <suitkaise-api>Skpath</suitkaise-api> pointing to the file where MyClass is defined
```

Arguments
`obj`: Object to inspect (module, class, function, etc.).
- `Any`
- required

Returns
`<suitkaise-api>Skpath</suitkaise-api> | None`: Module file path or None if not found.

(end of dropdown "Caller Path Functions")

(start of dropdown "Project Path Functions")
## Project Path Functions

### `<suitkaise-api>get_project_paths</suitkaise-api>()`

Get all paths in the project.

```python
# get all <suitkaise-api>paths</suitkaise-api>
all_paths = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>()

# use a custom root
all_paths = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>(root="src")

# exclude specific <suitkaise-api>paths</suitkaise-api>
all_paths = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>(exclude=["build", "dist"])

# get as strings for memory efficiency
all_paths = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>(as_strings=True)

# ignore .*ignore files
all_paths = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>(use_ignore_files=False)
```

Arguments
`root`: Custom root directory.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None`
- keyword only

`exclude`: Paths to exclude.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | list[...] | None = None`
- keyword only

`as_strings`: Return string paths instead of Skpath objects.
- `bool = False`
- keyword only

`use_ignore_files`: Respect .gitignore, .cursorignore, etc.
- `bool = True`
- keyword only

Returns
`list[<suitkaise-api>Skpath</suitkaise-api>] | list[str]`: All project paths.

### `<suitkaise-api>get_project_structure</suitkaise-api>()`

Get a nested dict representing the project structure.

```python
structure = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_structure</suitkaise-api>()
# {
#     "myproject": {
#         "src": {
#             "main.py": {},
#             "utils.py": {}
#         },
#         "tests": {...}
#     }
# }
```

Arguments
`root`: Custom root directory.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None`
- keyword only

`exclude`: Paths to exclude.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | list[...] | None = None`
- keyword only

`use_ignore_files`: Respect .gitignore, .cursorignore, etc.
- `bool = True`
- keyword only

Returns
`dict`: Nested dictionary of project structure.

### `<suitkaise-api>get_formatted_project_tree</suitkaise-api>()`

Get a formatted tree string for the project structure.

```python
tree = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_formatted_project_tree</suitkaise-api>()
print(tree)
# myproject/
# ├── src/
# │   ├── main.py
# │   └── utils/
# └── tests/
#     └── test_main.py
```

Arguments
`root`: Custom root directory.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None`
- keyword only

`exclude`: Paths to exclude.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | list[...] | None = None`
- keyword only

`use_ignore_files`: Respect .gitignore, .cursorignore, etc.
- `bool = True`
- keyword only

`depth`: Maximum depth to display (None = no limit).
- `int | None = None`
- keyword only

`include_files`: Include files in the tree.
- `bool = True`
- keyword only

Returns
`str`: Formatted tree string.

(end of dropdown "Project Path Functions")

(start of dropdown "Path ID Functions")
## Path ID Functions

### `<suitkaise-api>get_id</suitkaise-api>()`

Get the reversible encoded ID for a path.

```python
path_id = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_id</suitkaise-api>("myproject/feature/file.txt")
# "bXlwcm9qZWN0L2ZlYXR1cmUvZmlsZS50eHQ"

# same as
path_id = <suitkaise-api>Skpath</suitkaise-api>("myproject/feature/file.txt").<suitkaise-api>id</suitkaise-api>
```

Arguments
`path`: Path to generate ID for.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api>`
- required

Returns
`str`: Base64url encoded ID.

(end of dropdown "Path ID Functions")

(start of dropdown "Path Validation Functions")
## Path Validation Functions

### `<suitkaise-api>is_valid_filename</suitkaise-api>()`

Check if a filename is valid across operating systems.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>is_valid_filename</suitkaise-api>

<suitkaise-api>is_valid_filename</suitkaise-api>("my_file.txt")     # True
<suitkaise-api>is_valid_filename</suitkaise-api>("file<name>.txt")  # False (contains <, >)
<suitkaise-api>is_valid_filename</suitkaise-api>("CON")             # False (Windows reserved)
<suitkaise-api>is_valid_filename</suitkaise-api>("")                # False (empty)
```

Arguments
`filename`: Filename to validate (not a full path).
- `str`
- required

Returns
`bool`: True if valid, False otherwise.

### `<suitkaise-api>streamline_path</suitkaise-api>()`

Sanitize a path by replacing invalid characters.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>streamline_path</suitkaise-api>

# basic cleanup
path = <suitkaise-api>streamline_path</suitkaise-api>("My File<1>.txt", chars_to_replace=" ")
# "My_File_1_.txt"

# lowercase and limit length
path = <suitkaise-api>streamline_path</suitkaise-api>("My Long Filename.txt", max_len=10, lowercase=True, chars_to_replace=" ")
# "my_long_fi.txt"

# replace invalid chars with custom character
path = <suitkaise-api>streamline_path</suitkaise-api>("file:name.txt", replacement_char="-")
# "file-name.txt"

# ASCII only
path = <suitkaise-api>streamline_path</suitkaise-api>("файл.txt", allow_unicode=False)
# "____.txt"
```

Arguments
`path`: Path or filename to sanitize.
- `str`
- required

`max_len`: Maximum length (suffix preserved, not counted).
- `int | None = None`
- keyword only

`replacement_char`: Character to replace invalid chars with.
- `str = "_"`
- keyword only

`lowercase`: Convert to lowercase.
- `bool = False`
- keyword only

`strip_whitespace`: Strip leading/trailing whitespace.
- `bool = True`
- keyword only

`chars_to_replace`: Extra characters to replace.
- `str | list[str] | None = None`
- keyword only

`allow_unicode`: Allow unicode characters.
- `bool = True`
- keyword only

Returns
`str`: Sanitized path.

### `<suitkaise-api>streamline_path_quick</suitkaise-api>()`

Simple version of `<suitkaise-api>streamline_path</suitkaise-api>` that replaces all invalid and unicode characters.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>

path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>streamline_path_quick</suitkaise-api>("My File<1>файл.txt")
# "My_File_1_____.txt"
```

Arguments
`path`: Path or filename to sanitize.
- `str`
- required

`max_len`: Maximum length.
- `int | None = None`
- positional or keyword

`replacement_char`: Character to replace invalid chars with.
- `str = "_"`
- positional or keyword

`lowercase`: Convert to lowercase.
- `bool = False`
- positional or keyword

Returns
`str`: Sanitized path.

## Exceptions

### `<suitkaise-api>PathDetectionError</suitkaise-api>`

Raised when path or project root detection fails.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>PathDetectionError</suitkaise-api>

try:
    root = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()
except <suitkaise-api>PathDetectionError</suitkaise-api>:
    print("Could not detect project root")
```

Common causes:
- No project root indicators found
- Custom root path doesn't exist or isn't a directory
- Expected root name doesn't match detected root

### `<suitkaise-api>NotAFileError</suitkaise-api>`

Raised when a file operation is attempted on a directory.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>, <suitkaise-api>NotAFileError</suitkaise-api>

path = <suitkaise-api>Skpath</suitkaise-api>("some_directory")
try:
    path.unlink()  # attempting to unlink a directory
except <suitkaise-api>NotAFileError</suitkaise-api>:
    print("Cannot unlink a directory")
```

## Types

### `<suitkaise-api>AnyPath</suitkaise-api>`

Type alias for parameters that accept any path type.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>AnyPath</suitkaise-api>

def process(path: <suitkaise-api>AnyPath</suitkaise-api>) -> None:
    # path can be str, Path, or <suitkaise-api>Skpath</suitkaise-api>
    ...
```

Note: `<suitkaise-api>AnyPath</suitkaise-api>` does NOT include `None`. Use `<suitkaise-api>AnyPath</suitkaise-api> | None` when `None` is acceptable.
"
