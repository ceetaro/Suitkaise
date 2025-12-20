/*

how to use the skpath module. this is the default page when entered from the home page "learn more" or nav bar sidebar "skpath" link.

*/

rows = 2
columns = 1

# 1.1

title = "How to use `skpath`"

text = "

`skpath` makes file paths much easier to work with.

## `SKPath` class

Special path object. Automatically detects your project root and uses it to normalize paths.

- `SKPath.ap` - absolute path. All slashes are streamlined to `/` for cross-platform compatibility.

"Users/john/Documents/projects/myproject/feature1/file.txt"

- `SKPath.np` - normalized path, relative to project root

"myproject/feature1/file.txt"

```python
from suitkaise.skpath import SKPath

# create SKPath object with caller file path
path = SKPath()

# create SKPath object with Path object
path = SKPath(Path("feature1/file.txt"))

# and with string object
path = SKPath("feature1/file.txt")
```

Recommend not relying on just on file name, add at least the directory too.
```python\
path = SKPath("file.txt") # DON'T DO THIS!
```

(this is a dropdown section)
### `SKPath` Properties and Methods

- `ap` - absolute path
- `np` - path normalized to project root

Unique to `SKPath`

- `id(length)` - reproducible string ID for the path (default: 32 chars)

Common

- `root` - project root
- `last` - last part of the path

    - `last.name` - last part of the path without suffix if there is one (`"file.txt"` -> `"file"`)

    - `last.suffix` - suffix of last part of path if there is one (`"file.txt"` -> `".txt"`)

- `parent` - parent directory of the last part of the path
- `parts` - path parts as a tuple
- `exists` - whether the path exists
- `is_file` - whether the path is a file
- `is_dir` - whether the path is a directory


```python
path = SKPath("myproject/feature1")

path_as_string = str(path)

path_as_repr = repr(path)

# works with Paths and strings as well
if path == other_path:

    # ...

# truediv to join paths
child_path = path / "content" / "file.txt"

# os.fspath()
with open(path, "r") as f:

    # ...
```

Uncommon

- `is_symlink` - whether the path is a symlink
- `stat` - stat information for the path
- `lstat` - lstat information for the path
- `as_dict` - get the dict view of the path

```python
# iterate over the directory contents
for item in path.iterdir():

    # ...

# find all paths matching a pattern
matching_paths = path.glob("*.txt")

# recursively find all paths matching a pattern
matching_paths = path.rglob("*.txt")

# get the path relative to another path
relative_path = path.relative_to(other_path)

# get the path with a different name
new_path = path.with_new_last("new_name.txt")
```


### Root Detection

`SKPath` objects attempt to automatically detect your project root and use it to normalize paths.

- Gets rid of issues where 2 people have the same project in different locations

- Gets rid of cross-platform file path issues, as the project itself won't change just because of a different operating system.

If the file path given is outside of the project root, `SKPath.np` will be `None`. However, all `SKPaths` will still have their absolute path, `SKPath.ap`.

(this is a dropdown section)
#### Project Root Indicators

Required Project Files

- License: `LICENSE`, `LICENSE.txt`, `license`, etc.
- README: `README`, `README.md`, `readme.txt`, etc.
- Requirements: `requirements.txt`, `requirements.pip`, etc.

Strong Indicators

These help the algorithm determine the project root more confidently.

- Python setup files: `setup.py`, `setup.cfg`, `pyproject.toml`
- Configuration files: `tox.ini`, `.gitignore`, `.dockerignore`
- Environment files: `.env`, `.env.local`, etc.
- Package initializer: `__init__.py`

(end of dropdown)

#### Set Project Root

You have a couple of ways to manually set the project root.

Functions

- `set_custom_root(path)` - set the project root to a custom path instead of automatically detecting it
- `clear_custom_root()` - clear the custom project root
- `get_custom_root()` - get the custom project root

```python
from suitkaise import skpath

skpath.set_custom_root("Documents/projects/myproject")

current_root = skpath.get_custom_root()

skpath.clear_custom_root()
```

Context Manager

```python
from suitkaise import skpath

with skpath.CustomRoot("Documents/projects/myproject"):

    # normalizes to given custom root
    path = SKPath("feature1/file.txt")
```

### `AnyPath` Type

The `AnyPath` type is a union of `str`, `Path`, and `SKPath`. You can use this type to maintain clear code and type safety.


## `@autopath` Decorator

Converts path parameters based on type annotations.

```python
from suitkaise.skpath import autopath, AnyPath, SKPath

# automatically convert Paths and strings to SKPaths
@autopath()
def path_pvp(path1: AnyPath, path2: AnyPath):

    # guaranteed to work now
    id1 = path1.id()
    id2 = path2.id()

    return id1 > id2

# also works with iterables of valid types
@autopath()
def path_royale(paths: list[AnyPath]):

    # guaranteed to work now
    ids = [path.id() for path in paths]

    winning_path = SKPath(sorted(ids)[-1])
    return winning_path
```

