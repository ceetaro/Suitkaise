# SKPath Info - How It Works Under the Hood

This document explains how each component of the SKPath API actually works internally.

## Table of Contents

1. [Core Architecture](#core-architecture)
2. [Main Class](#main-class)
3. [Convenience Functions](#convenience-functions)
4. [Project Root Management](#project-root-management)
5. [Decorators](#decorators)
6. [Factory Functions](#factory-functions)
7. [Internal Mechanisms](#internal-mechanisms)

## Core Architecture

### Dual-Path System
SKPath maintains two representations of every path:
- **Absolute Path (ap)**: The full filesystem path
- **Normalized Path (np)**: Path relative to the detected project root

### Global State
- **Project Root Cache**: Cached result of expensive project root detection
- **Global Detector**: Singleton `_ProjectRootDetector` instance
- **Forced Root Override**: Optional manual project root setting

---

## Main Class

### `SKPath`

**Purpose**: Smart path object with dual-path architecture and automatic project root detection.

**How it works internally**:

1. **Initialization Process**:
   ```python
   def __init__(self, path=None, project_root=None):
   ```
   - If `path` is None: Uses `_get_non_sk_caller_file_path()` to detect caller's file
       - this inspects the frame stack to find the first non-suitkaise file path in the stack.
   - Converts any relative path to absolute using `Path.resolve()`
   - Auto-detects project root using `_get_project_root()` if not provided
       - this is the expensive operation, so it is cached in the _project_root_cache dictionary
   - Calculates normalized path using `_calculate_normalized_path()`

2. **Project Root Detection**:
   - Calls `_get_project_root()` with the file's parent directory
   - Uses sophisticated algorithm requiring LICENSE + README + requirements files
   - also uses indicators to score the current directory, choosing the highest scoring directory with the required files as the project root
   - Falls back to None if no valid project root found
   - the user can add the name of the directory that is their project root, and it will return None if that directory is not a valid project root (missing the required files)
   - helpful for figuring out if your project has been set up correctly with basic files

3. **Normalized Path Calculation**:
   ```python
   def _calculate_normalized_path(self) -> str:
   ```
   - Uses `Path.relative_to()` to get path relative to project root
   - Normalizes separators to forward slashes for cross-platform consistency
       - (normalizes to Unix style paths, where the root is always /root, and forward slashes are used)
   - Falls back to absolute path if file is outside project root

4. **String Conversion**:
   - `__str__()` returns absolute path for compatibility
   - `__fspath__()` enables direct use with `open()`, `shutil`, etc.
   - `__repr__()` shows both paths for debugging

5. **Path Operations**:
   - Wraps standard `pathlib.Path` methods with better cross-platform functionality
   - Returns new `SKPath` objects to maintain dual-path behavior
   - Preserves project root context across operations

---

## Convenience Functions

### `get_project_root(expected_name=None)`

**Purpose**: Find project root directory using sophisticated detection algorithm.

**How it works internally**:
1. **Caching**: Checks global cache `_project_root_cache` first
2. **Caller Detection**: Uses `_get_non_sk_caller_file_path()` to find starting point
3. **Detection Process**: Delegates to `_global_detector.find_project_root()`
4. **Algorithm**: 
   - Walks up directory tree from starting point
   - Uses `_ProjectRootDetector` with two-phase approach:
     - **Phase 1**: Check for necessary files (LICENSE, README, requirements)
     - **Phase 2**: Score based on project indicators (setup.py, .git, etc.)
   - Returns directory with highest confidence score above threshold
5. **Caching**: Stores result with cache key `f"{start_path}:{expected_name}"`

### `get_caller_path()`

**Purpose**: Get SKPath of file that called this function, ignoring suitkaise internals.

**How it works internally**:
1. Uses `_get_non_sk_caller_file_path()` to find the first non-suitkaise file path in the stack (the user's actual file calling this function)
2. **Frame Walking**: 
   ```python
   frame = inspect.currentframe()
   while caller_frame is not None:
   ```
   - Walks up call stack using `inspect.currentframe()`
   - Checks each frame's `__file__` attribute
   - Uses `_is_suitkaise_module()` to skip internal frames
   - Returns first non-suitkaise file found
3. Wraps result in `SKPath` with auto-detected project root

### `get_current_dir()`

**Purpose**: Get directory of the calling file.

**How it works internally**:
1. Calls `_get_current_dir()` which uses `_get_non_sk_caller_file_path()`
2. Returns parent directory of caller file as `SKPath`
3. Automatically detects project root for the directory

### `get_cwd()`

**Purpose**: Get current working directory as SKPath.

**How it works internally**:
1. Uses standard `Path.cwd()` to get working directory
2. Wraps in `SKPath` with auto-detected project root
3. Provides both absolute and project-relative views

### `equalpaths(path1, path2)`

**Purpose**: Intelligent path comparison with project-aware semantics.

**How it works internally**:
1. **Normalization**: Converts both paths to `SKPath` objects if needed
2. **Comparison Strategy**:
   - **First**: Compare normalized paths (`path1.np == path2.np`)
   - **Fallback**: Compare absolute paths using `_equal_paths()`
3. **Cross-platform**: Handles different path separators and case sensitivity

### `path_id(path, short=False)` and `path_id_short(path)`

**Purpose**: Generate reproducible identifiers for paths.

**How it works internally**:
1. Converts input to absolute path string
2. **Hashing**: Uses MD5 hash of absolute path
3. **ID Generation**:
   - **Short**: `filename_hash[:8]` (first 8 characters of the hash)
   - **Long**: full hash
4. **Reproducibility**: Same path always generates same ID

### `get_all_project_paths(custom_root=None, except_paths=None, as_str=False, ignore=True)`

**Purpose**: Smart file discovery with automatic ignore file integration.

**How it works internally**:
1. **Root Detection**: Uses `custom_root` or `_get_project_root()`
2. **Ignore Processing**:
   ```python
   if ignore:
       ignore_patterns.update(_parse_gitignore_file(gitignore_path))
   ```
   - Parses `.gitignore` and `.dockerignore` files
   - Adds default ignore patterns (`__pycache__`, `.git`, etc.)
3. **Directory Walking**: Uses `os.walk()` with ignore filtering
4. **Filtering**: `should_ignore()` function checks patterns using `fnmatch`
5. **Result Processing**: Returns `SKPath` objects or strings based on `as_str`

### `get_project_structure(custom_root=None, except_paths=None, ignore=True)`

**Purpose**: Build nested dictionary representing project structure.

**How it works internally**:
1. Uses same root detection and ignore logic as `get_all_project_paths`
2. **Recursive Building**:
   ```python
   def build_structure(path: Path) -> Dict:
   ```
   - Recursively walks directories
   - Creates nested dictionaries for directories
   - Marks files with `'file'` value
3. **Ignore Integration**: Respects same ignore patterns

### `get_formatted_project_tree(custom_root=None, max_depth=3, show_files=True, except_paths=None, ignore=True)`

**Purpose**: Generate ASCII tree representation of project structure.

**How it works internally**:
1. Uses same root detection and ignore logic
2. **Tree Formatting**:
   ```python
   def format_tree(path: Path, prefix: str = "", depth: int = 0):
   ```
   - Recursively formats with tree characters (`├──`, `└──`, `│`)
   - Controls depth with `max_depth` parameter
   - Sorts items for consistent output
3. **Character Selection**: Chooses appropriate tree characters based on position

---

## Project Root Management

### `force_project_root(path)`, `clear_forced_project_root()`, `get_forced_project_root()`

**Purpose**: Override automatic project root detection for testing/special cases.

**How it works internally**:
1. **Global Override**: Uses `_global_detector.force_project_root()`
2. **Cache Invalidation**: Clears `_project_root_cache` when forcing/clearing
3. **Validation**: `force_project_root()` validates path exists and is directory
4. **Detection Override**: When forced root is set, `_get_project_root()` returns it immediately

---

## Decorators

### `autopath(autofill=False, defaultpath=None)`

**Purpose**: Automatically convert path parameters to appropriate types.

**How it works internally**:
1. **Function Introspection**:
   ```python
   sig = inspect.signature(func)
   ```
   - Uses `inspect.signature()` to analyze function parameters
   - Finds parameters with 'path' in the name using `path_params = [name for name in bound_args.arguments.keys() if 'path' in name.lower()]`

2. **Parameter Processing**:
   - **Binding**: Uses `sig.bind_partial(*args, **kwargs)` to map arguments
   - **Path Detection**: Only processes parameters with 'path' in name
   - **Type Detection**: Uses annotation introspection to determine if parameter accepts SKPath

3. **Conversion Logic**:
   ```python
   if isinstance(param_value, SKPath):
       if not accepts_skpath and accepts_str:
           bound_args.arguments[param_name] = str(param_value)
   elif isinstance(param_value, (str, Path)):
       if looks_like_path and accepts_skpath:
           bound_args.arguments[param_name] = SKPath(param_value)
   ```

4. **Path Validation**:
   - **Heuristics**: Checks for separators, extensions, absolute paths
   - **Safety**: Only converts strings that look like valid paths
   - **Fallback**: Leaves non-path strings unchanged

5. **Default Handling**:
   - **autofill**: Uses `_get_non_sk_caller_file_path()` when parameter is None
   - **defaultpath**: Overrides autofill with specified path

---

## Factory Functions

### `create(path=None, custom_root=None)`

**Purpose**: Factory function for creating SKPath objects.

**How it works internally**:
1. **Simple Wrapper**: Direct call to `SKPath(path, project_root)`
2. **Root Processing**: Converts `custom_root` to resolved Path if provided
3. **Auto-detection**: Falls back to automatic project root detection if no custom root

---

## Internal Mechanisms

### Project Root Detection Algorithm

**Core Class**: `_ProjectRootDetector`

**Two-Phase Detection**:
1. **Necessary Files Check**: Requires LICENSE + README + requirements files
2. **Confidence Scoring**: Weights different indicators:
   - Strong indicators (0.4): app/, data/, docs/, tests/ directories
   - Regular indicators (0.3): setup.py, .gitignore files
   - Weak indicators (0.1): Makefile, docker-compose files

**Scoring Calculation**:
```python
score = sum(len(matches) * weight for category, matches in indicators.items())
```

### Caller Detection Magic

**Key Function**: `_get_non_sk_caller_file_path()`

**Frame Walking Process**:
1. Gets current frame with `inspect.currentframe()`
2. Walks up stack until finding non-suitkaise frame
3. **Suitkaise Detection**: Uses `_is_suitkaise_module()` which checks:
   - Path relative to `_SUITKAISE_BASE_PATH`
   - Common installation patterns (`site-packages/suitkaise`)

### Caching System

**Project Root Cache**:
```python
_project_root_cache = {
    'root': None,
    'cache_key': None  # format: "start_path:expected_name"
}
```

**Cache Strategy**:
- Cache key combines start path and expected name
- Invalidated when forcing/clearing project root
- Avoids expensive filesystem operations on repeated calls

### Ignore File Processing

**Supported Files**: `.gitignore`, `.dockerignore`

**Processing**:
1. **Parsing**: `_parse_gitignore_file()` reads and processes patterns
2. **Pattern Matching**: Uses `fnmatch` for wildcard support
3. **Default Patterns**: Built-in patterns for common ignore cases
4. **Integration**: Combined with custom `except_paths` parameter

This architecture provides the "magical" behavior users experience while maintaining clear separation of concerns and efficient caching strategies.
