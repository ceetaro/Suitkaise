# How `paths` actually works

`paths` provides project-aware path handling, streamlining how you handle paths and ensuring cross-platform compatibility.

- `Skpath` - enhanced path object with automatic project root detection
- `autopath` - decorator for automatic path type conversion
- `AnyPath` - streamline path handling using this union type
- utility functions for project paths, validation, and sanitization

All paths use normalized separators (`/`) internally for cross-platform consistency.

## `Skpath`

Enhanced path object that wraps `pathlib.Path`.

Arguments
`path`: Path to wrap.
- `str | Path | Skpath | None = None`
- If `None`, uses the caller's file path

Returns
`Skpath`: A new `Skpath` object.

When you create an `Skpath`, it automatically:
1. Detects the project root
2. Computes the absolute path (`ap`)
3. Computes the relative path to root (`rp`)
4. Generates a reversible encoded ID (`id`)

```
Skpath("feature/file.txt") → detects root → computes ap, rp, id
```

`Skpath` defines a module-level `threading.RLock` (`_skpath_lock`) for potential thread-safe operations.

### Tracking state

`_path: Path`
The underlying `pathlib.Path` object. Always resolved to an absolute path.

`_root: Path | None`
Cached project root. Lazily detected on first access.

`_ap: str | None`
Cached absolute path with normalized separators. Lazily computed.

`_rp: str | None`
Cached relative path to project root. Lazily computed.

`_id: str | None`
Cached base64url encoded ID. Lazily computed.

`_hash: int | None`
Cached hash value for use in sets and dicts.

### `__init__(path: str | Path | Skpath | None = None)`

The constructor handles four input types.

```python
def __init__(self, path: str | Path | Skpath | None = None):
    # initialize cached values
    self._path: Path
    self._root: Path | None = None
    self._ap: str | None = None
    self._rp: str | None = None
    self._id: str | None = None
    self._hash: int | None = None
    
    if path is None:
        # detect caller's file path using frame inspection
        self._path = detect_caller_path()
    
    elif isinstance(path, Skpath):
        # copy all values from source (avoids recomputation)
        self._path = path._path
        self._root = path._root
        self._ap = path._ap
        self._rp = path._rp
        self._id = path._id
        self._hash = path._hash
    
    elif isinstance(path, Path):
        # resolve to absolute path
        self._path = path.resolve()
    
    elif isinstance(path, str):
        # try multiple interpretations
        self._path = self._resolve_string_path(path)
```

If `path` is `None`:
Uses `detect_caller_path()` which inspects the call stack to find the file that called `Skpath()`. This allows `Skpath()` to return a path to "this file" without passing any argument.

If `path` is `Skpath`:
Copies all cached values directly. This is an optimization - if someone passes an existing Skpath, we don't recompute `ap`, `rp`, `id`, etc.

If `path` is `Path`:
Calls `.resolve()` to get an absolute path with symlinks resolved.

If `path` is `str`:
Calls `_resolve_string_path()` which tries multiple interpretations (see below).

### String path resolution

`_resolve_string_path()` tries multiple interpretations.

1. If string contains `/` or `\`:
   - Treat as path, resolve to absolute
2. If string exists as a file/directory:
   - Treat as relative path, resolve to absolute
3. If string looks like a base64url encoded ID:
   - Try to decode it
   - If decoded path is relative, resolve from project root
   - If decoded path exists, use it
4. Fall back to treating as path (may not exist)

### Core properties

#### `ap` (absolute path)

Absolute path with normalized separators (`/`).

```python
@property
def ap(self) -> str:
    if self._ap is None:
        self._ap = normalize_separators(str(self._path))
    return self._ap
```

Always available, even for paths outside project root.

#### `rp` (relative path)

Path relative to project root with normalized separators.

```python
@property
def rp(self) -> str:
    if self._rp is None:
        self._rp = self._compute_rp()
    return self._rp

def _compute_rp(self) -> str:
    try:
        root = self.root_path
        rel_path = self._path.relative_to(root)
        return normalize_separators(str(rel_path))
    except (ValueError, PathDetectionError):
        return ""  # outside project root