```python
# automatically convert SKPaths and strings to Paths
@autopath()
def i_like_pathlib(pathlib_path: Path):

    # if SKPaths or strings are passed in, they are converted to Path objects
    return pathlib_path.ap
```

```python
# convert SKPaths and Paths to strings
@autopath()
def i_like_strings(string_path: str):
    return str(path)
```

NOTE:`@autopath` not will normalize separators to `/` if a user passes in a string to a parameter only accepting strings.

### `use_caller`

If `use_caller` is `True`, parameters that accept `SKPath` or `Path` will use the caller's file path if no value was provided.

This occurs before the parameter's default value is used.

```python
from suitkaise.skpath import autopath, AnyPath

@autopath(use_caller=True)
def process_file(path: AnyPath):

    # path will never be None because of use_caller
    # all paths will be converted to SKPaths

# uses file that called this function
process_file() 

# uses given file and converts to SKPath
process_file("myproject/feature1/file.txt") 
```

```python
from suitkaise.skpath import autopath, AnyPath

@autopath() # use_caller=False
def process_file(path: AnyPath):

    # path could be None if no value was provided

# path will be None
process_file() 

# uses given file and converts to SKPath
process_file("myproject/feature1/file.txt") 
```

### `debug`

If `debug` is `True`, `@autopath` will output a message when a conversion is made.

```python
from suitkaise.skpath import autopath, AnyPath

@autopath(debug=True)
def process_file(path: AnyPath):
    return path.id()
```

For example, if a string got converted to a SKPath, it would output:
`"Converted str to SKPath: myproject/feature1/file.txt"`

## Functions

### `get_project_root()`

Arguments:
- `expected_name`: Expected project root name. If provided, the detected root must match this name.

Returns:
- `SKPath` object pointing to project root.

Raises:
- `PathDetectionError`: If project root detection fails.


Get the project root.

1. Checks if there is a custom root set.

2. If not 1, attempts to automatically detect the project root using the project root indicators. If the expected name is provided and doesn't match, move to step 3.

3. If not 1 or 2, raises a `PathDetectionError`.

```python
from suitkaise import skpath

root = skpath.get_project_root()
```

You can also get the project root like this:
```python
from suitkaise.skpath import SKPath

root = SKPath().root
```

### `get_caller_path()`

Returns:
- `SKPath` object pointing to the caller's file.

Raises:
- `PathDetectionError`: If caller detection fails.

Get the path of the file that called the current function.

```python
from suitkaise import skpath

caller = skpath.get_caller_path()
```

You can also get the caller path like this:
```python
from suitkaise.skpath import SKPath

caller = SKPath()
```

### `get_module_path()`

Arguments:
- `obj`: Object to inspect, module name string, or module object

Returns:
- `SKPath` object pointing to the module file, or `None` if not found

Raises:
- `ImportError`: If `obj` is a module name string that cannot be imported

Get the path of the module that the given object is defined in.

```python
from suitkaise import skpath

path = skpath.get_module_path(UnknownObject)
```

### `get_current_dir()`

Returns:
- `SKPath` object pointing to the current directory.

Get the directory of the current calling file.

```python
from suitkaise import skpath

path = skpath.get_current_dir()
```

You can also get the current directory like this:
```python
from suitkaise.skpath import SKPath

path = SKPath().parent
```

### `get_cwd()`

Returns:
- `SKPath` object pointing to the current working directory.

Get the current working directory.

```python
from suitkaise import skpath

path = skpath.get_cwd()
```

### `get_id()`

Arguments:
- `path`: Path to generate ID for
- `length`: Length of the hash to return (1-32, default 32)

Returns:
- Reproducible string ID for the path

Get the ID of a path. Reproducible across program runs and platforms.

```python
from suitkaise import skpath

id = skpath.get_id(path="myproject/feature1/file.txt", length=8)
```

You can also get the ID like this:
```python
from suitkaise.skpath import SKPath

id = SKPath().id(8)
```

### `get_project_paths()`

Arguments:
- `root`: Custom root directory (defaults to current project root)
- `exclude`: Paths to exclude from results.
- `as_strings`: Return string paths instead of `SKPath` objects (memory efficiency)
- `use_ignore_files`: Respect .*ignore files (default True)

Returns:
- List of paths in the project (`SKPath`s or strings based on `as_strings`)

Raises:
- `PathDetectionError`: If something goes wrong getting the project root.

Get all paths in the project as a list. 

This also can automatically ignore all paths that are in `.*ignore` files without requiring you to exclude them yourself.

```python
from suitkaise import skpath

# get all paths (use_ignore_files=True, auto detected root)
paths = skpath.get_project_paths()


# get all paths as strings
paths = skpath.get_project_paths(as_strings=True)


# exclude some paths
unwanted_paths = [
    "this/one/path/i/dont/want", 
    "another/path/i/dont/want"
    ]
paths = skpath.get_project_paths(exclude=unwanted_paths)

# use a custom root to start from a subdirectory
paths = skpath.get_project_paths(root="myproject/feature1")
```



