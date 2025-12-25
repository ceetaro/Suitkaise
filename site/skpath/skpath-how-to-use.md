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
```python
path = SKPath("file.txt") # DON'T DO THIS!
```
(this is a dropdown section)
### `SKPath` Properties and Methods

- `ap` - absolute path
- `np` - path normalized to project root

Unique to `SKPath`

- `id` - reversible base64url encoded ID (can be used to reconstruct the path)
- `root` - project root

`pathlib` Compatible

- `name` - complete filename (`"file.txt"` -> `"file.txt"`)
- `stem` - filename without suffix (`"file.txt"` -> `"file"`)
- `suffix` - suffix of last part of path (`"file.txt"` -> `".txt"`)
- `suffixes` - list of all suffixes (`"file.tar.gz"` -> `[".tar", ".gz"]`)
- `parent` - parent directory of the path
- `parts` - path parts as a tuple
- `exists` - whether the path exists
- `is_file` - whether the path is a file
- `is_dir` - whether the path is a directory


```python
path = SKPath("myproject/feature1")

path_as_string = str(path)

path_as_repr = repr(path)

# __hash__ method uses md5 instead of SKPath.id's encoding
path_hash = hash(path)

# works with Paths and strings as well
if path == other_path:

    # ...

# truediv to join paths
child_path = path / "content" / "file.txt"

# os.fspath()
with open(path, "r") as f:

    # ...
```

`__hash__` method creates a md5 hash of the path (1-way hash)

`id` encodes the path to a string, which can be decoded.

Uncommon

- `is_symlink` - whether the path is a symlink

(this is a dropdown section for symlinks)
#### What is a symlink?

A *symlink* (symbolic link) is like a shortcut or alias to another file or folder.

Think of it like a sticky note that says "the real file is over there →". When you open a symlink, your computer automatically follows it to the real file.

You might have a symlink at `~/Desktop/project` that points to `/Users/me/Documents/work/important-project`. Opening either path opens the same folder.

Sometimes you need to know if you're looking at the real file or just a shortcut. The `is_symlink` property tells you this. The `stat` and `lstat` properties behave differently with symlinks (see below).

(end of dropdown section for symlinks)

- `stat` - stat information for the path
- `lstat` - lstat information for the path

(this is a dropdown section for stat and lstat)
#### `stat` and `lstat`

`stat` gives you detailed information about a file: its size, when it was created, when it was last modified, who owns it, and its permissions.

```python
info = path.stat
print(info.st_size)    # File size in bytes
print(info.st_mtime)   # Last modified time (Unix timestamp)
print(info.st_ctime)   # Creation time (Unix timestamp)
print(info.st_mode)    # Permissions (octal)
print(info.st_uid)     # Owner ID
print(info.st_gid)     # Group ID
print(info.st_dev)     # Device ID
print(info.st_ino)     # Inode number
print(info.st_nlink)   # Number of links
```

- `stat` follows symlinks — gives you info about the *target* file
- `lstat` doesn't follow symlinks — gives you info about the *symlink itself*

**Example**: If `shortcut.txt` is a symlink pointing to a 1MB file:
- `shortcut.stat.st_size` → 1,000,000 (size of the target file)
- `shortcut.lstat.st_size` → 50 (size of the symlink itself)

For regular files (not symlinks), `stat` and `lstat` return the same thing.

(end of dropdown section for stat and lstat)

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

# get the path with a different name (pathlib compatible)
new_path = path.with_name("new_name.txt")
new_path = path.with_stem("new_name")
new_path = path.with_suffix(".md")

# create directory
path.mkdir(parents=True, exist_ok=True)

# create/touch file
path.touch(exist_ok=True)
```

(this is a dropdown section for glob and rglob)
#### `glob` and `rglob`

`glob` finds files matching a pattern in a directory.

Think of it like a search with wildcards:
- `*` matches anything (except path separators)
- `?` matches any single character
- `[abc]` matches any character in the brackets

```python
folder = SKPath("myproject/data")

# Find all .txt files in the data folder
for file in folder.glob("*.txt"):
    print(file.name)

# Find all files starting with "report"
for file in folder.glob("report*"):
    print(file.name)
```

`rglob` does the same thing, but *recursively* — it searches the folder AND all subfolders.

```python
folder = SKPath("myproject")

# Find ALL .py files anywhere in the project
for file in folder.rglob("*.py"):
    print(file.np)
```

The "r" stands for "recursive". Use `glob` for the current folder only, `rglob` for everything underneath.

(end of dropdown section for glob and rglob)

(this is a dropdown section for relative_to)
#### `relative_to`

`relative_to` gives you the path from one location to another.

Imagine you're in `/Users/me/projects` and want to describe how to get to `/Users/me/projects/app/src/main.py`. The relative path would be `app/src/main.py`.

```python
base = SKPath("/Users/me/projects")
file = SKPath("/Users/me/projects/app/src/main.py")