```

Returns empty string if path is outside project root.

#### `id` (encoded ID)

Reversible base64url encoded ID.

```python
@property
def id(self) -> str:
    if self._id is None:
        path_to_encode = self.rp if self.rp else self.ap
        self._id = encode_path_id(path_to_encode)
    return self._id
```

Uses `rp` if available (for cross-platform compatibility), otherwise `ap`.

Can be used to reconstruct the path: `Skpath(encoded_id)`.

#### `root`, `root_str`, `root_path`

Project root access in different formats.

- `root` → `Skpath` object
- `root_str` → `str` with normalized separators
- `root_path` → `pathlib.Path` object

### pathlib compatibility

`Skpath` mirrors most `pathlib.Path` properties and methods.

Properties: `name`, `stem`, `suffix`, `suffixes`, `parent`, `parents`, `parts`, `exists`, `is_file`, `is_dir`, `is_symlink`, `is_empty`, `stat`, `lstat`

Methods: `iterdir()`, `glob()`, `rglob()`, `relative_to()`, `with_name()`, `with_stem()`, `with_suffix()`, `mkdir()`, `touch()`, `rmdir()`, `unlink()`, `resolve()`, `absolute()`

Additional methods: `copy_to()`, `move_to()` (with `overwrite` and `parents` options)

Additional properties:
- `as_dict`: Dictionary representation with `ap`, `rp`, `root`, `name`, `exists`
- `platform`: Absolute path with OS-native separators (backslash on Windows)

### Path joining

`Skpath` supports the `/` operator for joining paths.

```python
def __truediv__(self, other: str | Path | Skpath) -> Skpath:
    return Skpath(self._path / other_str)
```

### Equality and hashing

Equality compares `rp` first (for cross-platform consistency), then falls back to `ap`.

```python
def __eq__(self, other: Any) -> bool:
    if self.rp and other_skpath.rp and self.rp == other_skpath.rp:
        return True
    return self.ap == other_skpath.ap
```

Hashing uses MD5 of `rp` (or `ap` if outside project root).

### `__fspath__` compatibility

`Skpath` implements `__fspath__()` to work with `open()`, `os.path`, etc.:

```python
def __fspath__(self) -> str:
    return to_os_separators(self.ap)
```

Returns OS-native separators (`\` on Windows, `/` elsewhere).

## Project Root Detection

Root detection walks up from a path looking for project indicators.

### Detection priority

1. Custom root (if set via `set_custom_root()`)
2. `setup.sk` file (`suitkaise` marker - highest priority)
3. Definitive indicators: `setup.py`, `setup.cfg`, `pyproject.toml`
4. Strong indicators: `.git`, `.gitignore`
5. License files: `LICENSE`, `LICENSE.txt`, etc. (case-insensitive)
6. README files: `README.md`, `README.txt`, etc. (case-insensitive)
7. Requirements files: `requirements.txt`, etc.

### Algorithm

```python
def _find_root_from_path(start_path: Path) -> Path | None:
    # First pass: look for setup.sk specifically
    check_path = current
    while check_path != check_path.parent:
        if (check_path / "setup.sk").exists():
            return check_path
        check_path = check_path.parent
    
    # Second pass: look for any indicator
    # Keep going up to find outermost root (handles nested projects)
    check_path = current
    best_root = None
    while check_path != check_path.parent:
        if _has_indicator(check_path):
            best_root = check_path
        check_path = check_path.parent
    
    return best_root
