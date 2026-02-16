/*

synced from suitkaise-docs/paths/how-it-works.md

*/

rows = 2
columns = 1

# 1.1

title = "How `<suitkaise-api>paths</suitkaise-api>` actually works"

# 1.2

text = "
`<suitkaise-api>paths</suitkaise-api>` provides project-aware path handling, streamlining how you handle paths and ensuring cross-platform compatibility.

- `<suitkaise-api>Skpath</suitkaise-api>` - enhanced path object with automatic project root detection
- `<suitkaise-api>autopath</suitkaise-api>` - decorator for automatic path type conversion
- `<suitkaise-api>AnyPath</suitkaise-api>` - streamline path handling using this union type
- utility functions for project paths, validation, and sanitization

All paths use normalized separators (`/`) internally for cross-platform consistency.

## `<suitkaise-api>Skpath</suitkaise-api>`

Enhanced path object that wraps `pathlib.Path`.

Arguments
`path`: Path to wrap.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None`
- If `None`, uses the caller's file path

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: A new `<suitkaise-api>Skpath</suitkaise-api>` object.

When you create an `<suitkaise-api>Skpath</suitkaise-api>`, it automatically:
1. Detects the project root
2. Computes the absolute path (`ap`)
3. Computes the relative path to root (`rp`)
4. Generates a reversible encoded ID (`id`)

```text
<suitkaise-api>Skpath</suitkaise-api>("feature/file.txt") → detects root → computes ap, rp, id
```

`<suitkaise-api>Skpath</suitkaise-api>` defines a module-level `threading.RLock` (`_skpath_lock`) for potential thread-safe operations.

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

### `__init__(path: str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None)`

The constructor handles four input types.

```python
def __init__(self, path: str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None):
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
    
    elif isinstance(path, <suitkaise-api>Skpath</suitkaise-api>):
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
Uses `detect_caller_path()` which inspects the call stack to find the file that called `<suitkaise-api>Skpath</suitkaise-api>()`. This allows `<suitkaise-api>Skpath</suitkaise-api>()` to return a path to "this file" without passing any argument.

If `path` is `<suitkaise-api>Skpath</suitkaise-api>`:
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
   - Use the resolved path even if it doesn't exist yet
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
    except (ValueError, <suitkaise-api>PathDetectionError</suitkaise-api>):
        return ""  # outside project root
```

Returns empty string if path is outside project root.

#### `id` (encoded ID)

Reversible base64url encoded ID.

```python
@property
def <suitkaise-api>id</suitkaise-api>(self) -> str:
    if self._id is None:
        path_to_encode = self.rp if self.rp else self.ap
        self._id = encode_path_id(path_to_encode)
    return self._id
```

Uses `rp` if available (for cross-platform compatibility), otherwise `ap`.

Can be used to reconstruct the path: `<suitkaise-api>Skpath</suitkaise-api>(encoded_id)`.

#### `root`, `root_str`, `root_path`

Project root access in different formats.

- `root` → `<suitkaise-api>Skpath</suitkaise-api>` object
- `root_str` → `str` with normalized separators
- `root_path` → `pathlib.Path` object

### pathlib compatibility

`<suitkaise-api>Skpath</suitkaise-api>` mirrors most `pathlib.Path` properties and methods, including file IO helpers like `read_text()`, `write_text()`, `read_bytes()`, and `write_bytes()`.

Properties: `name`, `stem`, `suffix`, `suffixes`, `parent`, `parents`, `parts`, `exists`, `is_file`, `is_dir`, `is_symlink`, `is_empty`, `stat`, `lstat`

Methods: `iterdir()`, `glob()`, `rglob()`, `relative_to()`, `with_name()`, `with_stem()`, `with_suffix()`, `mkdir()`, `touch()`, `rmdir()`, `unlink()`, `resolve()`, `absolute()`

Additional methods: `copy_to()`, `move_to()` (with `overwrite` and `parents` options)

Additional properties:
- `as_dict`: Dictionary representation with `ap`, `rp`, `root`, `name`, `exists`
- `platform`: Absolute path with OS-native separators (backslash on Windows)

### Path joining

`<suitkaise-api>Skpath</suitkaise-api>` supports the `/` operator for joining paths.

```python
def __truediv__(self, other: str | Path | <suitkaise-api>Skpath</suitkaise-api>) -> <suitkaise-api>Skpath</suitkaise-api>:
    return <suitkaise-api>Skpath</suitkaise-api>(self._path / other_str)
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

