# paths: How it Works

The `paths` module provides a project-root-aware `Skpath` class, automatic path normalization via `@autopath`, and project discovery utilities. Internals live in `suitkaise/paths/_int/`.

## `Skpath` design

### Core idea

`Skpath` normalizes all paths against an auto-detected project root. It keeps two canonical forms:

- `ap`: absolute path with normalized `/` separators
- `rp`: relative to project root (empty string if outside root)

This enables reproducible paths across machines and platforms.

### Construction logic

`Skpath.__init__` accepts:

- `None`: resolves caller file path
- `str`: treated as a path or an encoded ID
- `Path`: converted to resolved path
- `Skpath`: copies cached fields

String resolution rules:

1. If it looks like a path (contains separators), treat as path.
2. If it exists as a real path, use it.
3. If it is a valid encoded ID, decode to a relative path and join to root.
4. Fallback to treating it as a raw path.

### Lazy properties

`Skpath` computes expensive properties on demand and caches results:

- `root_path`: computed by `detect_project_root()`
- `rp`: computed relative to `root_path`
- `id`: base64url encoding of `rp` (or `ap` if outside root)

### Equality and hashing

`Skpath` compares by `rp` when available, otherwise by `ap`. Hashing uses a stable MD5-based integer for compatibility and speed.

## Root detection

Root detection lives in `root_detection.py` and has these priorities:

1. Custom root (`set_custom_root`)
2. `setup.sk` marker
3. Standard build files (`setup.py`, `pyproject.toml`, `setup.cfg`)
4. `.git`, `.gitignore`
5. License files (`LICENSE`, `LICENSE.md`, etc.)
6. README files
7. Requirements files

Algorithm:

- Walk upward from a start path
- Return the outermost valid root
- Cache the result for future calls

Thread safety is provided by `RLock` around shared root and cache state.

## `@autopath` decorator

`autopath` inspects type annotations and converts path-like inputs to the annotated type. It supports:

- `Skpath`, `Path`, `str`
- Unions (`X | Y` or `typing.Union`)
- Iterables (`list`, `tuple`, `set`, `Iterable`)

Conversion flow:

1. Convert input to `Skpath`
2. Convert `Skpath` to target type

If `use_caller=True`, any missing parameters are injected with the caller's file path.

## Project utilities

`get_project_paths`, `get_project_structure`, and `get_formatted_project_tree` are implemented in `project_utils.py`.

Ignore handling:

- Reads `.*ignore` files (.gitignore, .cursorignore, etc.)
- Uses `fnmatch` to filter entries
- Negation patterns (`!pattern`) are not applied

Performance choices:

- Filters directories before descending
- Handles permission errors gracefully
- Returns `Skpath` or `str` based on `as_strings`

## ID utilities

`id_utils.py` provides reversible IDs:

- `encode_path_id`: base64url encode (padding removed)
- `decode_path_id`: decode (returns `None` if invalid)
- `is_valid_encoded_id`: heuristics to disambiguate IDs from real paths
- `normalize_separators`: normalizes `\\` to `/`

These IDs let you store a short token and reconstruct a path relative to the project root.

## Caller path detection

`caller_paths.py` uses `inspect.stack()` to find the first frame outside the suitkaise package:

- Built-in or frozen frames are skipped
- Internal suitkaise frames are skipped
- You can offset frames with `skip_frames`

When no valid caller exists (interactive shell or compiled code), `PathDetectionError` is raised (or `None` returned in raw helpers).

## Exceptions

- `PathDetectionError`: raised for root/caller detection failures or invalid path IDs
- `NotAFileError`: raised when file operations are attempted on directories

## Cross-platform strategy

Internally, `Skpath` always stores normalized `/` separators.  
`__fspath__` returns OS-native separators for compatibility.