```

### Caching

Detected roots are cached to avoid repeated filesystem walks.

```python
_cached_root: Path | None = None
_cached_root_source: Path | None = None  # path used to detect cached root
```

Cache is invalidated when searching from a path outside the cached root.

Use `clear_root_cache()` to manually clear the cache.

### Custom root management

`set_custom_root(path)`: Override automatic detection.

`get_custom_root()`: Get current custom root (or `None`).

`clear_custom_root()`: Revert to automatic detection.

`CustomRoot(path)`: Context manager for temporary override.

All operations are thread-safe using `threading.RLock`.

## `autopath` Decorator

Decorator that automatically converts path parameters based on type annotations.

Arguments
`use_caller`: If True, parameters that accept `Skpath` or `Path` will use the caller's file path if no value was provided.
- `bool = False`
- keyword only

`debug`: If True, print messages when conversions occur.
- `bool = False`
- keyword only

`only`: Only apply autopath to specific params.
- `str | list[str] | None = None`
- If None, all path-like params are normalized (strs, Paths, Skpaths). If a param accepts str or list[str] and is listed in only, autopath will apply. If only is not None AND a param is not listed in only, autopath will not be applied to values being passed into that param.

### How it works

1. Inspects function signature and type hints
2. Identifies parameters annotated with path types
3. Wraps the function to convert inputs before calling

```python
@autopath()
def process(path: Skpath):
    # path is guaranteed to be Skpath
    ...

# Equivalent to:
def process(path):
    path = Skpath(path) # conversion happens here
    ...
```

### Type detection

The decorator recognizes:
- Direct types: `Skpath`, `Path`, `str`
- Union types: `str | Path | Skpath` (AnyPath)
- Iterables: `list[Skpath]`, `tuple[Path, ...]`, `set[str]`

For union types, it picks the richest type.

- If `Skpath` is in the union → convert to `Skpath`
- Else if `Path` is in the union → convert to `Path`
- Else if `str` is in the union → convert to `str`

### Conversion

All path-like inputs flow through `Skpath` for normalization.

```
input → Skpath → target type
```

This ensures:
- Resolved absolute paths
- Normalized separators (always `/`)
- Cross-platform consistency

```python
def _convert_value(value, target_type, ...):
    if target_type is Skpath:
        return Skpath(value)
    elif target_type is Path:
        return Path(Skpath(value).ap)
    elif target_type is str:
        return Skpath(value).ap
```

### `use_caller` option

When `use_caller=True`, missing path parameters are filled with the caller's file path.

```python
@autopath(use_caller=True)
def log_from(path: Skpath = None):
    print(f"Logging from: {path.rp}")

# Called without argument - uses caller's file
log_from() # logs the file that called log_from()
```

### `only` option

Restrict conversion to specific parameters.

```python
@autopath(only="file_path")
def process(file_path: str, names: list[str]):
    # only file_path is normalized
    # names is left unchanged (faster for large lists)
    ...
```

## General Utility Functions

### `get_project_root()`

Get the project root directory.

```python
def get_project_root(expected_name: str | None = None) -> Skpath:
    root_path = detect_project_root(expected_name=expected_name)
    return Skpath(root_path)
```

Arguments
`expected_name`: If provided, detected root must have this name.
- `str | None = None`
- positional or keyword

Returns
`Skpath`: Project root directory.

Raises
`PathDetectionError`: If root cannot be detected or doesn't match expected name.

### `get_caller_path()`

Get the file path of the caller.

```python
def get_caller_path() -> Skpath:
    caller = detect_caller_path(skip_frames=1)
    return Skpath(caller)
```

Uses `detect_caller_path()` which inspects the call stack, skipping internal frames to find the actual caller.

Returns
`Skpath`: Caller's file path.

Raises
`PathDetectionError`: If caller detection fails.

### `get_current_dir()`

Get the directory containing the caller's file.

```python
def get_current_dir() -> Skpath:
    caller = detect_caller_path(skip_frames=1)
    return Skpath(caller.parent)
```

Returns
`Skpath`: Caller's directory.

### `get_cwd()`

Get the current working directory.

```python
def get_cwd() -> Skpath:
    return Skpath(get_cwd_path())
```

Uses `Path.cwd()` internally.

Returns
`Skpath`: Current working directory.

### `get_module_path()`

Get the file path where an object is defined.

```python
def get_module_path(obj: Any) -> Skpath | None:
    path = get_module_file_path(obj)
    if path is None:
        return None
    return Skpath(path)