relative = file.relative_to(base)
print(relative.ap)  # "app/src/main.py"
```

- Display shorter, cleaner paths
- Create portable paths that work on different machines
- Find the "distance" between two paths

NOTE: The file must actually be inside the base path. If you try `file.relative_to(unrelated_folder)`, it raises a `ValueError`.

(end of dropdown section for relative_to)

(this is a dropdown section for mkdir and touch)
#### `mkdir` and `touch`

`mkdir` creates a directory (folder).

```python
folder = SKPath("myproject/new_folder")
folder.mkdir()  # Creates the folder
```

- `parents=True` — also creates parent folders if they don't exist
- `exist_ok=True` — don't raise an error if folder already exists

```python
# Create nested folders, don't fail if they exist
deep_folder = SKPath("myproject/a/b/c/d")
deep_folder.mkdir(parents=True, exist_ok=True)
```

`touch`creates an empty file, or updates its "last modified" time if it exists.

```python
file = SKPath("myproject/new_file.txt")
file.touch()  # Creates empty file (or updates timestamp)
```

The name "touch" comes from the idea of "touching" a file to update its timestamp, like leaving fingerprints showing you were there.

(end of dropdown section for mkdir and touch)

### Root Detection

`SKPath` objects attempt to automatically detect your project root and use it to normalize paths.

- Gets rid of issues where 2 people have the same project in different locations

- Gets rid of cross-platform file path issues, as the project itself won't change just because of a different operating system.

If the file path given is outside of the project root, `SKPath.np` will be an empty string `""`. However, all `SKPaths` will still have their absolute path, `SKPath.ap`.

1. Uses custom root if set via `set_custom_root()`
2. Uses `setup.sk` file if found walking up directories
3. Uses standard detection (see below)

Definitive Indicators

- `setup.sk`
- `setup.py`
- `setup.cfg`
- `pyproject.toml`

Strong Indicators

- `.gitignore`
- License: `LICENSE`, `LICENSE.txt`, `license`, ...
- README: `README`, `README.md`, `readme.txt`, ...
- Requirements: `requirements.txt`, `requirements.pip`, ...

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

##### Context Manager

```python
from suitkaise import skpath

with skpath.CustomRoot("Documents/projects/myproject"):

    # normalizes to given custom root
    path = SKPath("feature1/file.txt")
```

### Creating an SKPath from an ID

```python
from suitkaise import skpath

id = # the path's id from a previous operation

path = SKPath(id)
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

    # guaranteed to work now - path.id is a property
    id1 = path1.id
    id2 = path2.id

    return id1 > id2

# also works with iterables of valid types
@autopath()
def path_royale(paths: list[AnyPath]):

    # guaranteed to work now - path.id is a property
    ids = [path.id for path in paths]

    winning_path = SKPath(sorted(ids)[-1])
    return winning_path
```

```python
# automatically convert SKPaths and strings to Paths
@autopath()
def i_like_pathlib(pathlib_path: Path):

    # if SKPaths or strings are passed in, they are converted to Path objects
    return pathlib_path.name  # use standard Path methods
```

```python
# convert SKPaths and Paths to strings
@autopath()
def i_like_strings(string_path: str):
    # SKPaths and Paths are converted to strings (absolute path)
    return string_path.upper()  # it's a regular string now
```

NOTE: `@autopath` will NOT normalize separators to `/` if a user passes in a string to a parameter annotated as `str`. Normalization only occurs when converting to `SKPath`.

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
    return path.id
```

For example, if a string got converted to a SKPath, it would output:
`"@autopath: Converted path: str → SKPath"`

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

path = SKPath(path="...").parent
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

Returns:
- Base64url encoded ID string (reversible - can be used to reconstruct the path)

Get the reversible ID of a path. The ID can be used to reconstruct the SKPath later.

```python
from suitkaise import skpath

path_id = skpath.get_id(path="myproject/feature1/file.txt")

# Later, reconstruct the path from the ID
path = skpath.SKPath(path_id)
```

You can also get the ID like this:
```python
from suitkaise.skpath import SKPath

path_id = SKPath(path="...").id  # id is a property, not a method
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


# exclude some paths (list of AnyPaths)
unwanted_paths = [
    "this/one/path/i/dont/want", 
    Path("another/path/i/dont/want"),
    SKPath("yet/another/path/i/dont/want"),
    ]
paths = skpath.get_project_paths(exclude=unwanted_paths)

# use a custom root to start from a subdirectory
paths = skpath.get_project_paths(root="myproject/feature1")
```

### `get_project_structure()`

Arguments:
- `root`: Custom root directory (defaults to current project root) (`AnyPath`)
- `exclude`: Paths to exclude from results. (`AnyPath` or list of `AnyPaths`)
- `use_ignore_files`: Respect .*ignore files (default `True`)

Returns:
- Nested dictionary representing the project structure.

Raises:
- `PathDetectionError`: If something goes wrong getting the project root.

Provides a hierarchical representation of your project structure, in dictionary form.

```python
from suitkaise import skpath

structure = skpath.get_project_structure()
```

```python
{
    "myproject": {
        "feature1": {
            "file.txt": {},
            "another_file.txt": {}
        }
    }
}
```

### `get_formatted_project_tree()`

Arguments:
- `root`: Custom root directory (defaults to current project root) (`AnyPath`)
- `exclude`: Paths to exclude from results. (`AnyPath` or list of `AnyPaths`)
- `use_ignore_files`: Respect .*ignore files (default `True`)
- `depth`: Maximum depth of the tree to format (default 3) (`int`)
- `include_files`: Include files in the tree (default `True`)

Returns:
- String representing the project tree.

Raises:
- `PathDetectionError`: If something goes wrong getting the project root.

Returns a readable, formatted string using `│`, `├─`, and `└─` characters to create a tree-like visual hierarchy.

```python
from suitkaise import skpath

tree = skpath.get_formatted_project_tree()
print(tree)
```

root_directory/
├── __pycache__/
│   └── main.cpython-39.pyc
├── docs/
│   ├── api/
│   ├── development/
│   └── user_guide/
└── src/
    ├── __init__.py
    ├── main.py
    └── utils/


