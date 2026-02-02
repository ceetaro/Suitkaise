# How to use `paths`

`paths` provides project-aware path handling, streamlining how you handle paths and ensuring cross-platform compatibility.

Use it to work with paths relative to your project root, regardless of where your code is executed from.

- `Skpath`
Enhanced path object that detects your project root. Cross-platform compatible.

- `autopath`
Decorator for automatic path type conversion. Smack it on all of your functions that work with paths, and no more type mismatches will ever happen again.

- other super useful functions
There are a lot of other random annoying things you might come across when working with paths. Many of them are packed in here.

## Importing

```python
from suitkaise import paths
```

```python
from suitkaise.paths import Skpath, autopath, AnyPath, PathDetectionError, NotAFileError, CustomRoot, set_custom_root, get_custom_root, clear_custom_root, get_project_root, get_caller_path, get_current_dir, get_cwd, get_module_path, get_id, get_project_paths, get_project_structure, get_formatted_project_tree, is_valid_filename, streamline_path, streamline_path_quick
```

## `Skpath`

Enhanced path object with automatic project root detection.

All paths use normalized separators (`/`) for cross-platform consistency.

```python
from suitkaise.paths import Skpath

# create from caller's file path
path = Skpath()

# create from string
path = Skpath("myproject/feature/file.txt")

# create from Path object
from pathlib import Path
path = Path("myproject/feature/file.txt")
path = Skpath(path)

# create from encoded ID
path = Skpath("bXlwcm9qZWN0L2ZlYXR1cmUvZmlsZS50eHQ")
```

### Constructor

Arguments
`path`: Path to wrap.
- `str | Path | Skpath | None = None`
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
- can be used to reconstruct the path: `Skpath(encoded_id)`

`root`: Project root as Skpath object.
- `Skpath`
- read-only

`root_str`: Project root as string with normalized separators.
- `str`
- read-only

`root_path`: Project root as pathlib.Path object.
- `Path`
- read-only

```python
path = Skpath("src/main.py")

path.ap      # "/Users/me/myproject/src/main.py"
path.rp      # "src/main.py"
path.id      # "c3JjL21haW4ucHk"
path.root    # Skpath('/Users/me/myproject')
```

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
- `Skpath`

`parents`: All parent directories as Skpath objects.
- `tuple[Skpath, ...]`

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

### Path Joining

Use the `/` operator to join paths:

```python
root = Skpath()
data_file = root / "data" / "file.txt"
```

### Methods

#### `iterdir()`

Iterate over directory contents.

```python
path = Skpath("src")
for item in path.iterdir():
    print(item.name)
```

Returns
`Generator[Skpath]`: Each item in the directory.

Raises
`NotADirectoryError`: If path is not a directory.

#### `glob()`

Find paths matching a pattern.

```python
path = Skpath("src")
for py_file in path.glob("*.py"):
    print(py_file.name)
```

Arguments
`pattern`: Glob pattern (ex. `'*.txt'`).
- `str`
- required

Returns
`Generator[Skpath]`: Matching paths.

#### `rglob()`

Recursively find paths matching a pattern.

```python
root = Skpath()
for py_file in root.rglob("*.py"):
    print(py_file.rp)
```

Arguments
`pattern`: Glob pattern (ex. `'*.py'`).
- `str`
- required

Returns
`Generator[Skpath]`: Matching paths in all subdirectories.

#### `relative_to()`

Get path relative to another path.

```python
path = Skpath("src/utils/helpers.py")
rel = path.relative_to("src")
# Skpath("utils/helpers.py")
```

Arguments
`other`: Base path.
- `str | Path | Skpath`
- required

Returns
`Skpath`: Relative path.

Raises
`ValueError`: If path is not relative to other.

#### `with_name()`

Return path with changed name.

```python
path = Skpath("data/file.txt")
new_path = path.with_name("other.txt")
# Skpath("data/other.txt")
```

Arguments
`name`: New name.
- `str`
- required

Returns
`Skpath`: Path with new name.

#### `with_stem()`

Return path with changed stem (filename without suffix).

```python
path = Skpath("data/file.txt")
new_path = path.with_stem("other")
# Skpath("data/other.txt")
```

Arguments
`stem`: New stem.
- `str`
- required

Returns
`Skpath`: Path with new stem.

#### `with_suffix()`

Return path with changed suffix.

```python
path = Skpath("data/file.txt")
new_path = path.with_suffix(".json")
# Skpath("data/file.json")
```

Arguments
`suffix`: New suffix (including dot).
- `str`
- required

Returns
`Skpath`: Path with new suffix.

#### `mkdir()`

Create directory.

```python
path = Skpath("new_dir")
path.mkdir()

# create parent directories
path = Skpath("parent/child/grandchild")
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
path = Skpath("new_file.txt")
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
path = Skpath("empty_dir")
path.rmdir()
```

Raises
`OSError`: If directory is not empty.
`NotADirectoryError`: If path is not a directory.

#### `unlink()`

Remove file or symbolic link.

```python
path = Skpath("file.txt")
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
path = Skpath("./relative/path")
resolved = path.resolve()
```