```

Arguments
`obj`: Object to inspect (module, class, function, etc.).
- `Any`
- required

The function handles:
- Module objects: Uses `__file__` attribute
- Module name strings: Imports the module, then uses `__file__`
- Objects with `__module__`: Gets the module, then uses `__file__`

Returns
`Skpath | None`: Module file path, or None if not found.

Raises
`ImportError`: If obj is a module name string that cannot be imported.

### `get_id()`

Get the reversible encoded ID for a path.

```python
def get_id(path: str | Path | Skpath) -> str:
    if isinstance(path, Skpath):
        return path.id
    return Skpath(path).id
```

Arguments
`path`: Path to generate ID for.
- `str | Path | Skpath`
- required

Returns
`str`: Base64url encoded ID.

### `get_project_paths()`

Get all paths in the project.

```python
def get_project_paths(
    root: str | Path | Skpath | None = None,
    exclude: str | Path | Skpath | list[...] | None = None,
    as_strings: bool = False,
    use_ignore_files: bool = True,
) -> list[Skpath] | list[str]:
    return _get_project_paths(
        root=root,
        exclude=exclude,
        as_strings=as_strings,
        use_ignore_files=use_ignore_files,
    )
```

Arguments
`root`: Custom root directory (defaults to detected project root).
- `str | Path | Skpath | None = None`
- keyword only

`exclude`: Paths to exclude (single path or list).
- `str | Path | Skpath | list[...] | None = None`
- keyword only

`as_strings`: Return string paths instead of Skpath objects.
- `bool = False`
- keyword only

`use_ignore_files`: Respect .gitignore, .cursorignore, etc.
- `bool = True`
- keyword only

The function:
1. Detects or uses provided root
2. Walks the directory tree
3. Filters out paths matching `.*ignore` patterns (if enabled)
4. Filters out explicitly excluded paths
5. Returns as Skpath objects or strings

Returns
`list[Skpath] | list[str]`: All project paths.

Raises
`PathDetectionError`: If project root cannot be detected.

### `get_project_structure()`

Get a nested dict representing the project structure.

```python
def get_project_structure(
    root: str | Path | Skpath | None = None,
    exclude: str | Path | Skpath | list[...] | None = None,
    use_ignore_files: bool = True,
) -> dict:
    return _get_project_structure(
        root=root,
        exclude=exclude,
        use_ignore_files=use_ignore_files,
    )
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

Returns a nested dict where:
- Keys are directory/file names
- Values are empty dicts for files, nested dicts for directories

```python
{
    "myproject": {
        "src": {
            "main.py": {},
            "utils.py": {}
        },
        "tests": {...}
    }
}
```

Returns
`dict`: Nested dictionary of project structure.

Raises
`PathDetectionError`: If project root cannot be detected.

### `get_formatted_project_tree()`

Get a formatted tree string for the project structure.

```python
def get_formatted_project_tree(
    root: str | Path | Skpath | None = None,
    exclude: str | Path | Skpath | list[...] | None = None,
    use_ignore_files: bool = True,
    depth: int | None = None,
    include_files: bool = True,
) -> str:
    return _get_formatted_project_tree(
        root=root,
        exclude=exclude,
        use_ignore_files=use_ignore_files,
        depth=depth,
        include_files=include_files,
    )
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

Uses box-drawing characters (`│`, `├─`, `└─`) to create visual hierarchy:

```
myproject/
├── src/
│   ├── main.py
│   └── utils/
└── tests/
    └── test_main.py
```

Returns
`str`: Formatted tree string.

Raises
`PathDetectionError`: If project root cannot be detected.

## Path ID Encoding

Path IDs use base64url encoding for safe transport.

```python
def encode_path_id(path_str: str) -> str:
    # normalize path separators first
    normalized = normalize_separators(path_str)
    encoded = base64.urlsafe_b64encode(normalized.encode("utf-8"))
    # remove padding for cleaner IDs
    return encoded.decode("utf-8").rstrip("=")

