# How `skpath` actually works

`skpath` has no dependencies outside of the standard library.

- uses forward slashes (`/`) for all paths internally, regardless of operating system
- automatically detects project root by walking up directories looking for indicator files
- all shared state is thread-safe using `threading.RLock()`
- very easy cross-platform compatibility if used correctly

---

## `Skpath` class

The `Skpath` class is an enhanced path object that wraps Python's `pathlib.Path` while adding project-aware normalization.

Initialize with:
- `path` : a string, `Path`, `Skpath`, or `None` (uses caller's file path)

```python
from suitkaise.paths import Skpath

# from string
path = Skpath("myproject/feature/file.txt")

# from Path
path = Skpath(Path("myproject/feature/file.txt"))

# from caller's file (no argument)
path = Skpath()

# from encoded ID
path = Skpath(encoded_id_string)
```

### `Skpath.__init__()`

1. If `path` is `None`:
   - inspects the call stack using `inspect.stack()`
   - skips all frames from within the suitkaise package
   - returns the file path of the first external caller
   - raises `PathDetectionError` if no external caller found

2. If `path` is a `Skpath`:
   - copies all cached values (`_path`, `_root`, `_ap`, `_rp`, `_id`, `_hash`)
   - this is efficient because computed values are preserved

3. If `path` is a `Path`:
   - calls `.resolve()` to get the absolute path
   - stores as `_path`

4. If `path` is a `str`:
   - calls `_resolve_string_path()` which:
     - if it contains `/` or `\` - treats as path
     - if it exists on disk - treats as path
     - if it looks like base64url (no separators, valid chars) - tries to decode as ID
     - falls back to treating as path

### Core Properties

#### `Skpath.ap` (absolute path)

Returns the absolute path with normalized separators (`/`).

1. Checks if `_ap` is cached
2. If not cached:
   - converts `_path` to string
   - replaces all `\` with `/`
   - caches the result
3. Returns the cached value

Always available, even for paths outside the project root.

#### `Skpath.rp` (relative path)

Returns the path relative to the project root.

1. Checks if `_rp` is cached
2. If not cached:
   - gets the project root via `root_path` property
   - calculates `_path.relative_to(root)`
   - normalizes separators to `/`
   - if path is outside root, returns empty string `""`
   - caches the result
3. Returns the cached value

Returns `""` (empty string) if the path is outside the project root.

#### `Skpath.id` (encoded ID)

Returns a reversible base64url-encoded ID for the path.

1. Checks if `_id` is cached
2. If not cached:
   - uses `rp` if available, otherwise uses `ap`
   - encodes using `base64.urlsafe_b64encode()`
   - strips padding (`=`) for cleaner IDs
   - caches the result
3. Returns the cached value

The ID can be used to reconstruct the path later: `Skpath(encoded_id)`

#### `Skpath.root`, `Skpath.root_str`, and `Skpath.root_path`

Three ways to access the project root:

- `root` returns the project root as a `Skpath` object
- `root_str` returns the project root as a string with normalized separators (`/`)
- `root_path` returns the project root as a `Path` object

All three use the same cached `_root` value internally:

1. Checks if `_root` is cached
2. If not cached:
   - calls `detect_project_root(from_path=self._path)`
   - caches the result as a `Path`
3. Returns the cached value, converted to the appropriate type:
   - `root` wraps the `Path` in a `Skpath`
   - `root_str` normalizes separators and returns as string
   - `root_path` returns the `Path` directly

#### `Skpath.platform`

Returns the absolute path with OS-native separators.

- on Windows: uses backslashes (`\`)
- on Mac/Linux: uses forward slashes (`/`)

This is useful when you need to pass a path to OS-specific tools, display paths to users in their native format, or integrate with platform-specific APIs.

Internally calls `to_os_separators(self.ap)`.

### `__hash__` and `__eq__`

#### `Skpath.__hash__()`

Returns an integer hash for use in sets and dict keys.

1. Checks if `_hash` is cached
2. If not cached:
   - uses `rp` if available, otherwise uses `ap`
   - computes MD5 hash of the normalized path string
   - converts first 16 hex characters to integer
   - caches the result
3. Returns the cached value

MD5 is used (not the encoded ID) because:
- fixed length output
- fast computation
- returns an integer (required for `__hash__`)

#### `Skpath.__eq__(other)`

Compares two paths for equality.

1. If `other` is `None`, returns `False`
2. Converts `other` to `Skpath` if it's a string or `Path`
3. Compares `rp` first:
   - if both have non-empty `rp` and they match - return `True`
4. Falls back to comparing `ap`:
   - if `ap` values match - return `True`
5. Returns `False` otherwise

The fallback to `ap` handles paths outside the project root (where `rp` is empty).

### `__fspath__` and `__str__`

#### `Skpath.__fspath__()`

Returns the path for `os.fspath()` compatibility (used by `open()`, etc.).

1. Gets `ap` (absolute path with forward slashes)
2. If on Windows (`os.sep == "\\"`):
   - converts `/` back to `\` for OS compatibility
3. Returns the OS-native path string

#### `Skpath.__str__()`

Returns `ap` (absolute path with normalized separators).

This means `str(skpath)` always gives you a cross-platform compatible path string.

### `__truediv__` (path joining)

Supports the `/` operator for joining paths.

```python
child = path / "subdir" / "file.txt"
```

1. If `other` is a `Skpath`:
   - uses just the name if it's an absolute path
   - uses the full path otherwise
2. Creates new `Skpath` from `self._path / other_str`

---

## Root Detection

The root detection system finds your project's root directory automatically.

### Detection Priority

1. *Custom root* - if set via `set_custom_root()`, always used
2. `setup.sk` *file* - highest priority indicator (Suitkaise marker)
3. *Standard detection* - walks up looking for project files

### Indicator Files

*Definitive Indicators* (if found, this IS the root):
- `setup.sk`
- `setup.py`
- `setup.cfg`
- `pyproject.toml`

*Strong Indicators*:
- `.gitignore`
- `.git`

*Pattern Indicators* (case-insensitive):
- license files: `LICENSE`, `LICENSE.txt`, `license.md`, etc.
- README files: `README`, `README.md`, `readme.txt`, etc.
- requirements: `requirements.txt`, `requirements.pip`, etc.

### `detect_project_root()`

Arguments:
- `from_path` : Path to start searching from (default: current working directory)
- `expected_name` : If provided, detected root must have this name

Returns:
- `Path` object pointing to project root

1. Checks for custom root:
   - if set and matches `expected_name` (or no name required) - return it
   - if set but doesn't match - raise `PathDetectionError`

2. Checks cache:
   - if we've detected a root before and `from_path` is within it - return cached

3. First pass - looks for `setup.sk`:
   - walks up from `from_path` to filesystem root
   - if `setup.sk` found - return that directory immediately

4. Second pass - looks for any indicator:
   - walks up from `from_path`
   - tracks the "best" root found (outermost directory with indicators)
   - this handles nested projects correctly

5. If no root found - raise `PathDetectionError`

6. Caches the result for future calls

### Custom Root Management

#### `set_custom_root(path)`

Sets a custom project root, overriding automatic detection.

1. Converts to `Path` if string
2. Calls `.resolve()` for absolute path
3. Validates path exists and is a directory
4. Acquires lock and stores in `_custom_root`

Thread-safe operation.

#### `get_custom_root()`

Returns the current custom root as a string (or `None`).

#### `clear_custom_root()`

Clears the custom root, reverting to automatic detection.

### `CustomRoot` Context Manager

Temporarily sets a custom root for a code block.

```python
with CustomRoot("/path/to/project"):
    # all Skpath operations use this root
    path = Skpath("feature/file.txt")
# original root restored
```

1. `__enter__`:
   - saves the current `_custom_root`
   - calls `set_custom_root()` with new path

2. `__exit__`:
   - restores the previous `_custom_root`

Uses `RLock` so it can be nested from the same thread.

---

## `@autopath` Decorator

The `@autopath` decorator automatically normalizes paths and converts them to the types that a function expects.

### How It Works

At decoration time:
1. Analyzes the function's signature and type annotations
2. For each parameter, determines:
   - is it a path type? (`str`, `Path`, `Skpath`, or `AnyPath`)
   - is it an iterable of path types? (`list[AnyPath]`, etc.)
   - what's the target type to convert to?
3. If `only` is specified, filters to only those parameter names

At call time:
1. If `use_caller=True` and a path parameter is missing:
   - inspects call stack to find caller's file
   - uses that as the default value
2. For each path parameter:
   - normalizes the value through Skpath (resolves path, normalizes separators)
   - converts to the target type
3. Calls the original function with converted values

### Path Normalization

All path-like inputs flow through Skpath before conversion to the target type:

```
input -> Skpath -> best target type
```

This ensures:
- resolved absolute paths
- normalized separators (always `/`)
- cross-platform consistency

For example, `"./data\\file.txt"` becomes `"/abs/path/data/file.txt"`.

### Type Conversion Priority

When determining what type to convert to, `@autopath` picks the "best" type:

1. `Skpath` - if `Skpath` is in the annotation (including `AnyPath`)
2. `Path` - if `Path` is in the annotation (but not `Skpath`)
3. `str` - if only `str` is in the annotation

Examples:
- `path: AnyPath` -> converts to `Skpath`
- `path: Skpath` -> converts to `Skpath`
- `path: Path` -> converts to `Path`
- `path: str` -> converts to `str` (normalized absolute path)
- `path: Path | Skpath` -> converts to `Skpath`
- `path: str | Path` -> converts to `Path`

### Iterable Handling

Works with common iterables:
- `list[AnyPath]` - each element converted
- `tuple[Path, ...]` - each element converted
- `set[Skpath]` - each element converted

The container type is preserved (list -> list, tuple -> tuple, etc.).

### `only` Option

Restricts normalization to specific parameters. Use this when you have `str` or `list[str]` parameters that aren't actually file paths.

```python
@autopath(only="file_path")
def process(file_path: str, names: list[str]):
    # only file_path is normalized
    # names is passed through unchanged
```

```python
@autopath(only=["input", "output"])
def copy(input: str, output: str, tags: list[str]):
    # input and output are normalized
    # tags is left unchanged
```

### Performance Benchmarks

`@autopath` costs about 17-18 microseconds per path. 

When you have a large collection of strings that aren't paths, using `only` to only work on the correct parameters will increase performance.

### `use_caller` Option

When `use_caller=True`:

1. Gets the caller's file path by inspecting the stack
2. For parameters that accept `Skpath` or `Path` and have no value:
   - uses the caller's file path as the default

This lets you write functions like:
```python
@autopath(use_caller=True)
def log_from(path: AnyPath):
    print(f"Log from: {path.rp}")

log_from()  # uses caller's file automatically
```

### `debug` Option

When `debug=True`:
- prints a message for each conversion or normalization
- format: `"@autopath: Converted {param}: {from_type} -> {to_type}"`
- for same-type normalization: `"@autopath: Normalized {param}: '{old}' -> '{new}'"`

---

## Caller Detection

The caller detection system finds the file path of the code that called a function.

### `get_caller_path()` / `detect_caller_path()`

1. Calls `inspect.stack()` to get the call stack
2. Iterates through frames
3. Skips all frames from within the suitkaise package:
   - determines suitkaise path at import time
   - compares each frame's filename
4. Skips built-in/frozen modules (filenames starting with `<`)
5. Returns the first external frame's filename as a `Path`
6. Raises `PathDetectionError` if no external caller found

The suitkaise package path is cached at module load time for efficiency.

### `get_module_path(obj)`

Gets the file path where an object is defined.

1. If `obj` is a string:
   - looks up in `sys.modules`
   - if not found, tries `importlib.import_module()`

2. If `obj` is a module:
   - uses it directly

3. If `obj` has `__module__` attribute:
   - looks up that module name in `sys.modules`

4. Gets `__file__` from the module
5. Returns as `Path`, or `None` if not found

---

## ID Encoding/Decoding

### `encode_path_id(path_str)`

1. Normalizes separators to `/`
2. Encodes to bytes using UTF-8
3. Base64url encodes (`urlsafe_b64encode`)
4. Strips padding (`=`) for cleaner IDs
5. Returns as string

### `decode_path_id(encoded_id)`

1. Adds back padding if needed
2. Base64url decodes
3. Decodes bytes to string using UTF-8
4. Returns the path string (or `None` if decoding fails)

### `is_valid_encoded_id(s)`

Heuristic check for whether a string looks like an encoded ID:
- not empty
- no path separators (`/` or `\`)
- no spaces
- all characters are valid base64url (`A-Za-z0-9-_=`)

---

## Project Utilities

### `get_project_paths()`

Returns all paths in the project.

1. Resolves root (custom or auto-detected)
2. Collects ignore patterns from `.*ignore` files
3. Walks directory tree with `os.walk()`
4. For each file/directory:
   - checks against exclude list
   - checks against ignore patterns
   - adds to results (as `Skpath` or string)
5. Returns the list

### Ignore File Parsing

Supports gitignore-style patterns:
- comments (`#`)
- directory patterns (`dir/`)
- wildcard patterns (`*.txt`)
- path patterns (`src/*.py`)

Reads all files ending in `ignore` (`.gitignore`, `.cursorignore`, etc.).

### `get_project_structure()`

Returns a nested dict representing the project hierarchy.

1. Gets all paths using `get_project_paths()`
2. For each path:
   - splits into parts
   - builds nested dict structure
3. Returns the structure

### `get_formatted_project_tree()`

Returns a visual tree string.

1. Resolves root and ignore patterns
2. Recursively formats using tree characters:
   - `|--` for non-last items
   - `+--` for last items
   - `|   ` for continuation lines
   - `    ` for spacing after last items
3. Respects `depth` limit
4. Optionally includes/excludes files

---

## Path Validation Utilities

### `is_valid_filename(filename)`

Checks if a filename is valid across common operating systems.

1. Checks for empty or whitespace-only names
2. Checks for invalid characters: `<>:"/\|?*` and null byte
3. Checks for problematic characters: tab, newline, carriage return
4. Checks Windows reserved names (case-insensitive): CON, PRN, AUX, NUL, COM1-9, LPT1-9
5. Checks for names ending with space or period (problematic on Windows)
6. Returns `True` if valid, `False` otherwise

### `streamline_path(path, ...)`

Sanitizes a path or filename by removing/replacing invalid characters.

Arguments:
- `path`: String to sanitize
- `max_length`: Maximum length (default None = no limit)
- `replacement_char`: Character to replace invalid chars with (default "_")
- `lowercase`: Convert to lowercase (default False)
- `strip_whitespace`: Strip leading/trailing whitespace (default True)
- `allow_unicode`: Allow unicode characters (default True)

Process:
1. Strip whitespace if enabled
2. Replace invalid characters with replacement_char
3. Replace problematic characters
4. If not allow_unicode, replace non-ASCII characters
5. Apply lowercase if enabled
6. Truncate to max_length if specified
7. Clean up trailing spaces/periods
8. Return sanitized string

---

## Thread Safety

All shared state uses `threading.RLock()` (reentrant locks):

- `_root_lock` - protects custom root state
- `_cache_lock` - protects root detection cache
- `_caller_lock` - protects suitkaise path cache
- `_skpath_lock` - available for Skpath operations

*Why reentrant locks?*

A reentrant lock can be acquired multiple times by the same thread without deadlocking. This is important because:
- Skpath operations often call other Skpath operations
- the same thread might need to acquire a lock it already holds
- regular locks would deadlock in this situation

---

## Memory and Caching

### Skpath Caching

Each `Skpath` instance caches computed values:
- `_ap` - computed on first access to `ap`
- `_rp` - computed on first access to `rp`
- `_id` - computed on first access to `id`
- `_hash` - computed on first access to `__hash__`
- `_root` - computed on first access to `root_path`

This means repeated access to properties is fast (no recomputation).

### Root Detection Caching

The detected project root is cached at module level:
- `_cached_root` - the detected root
- `_cached_root_source` - the path used for detection

Cache is invalidated when:
- a new path outside the cached root is used
- `clear_root_cache()` is called

### Suitkaise Path Caching

The suitkaise package path (for caller detection) is computed once at first use and cached for the lifetime of the process.

---

## Error Handling

### `PathDetectionError`

Raised when:
- project root cannot be detected
- caller file cannot be determined
- custom root path doesn't exist or isn't a directory
- a string cannot be interpreted as a path or valid encoded ID
- expected root name doesn't match detected root

### Silent Failures

Some operations return `None` instead of raising:
- `get_module_path()` - returns `None` if module has no `__file__`
- `decode_path_id()` - returns `None` if decoding fails
- properties like `rp` - return `""` if outside project root
