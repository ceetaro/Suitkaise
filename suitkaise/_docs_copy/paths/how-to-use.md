# paths: How to Use

This guide covers all public API exposed by `suitkaise.paths`.

```python
from suitkaise import paths
from suitkaise.paths import Skpath, autopath
```

## `Skpath`

### Construction

```python
Skpath()                 # caller file path
Skpath("src/main.py")    # from string
Skpath(Path("src"))      # from Path
Skpath(existing_skpath)  # copy
Skpath(encoded_id)       # decode from ID if valid
```

### Common properties

- `ap`: absolute normalized path
- `rp`: relative path to root (empty if outside)
- `id`: reversible encoded ID
- `root`: `Skpath` for project root
- `root_path`: `Path` for project root
- `root_str`: root as normalized string
- `name`, `stem`, `suffix`, `suffixes`, `parent`, `parents`, `parts`
- `exists`, `is_file`, `is_dir`, `is_symlink`, `is_empty`

### Path operations

```python
p = Skpath("src/main.py")
p.parent
p.with_suffix(".txt")
p.glob("*.py")
p.iterdir()
p.mkdir(parents=True, exist_ok=True)
p.touch()
p.unlink()
```

### Copy and move

```python
p.copy_to("dist/main.py", overwrite=True)
p.move_to("dist/main.py", overwrite=True)
```

### Dunder behavior

- `str(Skpath)` returns absolute normalized path
- `/` joins paths (`Skpath("src") / "main.py"`)
- Hashing uses the normalized path

## Project root and caller utilities

### `get_project_root(expected_name=None) -> Skpath`

```python
root = paths.get_project_root()
```

### `get_caller_path() -> Skpath`

```python
caller = paths.get_caller_path()
```

### `get_current_dir() -> Skpath`

```python
current_dir = paths.get_current_dir()
```

### `get_cwd() -> Skpath`

```python
cwd = paths.get_cwd()
```

### `get_module_path(obj) -> Skpath | None`

```python
paths.get_module_path(SomeClass)
paths.get_module_path("module_name")
```

## IDs

### `get_id(path) -> str`

```python
path_id = paths.get_id("src/main.py")
Skpath(path_id)  # reconstructs the path
```

## Project scanning

### `get_project_paths(...) -> list[Skpath] | list[str]`

```python
paths.get_project_paths()
paths.get_project_paths(root="src")
paths.get_project_paths(exclude=["build", "dist"])
paths.get_project_paths(as_strings=True)
paths.get_project_paths(use_ignore_files=False)
```

### `get_project_structure(...) -> dict`

```python
structure = paths.get_project_structure()
```

### `get_formatted_project_tree(...) -> str`

```python
tree = paths.get_formatted_project_tree(depth=2, include_files=True)
print(tree)
```

## Path validation utilities

### `is_valid_filename(filename) -> bool`

```python
paths.is_valid_filename("good.txt")  # True
paths.is_valid_filename("CON")       # False (Windows reserved)
```

### `streamline_path(...) -> str`

```python
paths.streamline_path("My File<1>.txt", chars_to_replace=" ")
paths.streamline_path("файл.txt", allow_unicode=False)
```

### `streamline_path_quick(...) -> str`

```python
paths.streamline_path_quick("My File<1>файл.txt")
```

## `@autopath` decorator

Automatically normalizes annotated path parameters:

```python
@autopath()
def load_data(path: Skpath, output_dir: Path):
    ...

@autopath(only=["path"])
def read(path: str, *, verbose: bool = False):
    ...
```

### Options

- `use_caller`: fill missing path args with caller file path
- `debug`: print conversion messages
- `only`: list of parameter names to convert