Returns
`Skpath`: Absolute path with symlinks resolved.

#### `absolute()`

Return absolute version of path.

```python
path = Skpath("relative/path")
abs_path = path.absolute()
```

Returns
`Skpath`: Absolute path.

#### `copy_to()`

Copy path to destination.

```python
source = Skpath("data/file.txt")
dest = source.copy_to("backup/file.txt")

# with options
dest = source.copy_to("backup/", overwrite=True, parents=True)
```

Arguments
`destination`: Target path or directory.
- `str | Path | Skpath`
- required

`overwrite`: Remove existing destination.
- `bool = False`
- keyword only

`parents`: Create parent directories.
- `bool = True`
- keyword only

Returns
`Skpath`: Path to the copied file/directory.

Raises
`FileNotFoundError`: If source path doesn't exist.
`FileExistsError`: If destination exists and `overwrite=False`.

#### `move_to()`

Move path to destination.

```python
source = Skpath("temp/file.txt")
dest = source.move_to("data/file.txt")

# with options
dest = source.move_to("archive/", overwrite=True, parents=True)
```

Arguments
`destination`: Target path or directory.
- `str | Path | Skpath`
- required

`overwrite`: Remove existing destination.
- `bool = False`
- keyword only

`parents`: Create parent directories.
- `bool = True`
- keyword only

Returns
`Skpath`: Path to the moved file/directory.

Raises
`FileNotFoundError`: If source path doesn't exist.
`FileExistsError`: If destination exists and `overwrite=False`.

### os.fspath Compatibility

`Skpath` works with `open()`, `os.path`, and other functions that accept paths:

```python
path = Skpath("data/file.txt")

# works directly with open()
with open(path, 'r') as f:
    content = f.read()

# works with os.path functions
import os
os.path.exists(path)
```

## `autopath` Decorator

Automatically converts path parameters based on type annotations.

```python
from suitkaise.paths import autopath, AnyPath, Skpath

@autopath()
def process(path: AnyPath):
    # path is guaranteed to be Skpath
    return path.id

# works with any input type
process("src/main.py")
process(Path("src/main.py"))
process(Skpath("src/main.py"))
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
- `Skpath` → converted to Skpath
- `Path` → normalized through Skpath, converted to Path
- `str` → normalized through Skpath, returns absolute path string
- `AnyPath` (or any union containing Skpath) → converted to Skpath (richest type)
- `str | Path` (union without Skpath) → converted to Path

Supported iterables:
- `list[Skpath]`, `list[Path]`, `list[str]`
- `tuple[Skpath, ...]`, `tuple[Path, ...]`, `tuple[str, ...]`
- `set[Skpath]`, `set[Path]`, `set[str]`
- `frozenset[Skpath]`, `frozenset[Path]`, `frozenset[str]`
- `Iterable[Skpath]`, `Iterable[Path]`, `Iterable[str]` (converted to list)

```python
@autopath()
def process(
    path: Skpath,
    files: list[Path],
    names: set[str],
):
    ...
```

### `use_caller` Option

Fill missing path parameters with the caller's file path.

```python
@autopath(use_caller=True)
def log_from(path: Skpath = None):
    print(f"Logging from: {path.rp}")

# called without argument - uses caller's file
log_from()  # prints the file that called log_from()
```

### `only` Option

Restrict conversion to specific parameters (faster for large lists).

```python
@autopath(only="file_path")
def process(file_path: str, names: list[str], ids: list[str]):
    # only file_path is normalized
    # names and ids are left unchanged
    return file_path
```

### `debug` Option

Print conversion messages.

```python
@autopath(debug=True)
def process(path: Skpath):
    return path

process("src/main.py")
# @autopath: Converted path: str → Skpath
```

## Project Root

### `get_project_root()`

Get the project root directory.

```python
from suitkaise import paths

root = paths.get_project_root()
# Skpath('/Users/me/myproject')
```

Arguments
`expected_name`: If provided, detected root must have this name.
- `str | None = None`
- positional or keyword

Returns
`Skpath`: Project root directory.

Raises
`PathDetectionError`: If root cannot be detected or doesn't match expected name.

### `set_custom_root()`

Override automatic root detection.

```python
paths.set_custom_root("/my/project")
```

Arguments
`path`: Path to use as project root.
- `str | Path`
- required

Raises
`PathDetectionError`: If path doesn't exist or isn't a directory.

### `get_custom_root()`

Get the current custom root.

```python
current = paths.get_custom_root()
# "/my/project" or None
```

Returns
`str | None`: Custom root path or None.

### `clear_custom_root()`

Revert to automatic root detection.

```python
paths.clear_custom_root()
```

### `CustomRoot` Context Manager

Temporarily set a custom root:

```python
with paths.CustomRoot("/my/project"):
    root = paths.get_project_root()
    # Skpath('/my/project')

