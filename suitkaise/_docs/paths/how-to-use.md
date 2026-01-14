# How to use `skpath`

`skpath` makes file paths much easier to work with.

## `Skpath` class

Special path object. Automatically detects your project root and uses it to normalize paths.

- `Skpath.ap` - absolute path. All slashes are streamlined to `/` for cross-platform compatibility.

"Users/john/Documents/projects/myproject/feature1/file.txt"

- `Skpath.rp` - relative path, relative to project root

"myproject/feature1/file.txt"

```python
from suitkaise.paths import Skpath

# create Skpath object with caller file path
path = Skpath()

# create Skpath object with Path object
path = Skpath(Path("feature1/file.txt"))

# and with string object
path = Skpath("feature1/file.txt")
```

Recommend not relying on just on file name, add at least the directory too.
```python
path = Skpath("file.txt") # DON'T DO THIS!
```


### `Skpath` Properties and Methods

- `ap` - absolute path
- `rp` - path relative to project root

Unique to `Skpath`

- `id` - reversible base64url encoded ID (can be used to reconstruct the path)
- `root` - project root as `Skpath` object
- `root_str` - project root as string (normalized separators)
- `root_path` - project root as `Path` object
- `platform` - absolute path with OS-native separators (backslashes on Windows)

Pathlib Compatible

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
path = Skpath("myproject/feature1")

path_as_string = str(path)

path_as_repr = repr(path)

# __hash__ method uses md5 instead of Skpath.id's encoding
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

# get the path with a different name (pathlib compatible)
new_path = path.with_name("new_name.txt")
new_path = path.with_stem("new_name")
new_path = path.with_suffix(".md")

# create directory
path.mkdir(parents=True, exist_ok=True)

# create/touch file
path.touch(exist_ok=True)
```


### Root Detection

`Skpath` objects attempt to automatically detect your project root and use it to normalize paths.

- gets rid of issues where 2 people have the same project in different locations

- gets rid of cross-platform file path issues, as the project itself won't change just because of a different operating system.

If the file path given is outside of the project root, `Skpath.rp` will be an empty string `""`. However, all `Skpaths` will still have their absolute path, `Skpath.ap`.

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
- license: `LICENSE`, `LICENSE.txt`, `license`, ...
- README: `README`, `README.md`, `readme.txt`, ...
- requirements: `requirements.txt`, `requirements.pip`, ...

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
    path = Skpath("feature1/file.txt")
```

### Creating a Skpath from an ID

```python
from suitkaise import skpath

id = # the path's id from a previous operation

path = Skpath(id)
```


### `AnyPath` Type

The `AnyPath` type is a union of `str`, `Path`, and `Skpath`. You can use this type to maintain clear code and type safety.


## `@autopath` Decorator

Automatically converts paths to the types that a function expects.

- paths get normalized through `Skpath` first
- converts before passing, avoiding `TypeErrors`
- works with iterables
- `Skpath`, `Path`, and `str` can be used interchangeably

```python
from suitkaise.paths import autopath, AnyPath, Skpath

# automatically convert Paths and strings to Skpaths
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

    winning_path = Skpath(sorted(ids)[-1])
    return winning_path
```

```python
# automatically convert Skpaths and strings to Paths
@autopath()
def i_like_pathlib(pathlib_path: Path):

    # if Skpaths or strings are passed in, they are converted to Path objects
    return pathlib_path.name  # use standard Path methods
```

```python
# convert Skpaths and Paths to strings
@autopath()
def i_like_strings(string_path: str):

    # All inputs are normalized: "./data\\file.txt" → "/abs/path/data/file.txt"

    return string_path.upper()  # it's a regular string now
```

### `only`

Tells `@autopath` to only focus on given parameters. 

Use this for performance when you have `str` or `list[str]` parameters that aren't actually file paths.

When not using `only`, all parameters accepting `Skpath`, `Path`, or `str` will be normalized and converted.

When using `only`, ONLY the parameters specified will do this.

```python
from suitkaise.paths import autopath

@autopath(only="file_path")
def process_with_data(file_path: str, names: list[str], ids: list[str]):

    # Only file_path is normalized
    # names and ids are passed through unchanged (much faster!)
    return file_path
```

```python
# Multiple parameters
@autopath(only=["input_path", "output_path"])
def copy_file(input_path: str, output_path: str, metadata: list[str]):

    # input_path and output_path are normalized
    # metadata is left unchanged
    ...
```

### `use_caller`

If `use_caller` is `True`, parameters that accept `Skpath` or `Path` will use the caller's file path if no value was provided.

This occurs before the parameter's default value is used.

```python
from suitkaise.paths import autopath, AnyPath

@autopath(use_caller=True)
def process_file(path: AnyPath):

    # path will never be None because of use_caller
    # all paths will be converted to Skpaths

# uses file that called this function
process_file() 

# uses given file and converts to Skpath
process_file("myproject/feature1/file.txt") 
```