def decode_path_id(encoded_id: str) -> str | None:
    try:
        # add back padding if needed
        padding = 4 - (len(encoded_id) % 4)
        if padding != 4:
            encoded_id += "=" * padding
        
        decoded = base64.urlsafe_b64decode(encoded_id.encode("utf-8"))
        return decoded.decode("utf-8")
    except Exception:
        return None
```

The encoding is:
- URL-safe (uses `-` and `_` instead of `+` and `/`)
- Reversible (can reconstruct original path)
- Padding-stripped (for cleaner IDs)
- Path separators normalized to `/` before encoding

## Path Validation and Sanitization

### `is_valid_filename()`

Arguments
`filename`: Filename to validate.
- `str`
- required

Returns
`bool`: True if valid, False otherwise.

Checks if a filename is valid across common operating systems.

1. Not empty or whitespace-only
2. No invalid characters: `<>:"/\|?*\0`
3. No problematic characters: `\t\n\r`
4. Not a Windows reserved name: `CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`
5. Doesn't end with space or period

### `streamline_path()`

Sanitizes a path by replacing invalid characters.

Arguments
`path`: Path to sanitize.
- `str`
- required

`max_len`: Maximum length to truncate to.
- `int | None = None`
- keyword only
- If None, no truncation is performed.

`replacement_char`: Character to replace invalid characters with.
- `str = "_"`
- keyword only

`lowercase`: Convert to lowercase.
- `bool = False`
- keyword only

`strip_whitespace`: Strip whitespace.
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

1. Strip whitespace (if enabled)
2. Replace extra specified characters
3. Replace invalid characters with replacement char
4. Replace problematic characters
5. Replace non-ASCII characters (if `allow_unicode=False`)
6. Lowercase (if enabled)
7. Truncate to max length (preserving suffix)
8. Clean up trailing spaces/periods

### `streamline_path_quick()`

Simple version of `streamline_path` with common defaults.

```python
def streamline_path_quick(
    path: str,
    max_len: int | None = None,
    replacement_char: str = "_",
    lowercase: bool = False
) -> str:
    return streamline_path(
        path,
        max_len=max_len,
        replacement_char=replacement_char,
        lowercase=lowercase,
        strip_whitespace=True,
        chars_to_replace=" ",
        allow_unicode=False,
    )
```

Arguments
`path`: Path to sanitize.
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

This version:
- Always strips whitespace
- Replaces spaces with replacement char
- Disallows unicode (ASCII only)

## Exceptions

### `PathDetectionError`

Raised when path or project root detection fails.

Examples:
- Project root cannot be detected (no indicators found)
- Custom root path doesn't exist or isn't a directory
- Expected root name doesn't match detected root

### `NotAFileError`

Raised when a file operation is attempted on a directory.

Example: Calling `Skpath.unlink()` on a directory.

## Types

### `AnyPath`

Type alias for path parameters that accept multiple types.

```python
from typing import Union

# using Union for forward reference compatibility at runtime
AnyPath = Union[str, Path, "Skpath"]
```

Note: Does NOT include `None` - use `AnyPath | None` when `None` is acceptable.

Use in function annotations to indicate a parameter accepts any path type:

```python
def process(path: AnyPath) -> None:
    ...
```

When used with `@autopath()`, parameters annotated with `AnyPath` are converted to `Skpath` (the richest type in the union).

## Thread Safety

Module-level state is protected by `threading.RLock` instances.

- `_root_lock`: Protects custom root state (`_custom_root`)
- `_cache_lock`: Protects cached root state (`_cached_root`, `_cached_root_source`)
- `_skpath_lock`: Defined for potential Skpath operations (currently unused)
- `_autopath_lock`: Defined for potential autopath operations (currently unused)
- `_id_lock`: Defined in id_utils for potential ID operations (currently unused)

RLock (reentrant lock) is used because operations may call each other (e.g., `detect_project_root()` is called from both `Skpath()` and custom root validation).

The root detection functions (`set_custom_root`, `get_custom_root`, `clear_custom_root`, `detect_project_root`) actively use locks to protect shared state.