# reverts to automatic detection after the block
```

## Caller Path Functions

### `get_caller_path()`

Get the file path of the caller.

```python
caller = paths.get_caller_path()
```

Returns
`Skpath`: Caller's file path.

### `get_current_dir()`

Get the directory containing the caller's file.

```python
current_dir = paths.get_current_dir()
```

Returns
`Skpath`: Caller's directory.

### `get_cwd()`

Get the current working directory.

```python
cwd = paths.get_cwd()
```

Returns
`Skpath`: Current working directory.

### `get_module_path()`

Get the file path where an object is defined.

```python
from myapp import MyClass

path = paths.get_module_path(MyClass)
# Skpath pointing to the file where MyClass is defined
```

Arguments
`obj`: Object to inspect (module, class, function, etc.).
- `Any`
- required

Returns
`Skpath | None`: Module file path or None if not found.

## Project Path Functions

### `get_project_paths()`

Get all paths in the project.

```python
# get all paths
all_paths = paths.get_project_paths()

# use a custom root
all_paths = paths.get_project_paths(root="src")

# exclude specific paths
all_paths = paths.get_project_paths(exclude=["build", "dist"])

# get as strings for memory efficiency
all_paths = paths.get_project_paths(as_strings=True)

# ignore .*ignore files
all_paths = paths.get_project_paths(use_ignore_files=False)
```

Arguments
`root`: Custom root directory.
- `str | Path | Skpath | None = None`
- keyword only

`exclude`: Paths to exclude.
- `str | Path | Skpath | list[...] | None = None`
- keyword only

`as_strings`: Return string paths instead of Skpath objects.
- `bool = False`
- keyword only

`use_ignore_files`: Respect .gitignore, .cursorignore, etc.
- `bool = True`
- keyword only

Returns
`list[Skpath] | list[str]`: All project paths.

### `get_project_structure()`

Get a nested dict representing the project structure.

```python
structure = paths.get_project_structure()
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
- `str | Path | Skpath | None = None`
- keyword only

`exclude`: Paths to exclude.
- `str | Path | Skpath | list[...] | None = None`
- keyword only

`use_ignore_files`: Respect .gitignore, .cursorignore, etc.
- `bool = True`
- keyword only

Returns
`dict`: Nested dictionary of project structure.

### `get_formatted_project_tree()`

Get a formatted tree string for the project structure.

```python
tree = paths.get_formatted_project_tree()
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
- `str | Path | Skpath | None = None`
- keyword only

`exclude`: Paths to exclude.
- `str | Path | Skpath | list[...] | None = None`
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

## Path ID Functions

### `get_id()`

Get the reversible encoded ID for a path.

```python
path_id = paths.get_id("myproject/feature/file.txt")
# "bXlwcm9qZWN0L2ZlYXR1cmUvZmlsZS50eHQ"

# same as
path_id = Skpath("myproject/feature/file.txt").id
```

Arguments
`path`: Path to generate ID for.
- `str | Path | Skpath`
- required

Returns
`str`: Base64url encoded ID.

## Path Validation Functions

### `is_valid_filename()`

Check if a filename is valid across operating systems.

```python
from suitkaise.paths import is_valid_filename

is_valid_filename("my_file.txt")     # True
is_valid_filename("file<name>.txt")  # False (contains <, >)
is_valid_filename("CON")             # False (Windows reserved)
is_valid_filename("")                # False (empty)
```

Arguments
`filename`: Filename to validate (not a full path).
- `str`
- required

Returns
`bool`: True if valid, False otherwise.

### `streamline_path()`

Sanitize a path by replacing invalid characters.

```python
from suitkaise.paths import streamline_path

# basic cleanup
path = streamline_path("My File<1>.txt", chars_to_replace=" ")
# "My_File_1_.txt"

# lowercase and limit length
path = streamline_path("My Long Filename.txt", max_len=10, lowercase=True, chars_to_replace=" ")
# "my_long_fi.txt"

# replace invalid chars with custom character
path = streamline_path("file:name.txt", replacement_char="-")
# "file-name.txt"

# ASCII only
path = streamline_path("файл.txt", allow_unicode=False)
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

### `streamline_path_quick()`

Simple version of `streamline_path` that replaces all invalid and unicode characters.

```python
from suitkaise import paths

path = paths.streamline_path_quick("My File<1>файл.txt")
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

### `PathDetectionError`

Raised when path or project root detection fails.

```python
from suitkaise import paths
from suitkaise.paths import PathDetectionError

try:
    root = paths.get_project_root()
except PathDetectionError:
    print("Could not detect project root")
```

Common causes:
- No project root indicators found
- Custom root path doesn't exist or isn't a directory
- Expected root name doesn't match detected root

### `NotAFileError`

Raised when a file operation is attempted on a directory.

```python
from suitkaise.paths import Skpath, NotAFileError

path = Skpath("some_directory")
try:
    path.unlink()  # attempting to unlink a directory
except NotAFileError:
    print("Cannot unlink a directory")
```

## Types

### `AnyPath`

Type alias for parameters that accept any path type.

```python
from suitkaise.paths import AnyPath

def process(path: AnyPath) -> None:
    # path can be str, Path, or Skpath
    ...
```

Note: `AnyPath` does NOT include `None`. Use `AnyPath | None` when `None` is acceptable.