```python
from suitkaise.paths import autopath, AnyPath

@autopath() # use_caller=False
def process_file(path: AnyPath):

    # path could be None if no value was provided

# path will be None
process_file() 

# uses given file and converts to Skpath
process_file("myproject/feature1/file.txt") 
```

### `debug`

If `debug` is `True`, `@autopath` will output a message when a conversion is made or a path string is normalized.

```python
from suitkaise.paths import autopath, AnyPath

@autopath(debug=True)
def process_file(path: AnyPath):
    return path.id
```

Output when a string got converted to a Skpath:
`"@autopath: Converted path: str → Skpath"`

Output when a string was normalized:
`"@autopath: Normalized path: './file.txt' → '/abs/path/file.txt'"`

## Functions

### `get_project_root()`

Arguments:
- `expected_name`: Expected project root name. If provided, the detected root must match this name.

Returns:
- `Skpath` object pointing to project root.

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
from suitkaise.paths import Skpath

root = Skpath().root
```

### `get_caller_path()`

Returns:
- `Skpath` object pointing to the caller's file.

Raises:
- `PathDetectionError`: If caller detection fails.

Get the path of the file that called the current function.

```python
from suitkaise import skpath

caller = skpath.get_caller_path()
```

You can also get the caller path like this:
```python
from suitkaise.paths import Skpath

caller = Skpath()
```

### `get_module_path()`

Arguments:
- `obj`: Object to inspect, module name string, or module object

Returns:
- `Skpath` object pointing to the module file, or `None` if not found

Raises:
- `ImportError`: If `obj` is a module name string that cannot be imported

Get the path of the module that the given object is defined in.

```python
from suitkaise import skpath

path = skpath.get_module_path(UnknownObject)
```

### `get_current_dir()`

Returns:
- `Skpath` object pointing to the current directory.

Get the directory of the current calling file.

```python
from suitkaise import skpath

path = skpath.get_current_dir()
```

You can also get the current directory like this:
```python
from suitkaise.paths import Skpath

path = Skpath(path="...").parent
```

### `get_cwd()`

Returns:
- `Skpath` object pointing to the current working directory.

Get the current working directory.

```python
from suitkaise import skpath

path = skpath.get_cwd()
```

### `get_id()`

Arguments:
- `path`: Path to generate ID for

Returns:
- base64url encoded ID string (reversible - can be used to reconstruct the path)

Get the reversible ID of a path. The ID can be used to reconstruct the Skpath later.

```python
from suitkaise import skpath

path_id = skpath.get_id(path="myproject/feature1/file.txt")

# Later, reconstruct the path from the ID
path = skpath.Skpath(path_id)
```

You can also get the ID like this:
```python
from suitkaise.paths import Skpath

path_id = Skpath(path="...").id  # id is a property, not a method
```

### `get_project_paths()`

Arguments:
- `root`: Custom root directory (defaults to current project root)
- `exclude`: Paths to exclude from results.
- `as_strings`: Return string paths instead of `Skpath` objects (memory efficiency)
- `use_ignore_files`: Respect .*ignore files (default True)

Returns:
- list of paths in the project (`Skpath`s or strings based on `as_strings`)

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
    Skpath("yet/another/path/i/dont/want"),
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
- nested dictionary representing the project structure.

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
- string representing the project tree.

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

---

## Path Validation Utilities

### `is_valid_filename()`

Check if a filename is valid across common operating systems.

```python
from suitkaise.paths import is_valid_filename

is_valid_filename("my_file.txt")     # True
is_valid_filename("file<name>.txt")  # False (contains <, >)
is_valid_filename("CON")             # False (Windows reserved)
is_valid_filename("")                # False (empty)
```

Checks for:
- empty or whitespace-only names
- invalid characters (`<>:"/\|?*`)
- Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
- names ending with space or period

### `streamline_path()`

Sanitize a path or filename by removing/replacing invalid characters.

```python
from suitkaise.paths import streamline_path

# Basic cleanup
streamline_path("My File<1>.txt")
# "My File_1_.txt"

# Lowercase and limit length
streamline_path("My Long Filename.txt", max_length=10, lowercase=True)
# "my long fi"

# Replace invalid chars with custom character
streamline_path("file:name.txt", replacement_char="-")
# "file-name.txt"

# ASCII only (no unicode)
streamline_path("файл.txt", allow_unicode=False)
# "____.txt"
```

Arguments:
- `path`: The path or filename to sanitize
- `max_length`: Maximum length to truncate to (None = no limit)
- `replacement_char`: Character to replace invalid chars with (default "_")
- `lowercase`: Convert to lowercase (default False)
- `strip_whitespace`: Strip leading/trailing whitespace (default True)
- `allow_unicode`: Allow unicode characters (default True)