`<suitkaise-api>Skpath</suitkaise-api>` implements `__fspath__()` to work with `open()`, `os.path`, etc.:

```python
def __fspath__(self) -> str:
    return to_os_separators(self.ap)
```

Returns OS-native separators (`\` on Windows, `/` elsewhere).

## Project Root Detection

Root detection walks up from a path looking for project indicators.

### Detection priority

1. Custom root (if set via `<suitkaise-api>set_custom_root</suitkaise-api>()`)
2. `setup.<suitkaise-api>sk</suitkaise-api>` file (`<suitkaise-api>suitkaise</suitkaise-api>` marker - highest priority)
3. Definitive indicators: `setup.py`, `setup.cfg`, `pyproject.toml`
4. Strong indicators: `.git`, `.gitignore`
5. License files: `LICENSE`, `LICENSE.txt`, etc. (case-insensitive)
6. README files: `README.md`, `README.txt`, etc. (case-insensitive)
7. Requirements files: `requirements.txt`, etc.

### Algorithm

```python
def _find_root_from_path(start_path: Path) -> Path | None:
    # First pass: look for setup.<suitkaise-api>sk</suitkaise-api> specifically
    check_path = current
    while check_path != check_path.<suitkaise-api>parent</suitkaise-api>:
        if (check_path / "setup.<suitkaise-api>sk</suitkaise-api>").exists():
            return check_path
        check_path = check_path.<suitkaise-api>parent</suitkaise-api>
    
    # Second pass: look for any indicator
    # Keep going up to find outermost <suitkaise-api>root</suitkaise-api> (handles nested projects)
    check_path = current
    best_root = None
    while check_path != check_path.<suitkaise-api>parent</suitkaise-api>:
        if _has_indicator(check_path):
            best_root = check_path
        check_path = check_path.<suitkaise-api>parent</suitkaise-api>
    
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

`<suitkaise-api>set_custom_root</suitkaise-api>(path)`: Override automatic detection.

`<suitkaise-api>get_custom_root</suitkaise-api>()`: Get current custom root (or `None`).

`<suitkaise-api>clear_custom_root</suitkaise-api>()`: Revert to automatic detection.

`<suitkaise-api>CustomRoot</suitkaise-api>(path)`: Context manager for temporary override.

All operations are thread-safe using `threading.RLock`.

## `<suitkaise-api>autopath</suitkaise-api>` Decorator

Decorator that automatically converts path parameters based on type annotations.

Arguments
`use_caller`: If True, parameters that accept `<suitkaise-api>Skpath</suitkaise-api>` or `Path` will use the caller's file path if no value was provided.
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
@<suitkaise-api>autopath</suitkaise-api>()
def process(path: <suitkaise-api>Skpath</suitkaise-api>):
    # path is guaranteed to be <suitkaise-api>Skpath</suitkaise-api>
    ...

# Equivalent to:
def process(path):
    path = <suitkaise-api>Skpath</suitkaise-api>(path) # conversion happens here
    ...
```

### Type detection

The decorator recognizes:
- Direct types: `<suitkaise-api>Skpath</suitkaise-api>`, `Path`, `str`
- Union types: `str | Path | <suitkaise-api>Skpath</suitkaise-api>` (AnyPath)
- Iterables: `list[<suitkaise-api>Skpath</suitkaise-api>]`, `tuple[Path, ...]`, `set[str]`

For union types, it picks the richest type.

- If `<suitkaise-api>Skpath</suitkaise-api>` is in the union → convert to `<suitkaise-api>Skpath</suitkaise-api>`
- Else if `Path` is in the union → convert to `Path`
- Else if `str` is in the union → convert to `str`

### Conversion

All path-like inputs flow through `<suitkaise-api>Skpath</suitkaise-api>` for normalization.

```text
input → <suitkaise-api>Skpath</suitkaise-api> → target type
```

This ensures:
- Resolved absolute paths
- Normalized separators (always `/`)
- Cross-platform consistency

```python
def _convert_value(value, target_type, ...):
    if target_type is <suitkaise-api>Skpath</suitkaise-api>:
        return <suitkaise-api>Skpath</suitkaise-api>(value)
    elif target_type is Path:
        return Path(<suitkaise-api>Skpath</suitkaise-api>(value).ap)
    elif target_type is str:
        return <suitkaise-api>Skpath</suitkaise-api>(value).ap
```

### `use_caller` option

When `use_caller=True`, missing path parameters are filled with the caller's file path.

```python
@<suitkaise-api>autopath</suitkaise-api>(use_caller=True)
def log_from(path: <suitkaise-api>Skpath</suitkaise-api> = None):
    print(f"Logging from: {path.rp}")

# Called without argument - uses caller's file
log_from() # logs the file that called log_from()
```

### `only` option

Restrict conversion to specific parameters.

```python
@<suitkaise-api>autopath</suitkaise-api>(only="file_path")
def process(file_path: str, names: list[str]):
    # only file_path is normalized
    # names is left unchanged (faster for large lists)
    ...
```

## General Utility Functions

### `<suitkaise-api>get_project_root</suitkaise-api>()`

Get the project root directory.

```python
def <suitkaise-api>get_project_root</suitkaise-api>(expected_name: str | None = None) -> <suitkaise-api>Skpath</suitkaise-api>:
    root_path = detect_project_root(expected_name=expected_name)
    return <suitkaise-api>Skpath</suitkaise-api>(root_path)
```

Arguments
`expected_name`: If provided, detected root must have this name.
- `str | None = None`
- positional or keyword

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Project root directory.

Raises
`<suitkaise-api>PathDetectionError</suitkaise-api>`: If root cannot be detected or doesn't match expected name.

### `<suitkaise-api>get_caller_path</suitkaise-api>()`

Get the file path of the caller.

```python
def <suitkaise-api>get_caller_path</suitkaise-api>() -> <suitkaise-api>Skpath</suitkaise-api>:
    caller = detect_caller_path(skip_frames=1)
    return <suitkaise-api>Skpath</suitkaise-api>(caller)
```

Uses `detect_caller_path()` which inspects the call stack, skipping internal frames to find the actual caller.

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Caller's file path.

Raises
`<suitkaise-api>PathDetectionError</suitkaise-api>`: If caller detection fails.

### `<suitkaise-api>get_current_dir</suitkaise-api>()`

Get the directory containing the caller's file.

```python
def <suitkaise-api>get_current_dir</suitkaise-api>() -> <suitkaise-api>Skpath</suitkaise-api>:
    caller = detect_caller_path(skip_frames=1)
    return <suitkaise-api>Skpath</suitkaise-api>(caller.<suitkaise-api>parent</suitkaise-api>)
```

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Caller's directory.

### `<suitkaise-api>get_cwd</suitkaise-api>()`

Get the current working directory.

```python
def <suitkaise-api>get_cwd</suitkaise-api>() -> <suitkaise-api>Skpath</suitkaise-api>:
    return <suitkaise-api>Skpath</suitkaise-api>(get_cwd_path())
```

Uses `Path.cwd()` internally.

Returns
`<suitkaise-api>Skpath</suitkaise-api>`: Current working directory.

### `<suitkaise-api>get_module_path</suitkaise-api>()`

Get the file path where an object is defined.

```python
def <suitkaise-api>get_module_path</suitkaise-api>(obj: Any) -> <suitkaise-api>Skpath</suitkaise-api> | None:
    path = get_module_file_path(obj)
    if path is None:
        return None
    return <suitkaise-api>Skpath</suitkaise-api>(path)
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
`<suitkaise-api>Skpath</suitkaise-api> | None`: Module file path, or None if not found.

Raises
`ImportError`: If obj is a module name string that cannot be imported.

### `<suitkaise-api>get_id</suitkaise-api>()`

Get the reversible encoded ID for a path.

```python
def <suitkaise-api>get_id</suitkaise-api>(path: str | Path | <suitkaise-api>Skpath</suitkaise-api>) -> str:
    if isinstance(path, <suitkaise-api>Skpath</suitkaise-api>):
        return path.<suitkaise-api>id</suitkaise-api>
    return <suitkaise-api>Skpath</suitkaise-api>(path).<suitkaise-api>id</suitkaise-api>
```

Arguments
`path`: Path to generate ID for.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api>`
- required

Returns
`str`: Base64url encoded ID.

### `<suitkaise-api>get_project_paths</suitkaise-api>()`

Get all paths in the project.

```python
def <suitkaise-api>get_project_paths</suitkaise-api>(
    root: str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None,
    exclude: str | Path | <suitkaise-api>Skpath</suitkaise-api> | list[...] | None = None,
    as_strings: bool = False,
    use_ignore_files: bool = True,
) -> list[<suitkaise-api>Skpath</suitkaise-api>] | list[str]:
    return _get_project_paths(
        root=root,
        exclude=exclude,
        as_strings=as_strings,
        use_ignore_files=use_ignore_files,
    )
```

Arguments
`root`: Custom root directory (defaults to detected project root).
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None`
- keyword only

`exclude`: Paths to exclude (single path or list).
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | list[...] | None = None`
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
`list[<suitkaise-api>Skpath</suitkaise-api>] | list[str]`: All project paths.

Raises
`<suitkaise-api>PathDetectionError</suitkaise-api>`: If project root cannot be detected.

### `<suitkaise-api>get_project_structure</suitkaise-api>()`

Get a nested dict representing the project structure.

```python
def <suitkaise-api>get_project_structure</suitkaise-api>(
    root: str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None,
    exclude: str | Path | <suitkaise-api>Skpath</suitkaise-api> | list[...] | None = None,
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
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None`
- keyword only

`exclude`: Paths to exclude.
- `str | Path | <suitkaise-api>Skpath</suitkaise-api> | list[...] | None = None`
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
`<suitkaise-api>PathDetectionError</suitkaise-api>`: If project root cannot be detected.

### `<suitkaise-api>get_formatted_project_tree</suitkaise-api>()`

Get a formatted tree string for the project structure.

```python
def <suitkaise-api>get_formatted_project_tree</suitkaise-api>(
    root: str | Path | <suitkaise-api>Skpath</suitkaise-api> | None = None,
    exclude: str | Path | <suitkaise-api>Skpath</suitkaise-api> | list[...] | None = None,
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

Uses box-drawing characters (`│`, `├─`, `└─`) to create visual hierarchy:

```text
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
`<suitkaise-api>PathDetectionError</suitkaise-api>`: If project root cannot be detected.

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

### `<suitkaise-api>is_valid_filename</suitkaise-api>()`

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

### `<suitkaise-api>streamline_path</suitkaise-api>()`

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

### `<suitkaise-api>streamline_path_quick</suitkaise-api>()`

Simple version of `<suitkaise-api>streamline_path</suitkaise-api>` with common defaults.

```python
def <suitkaise-api>streamline_path_quick</suitkaise-api>(
    path: str,
    max_len: int | None = None,
    replacement_char: str = "_",
    lowercase: bool = False
) -> str:
    return <suitkaise-api>streamline_path</suitkaise-api>(
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

### `<suitkaise-api>PathDetectionError</suitkaise-api>`

Raised when path or project root detection fails.

Examples:
- Project root cannot be detected (no indicators found)
- Custom root path doesn't exist or isn't a directory
- Expected root name doesn't match detected root

### `<suitkaise-api>NotAFileError</suitkaise-api>`

Raised when a file operation is attempted on a directory.

Example: Calling `<suitkaise-api>Skpath</suitkaise-api>.unlink()` on a directory.

## Types

### `<suitkaise-api>AnyPath</suitkaise-api>`

Type alias for path parameters that accept multiple types.

```python
from typing import Union

# using Union for forward reference compatibility at runtime
<suitkaise-api>AnyPath</suitkaise-api> = Union[str, Path, "<suitkaise-api>Skpath</suitkaise-api>"]
```

Note: Does NOT include `None` - use `<suitkaise-api>AnyPath</suitkaise-api> | None` when `None` is acceptable.

Use in function annotations to indicate a parameter accepts any path type:

```python
def process(path: <suitkaise-api>AnyPath</suitkaise-api>) -> None:
    ...
```

When used with `@<suitkaise-api>autopath</suitkaise-api>()`, parameters annotated with `<suitkaise-api>AnyPath</suitkaise-api>` are converted to `<suitkaise-api>Skpath</suitkaise-api>` (the richest type in the union).

## Thread Safety

Module-level state is protected by `threading.RLock` instances.

- `_root_lock`: Protects custom root state (`_custom_root`)
- `_cache_lock`: Protects cached root state (`_cached_root`, `_cached_root_source`)
- `_skpath_lock`: Defined for potential Skpath operations (currently unused)
- `_autopath_lock`: Defined for potential autopath operations (currently unused)
- `_id_lock`: Defined in id_utils for potential ID operations (currently unused)

RLock (reentrant lock) is used because operations may call each other (e.g., `detect_project_root()` is called from both `<suitkaise-api>Skpath</suitkaise-api>()` and custom root validation).

The root detection functions (`<suitkaise-api>set_custom_root</suitkaise-api>`, `<suitkaise-api>get_custom_root</suitkaise-api>`, `<suitkaise-api>clear_custom_root</suitkaise-api>`, `detect_project_root`) actively use locks to protect shared state.
"
