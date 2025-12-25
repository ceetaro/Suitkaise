/*

how the skpath module actually works.

*/

rows = 2
columns = 1

# 1.1

title = "How `skpath` actually works"

text = "

`skpath` has no dependencies outside of the standard library.

- uses forward slashes (`/`) for all paths internally, regardless of operating system
- automatically detects project root by walking up directories looking for indicator files
- all shared state is thread-safe using `threading.RLock()`

---

## `SKPath` class

The `SKPath` class is an enhanced path object that wraps Python's `pathlib.Path` while adding project-aware normalization.

Initialize with:
- `path`: a string, `Path`, `SKPath`, or `None` (uses caller's file path)

```python
from suitkaise.skpath import SKPath

# From string
path = SKPath("myproject/feature/file.txt")

# From Path
path = SKPath(Path("myproject/feature/file.txt"))

# From caller's file (no argument)
path = SKPath()

# From encoded ID
path = SKPath(encoded_id_string)
```

### `SKPath.__init__()`

1. If `path` is `None`:
   - Inspects the call stack using `inspect.stack()`
   - Skips all frames from within the suitkaise package
   - Returns the file path of the first external caller
   - Raises `PathDetectionError` if no external caller found

2. If `path` is an `SKPath`:
   - Copies all cached values (`_path`, `_root`, `_ap`, `_np`, `_id`, `_hash`)
   - This is efficient because computed values are preserved

3. If `path` is a `Path`:
   - Calls `.resolve()` to get the absolute path
   - Stores as `_path`

4. If `path` is a `str`:
   - Calls `_resolve_string_path()` which:
     - If it contains `/` or `\` → treats as path
     - If it exists on disk → treats as path
     - If it looks like base64url (no separators, valid chars) → tries to decode as ID
     - Falls back to treating as path

### Core Properties

#### `SKPath.ap` (absolute path)

Returns the absolute path with normalized separators (`/`).

1. Checks if `_ap` is cached
2. If not cached:
   - Converts `_path` to string
   - Replaces all `\` with `/`
   - Caches the result
3. Returns the cached value

Always available, even for paths outside the project root.

#### `SKPath.np` (normalized path)

Returns the path relative to the project root.

1. Checks if `_np` is cached
2. If not cached:
   - Gets the project root via `root_path` property
   - Calculates `_path.relative_to(root)`
   - Normalizes separators to `/`
   - If path is outside root, returns empty string `""`
   - Caches the result
3. Returns the cached value

Returns `""` (empty string) if the path is outside the project root.

#### `SKPath.id` (encoded ID)

Returns a reversible base64url-encoded ID for the path.

1. Checks if `_id` is cached
2. If not cached:
   - Uses `np` if available, otherwise uses `ap`
   - Encodes using `base64.urlsafe_b64encode()`
   - Strips padding (`=`) for cleaner IDs
   - Caches the result
3. Returns the cached value

The ID can be used to reconstruct the path later: `SKPath(encoded_id)`

#### `SKPath.root` and `SKPath.root_path`

`root` returns the project root as a string with normalized separators.
`root_path` returns the project root as a `Path` object.

1. Checks if `_root` is cached
2. If not cached:
   - Calls `detect_project_root(from_path=self._path)`
   - Caches the result
3. Returns the cached value

### `__hash__` and `__eq__`

#### `SKPath.__hash__()`

Returns an integer hash for use in sets and dict keys.

1. Checks if `_hash` is cached
2. If not cached:
   - Uses `np` if available, otherwise uses `ap`
   - Computes MD5 hash of the normalized path string
   - Converts first 16 hex characters to integer
   - Caches the result
3. Returns the cached value

MD5 is used (not the encoded ID) because:
- Fixed length output
- Fast computation
- Returns an integer (required for `__hash__`)

#### `SKPath.__eq__(other)`

Compares two paths for equality.

1. If `other` is `None`, returns `False`
2. Converts `other` to `SKPath` if it's a string or `Path`
3. Compares `np` first:
   - If both have non-empty `np` and they match → return `True`
4. Falls back to comparing `ap`:
   - If `ap` values match → return `True`
5. Returns `False` otherwise

The fallback to `ap` handles paths outside the project root (where `np` is empty).

### `__fspath__` and `__str__`

#### `SKPath.__fspath__()`

Returns the path for `os.fspath()` compatibility (used by `open()`, etc.).

1. Gets `ap` (absolute path with forward slashes)
2. If on Windows (`os.sep == "\\"`):
   - Converts `/` back to `\` for OS compatibility
3. Returns the OS-native path string

#### `SKPath.__str__()`

Returns `ap` (absolute path with normalized separators).

This means `str(skpath)` always gives you a cross-platform compatible path string.

### `__truediv__` (path joining)

Supports the `/` operator for joining paths.

```python
child = path / "subdir" / "file.txt"
```

1. If `other` is an `SKPath`:
   - Uses just the name if it's an absolute path
   - Uses the full path otherwise
2. Creates new `SKPath` from `self._path / other_str`

---

## Root Detection

The root detection system finds your project's root directory automatically.

### Detection Priority

1. **Custom root** — if set via `set_custom_root()`, always used
2. **setup.sk file** — highest priority indicator (Suitkaise marker)
3. **Standard indicators** — walks up looking for project files

### Indicator Files

**Definitive Indicators** (if found, this IS the root):
- `setup.sk`
- `setup.py`
- `setup.cfg`
- `pyproject.toml`

**Strong Indicators**:
- `.gitignore`
- `.git`

**Pattern Indicators** (case-insensitive):
- License files: `LICENSE`, `LICENSE.txt`, `license.md`, etc.
- README files: `README`, `README.md`, `readme.txt`, etc.
- Requirements: `requirements.txt`, `requirements.pip`, etc.

### `detect_project_root()`

Arguments:
- `from_path`: Path to start searching from (default: current working directory)
- `expected_name`: If provided, detected root must have this name

Returns:
- `Path` object pointing to project root

1. Checks for custom root:
   - If set and matches `expected_name` (or no name required) → return it
   - If set but doesn't match → raise `PathDetectionError`

2. Checks cache:
   - If we've detected a root before and `from_path` is within it → return cached

3. First pass — looks for `setup.sk`:
   - Walks up from `from_path` to filesystem root
   - If `setup.sk` found → return that directory immediately

4. Second pass — looks for any indicator:
   - Walks up from `from_path`
   - Tracks the "best" root found (outermost directory with indicators)
   - This handles nested projects correctly

5. If no root found → raise `PathDetectionError`

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
    # All SKPath operations use this root
    path = SKPath("feature/file.txt")
# Original root restored
```

1. `__enter__`:
   - Saves the current `_custom_root`
   - Calls `set_custom_root()` with new path

2. `__exit__`:
   - Restores the previous `_custom_root`

Uses `RLock` so it can be nested from the same thread.

---

## `@autopath` Decorator

The `@autopath` decorator automatically converts path parameters based on their type annotations.

### How It Works

At decoration time:
1. Analyzes the function's signature and type annotations
2. For each parameter, determines:
   - Is it a path type? (`str`, `Path`, `SKPath`, or `AnyPath`)
   - Is it an iterable of path types? (`list[AnyPath]`, etc.)
   - What's the target type to convert to?

At call time:
1. If `use_caller=True` and a path parameter is missing:
   - Inspects call stack to find caller's file
   - Uses that as the default value
2. For each path parameter:
   - Converts the value to match the annotation type
3. Calls the original function with converted values

### Type Conversion Priority

When determining what type to convert to, `@autopath` picks the "richest" type:

1. **SKPath** — if `SKPath` is in the annotation (including `AnyPath`)
2. **Path** — if `Path` is in the annotation (but not `SKPath`)
3. **str** — if only `str` is in the annotation

Examples:
- `path: AnyPath` → converts to `SKPath`
- `path: SKPath` → converts to `SKPath`
- `path: Path` → converts to `Path`
- `path: str` → converts to `str`
- `path: Path | SKPath` → converts to `SKPath`
- `path: str | Path` → converts to `Path`

### Iterable Handling

Works with common iterables:
- `list[AnyPath]` → each element converted
- `tuple[Path, ...]` → each element converted
- `set[SKPath]` → each element converted

The container type is preserved (list → list, tuple → tuple, etc.).

### `use_caller` Option

When `use_caller=True`:
1. Gets the caller's file path by inspecting the stack
2. For parameters that accept `SKPath` or `Path` and have no value:
   - Uses the caller's file path as the default

This lets you write functions like:
```python
@autopath(use_caller=True)
def log_from(path: AnyPath):
    print(f"Log from: {path.np}")

log_from()  # Uses caller's file automatically
```

### `debug` Option

When `debug=True`:
- Prints a message for each conversion
- Format: `"@autopath: Converted {param}: {from_type} → {to_type}"`

---

## Caller Detection

The caller detection system finds the file path of the code that called a function.

### `get_caller_path()` / `detect_caller_path()`

1. Calls `inspect.stack()` to get the call stack
2. Iterates through frames
3. Skips all frames from within the suitkaise package:
   - Determines suitkaise path at import time
   - Compares each frame's filename
4. Skips built-in/frozen modules (filenames starting with `<`)
5. Returns the first external frame's filename as a `Path`
6. Raises `PathDetectionError` if no external caller found

The suitkaise package path is cached at module load time for efficiency.

### `get_module_path(obj)`

Gets the file path where an object is defined.

1. If `obj` is a string:
   - Looks up in `sys.modules`
   - If not found, tries `importlib.import_module()`

2. If `obj` is a module:
   - Uses it directly

3. If `obj` has `__module__` attribute:
   - Looks up that module name in `sys.modules`

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
- Not empty
- No path separators (`/` or `\`)
- No spaces
- All characters are valid base64url (`A-Za-z0-9-_=`)

---

## Project Utilities

### `get_project_paths()`

Returns all paths in the project.

1. Resolves root (custom or auto-detected)
2. Collects ignore patterns from `.*ignore` files
3. Walks directory tree with `os.walk()`
4. For each file/directory:
   - Checks against exclude list
   - Checks against ignore patterns
   - Adds to results (as `SKPath` or string)
5. Returns the list

### Ignore File Parsing

Supports gitignore-style patterns:
- Comments (`#`)
- Directory patterns (`dir/`)
- Wildcard patterns (`*.txt`)
- Path patterns (`src/*.py`)

Reads all files ending in `ignore` (`.gitignore`, `.cursorignore`, etc.).

### `get_project_structure()`

Returns a nested dict representing the project hierarchy.

1. Gets all paths using `get_project_paths()`
2. For each path:
   - Splits into parts
   - Builds nested dict structure
3. Returns the structure

### `get_formatted_project_tree()`

Returns a visual tree string.

1. Resolves root and ignore patterns
2. Recursively formats using tree characters:
   - `├──` for non-last items
   - `└──` for last items
   - `│   ` for continuation lines
   - `    ` for spacing after last items
3. Respects `depth` limit
4. Optionally includes/excludes files

---

## Thread Safety

All shared state uses `threading.RLock()` (reentrant locks):

- `_root_lock` — protects custom root state
- `_cache_lock` — protects root detection cache
- `_caller_lock` — protects suitkaise path cache
- `_autopath_lock` — available for future use
- `_project_lock` — available for future use

(this is a dropdown)
### What is a reentrant lock?

A reentrant lock can be acquired multiple times by the same thread without deadlocking. This is important because:
- SKPath operations often call other SKPath operations
- The same thread might need to acquire a lock it already holds
- Regular locks would deadlock in this situation

(end of dropdown)

---

## Memory and Caching

### SKPath Caching

Each `SKPath` instance caches computed values:
- `_ap` — computed on first access to `ap`
- `_np` — computed on first access to `np`
- `_id` — computed on first access to `id`
- `_hash` — computed on first access to `__hash__`
- `_root` — computed on first access to `root_path`

This means repeated access to properties is fast (no recomputation).

### Root Detection Caching

The detected project root is cached at module level:
- `_cached_root` — the detected root
- `_cached_root_source` — the path used for detection

Cache is invalidated when:
- A new path outside the cached root is used
- `clear_root_cache()` is called

### Suitkaise Path Caching

The suitkaise package path (for caller detection) is computed once at first use and cached for the lifetime of the process.

---

## Error Handling

### `PathDetectionError`

Raised when:
- Project root cannot be detected
- Caller file cannot be determined
- Custom root path doesn't exist or isn't a directory
- A string cannot be interpreted as a path or valid encoded ID
- Expected root name doesn't match detected root

### Silent Failures

Some operations return `None` instead of raising:
- `get_module_path()` — returns `None` if module has no `__file__`
- `decode_path_id()` — returns `None` if decoding fails
- Properties like `np` — return `""` if outside project root

"
