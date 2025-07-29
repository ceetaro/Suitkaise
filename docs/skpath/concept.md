# SKPath Concept

## Overview

skpath provides easy, intuitive path operations that ensure good developer habits and make paths easier to work with. It's designed as a foundational gateway module that provides immediate utility while integrating seamlessly with other SK modules.

## Core Philosophy

SKPath is a special path object that maintains both absolute and normalized paths, providing the best of both worlds for cross-platform compatibility and project organization.

## SKPath Object Structure

SKPath is a special path object that is a dict of 2 paths:
```python
an_skpath = {
    "ap": "an/absolute/system/path",
    "np": "a/normalized/path/up_to_your_project_root"
}
```

## Key Features

- **Dual-path architecture**: Absolute + normalized path in one object
- **Automatic project root detection**: Uses sophisticated indicator-based algorithm
- **String compatibility**: `str(skpath)` returns absolute path for standard library compatibility
- **Cross-module integration**: All SK modules accept SKPath objects seamlessly
- **Zero-argument initialization**: `SKPath()` automatically detects caller's file

## Project Root Detection

`get_project_root` requires you to have necessary files in your project root to safely recognize it.

### Essential Project Files (Necessary)
Your project should have these files in the root directory:
- **License file**: LICENSE, LICENSE.txt, license, etc.
- **README file**: README, README.md, readme.txt, etc.
- **Requirements file**: requirements.txt, requirements.pip, etc.

### Strong Project Indicators
These files significantly increase confidence that a directory is a project root:
- **Python setup files**: setup.py, setup.cfg, pyproject.toml
- **Configuration files**: tox.ini, .gitignore, .dockerignore
- **Environment files**: .env, .env.local, etc.
- **Package initializer**: __init__.py

### Expected Directory Structure
The algorithm looks for these common project directories:

**Strong indicators:**
- `app/` or `apps/` - Application code
- `data/` or `datasets/` - Data files
- `docs/` or `documentation/` - Documentation
- `test/` or `tests/` - Test files

**Regular indicators:**
- `.git/` - Git repository
- `src/` or `source/` - Source code
- `examples/` - Example code
- `venv/` or `env/` - Virtual environments

## AutoPath Decorator

The autopath decorator automatically converts valid paths to SKPaths before running a function. Any parameter with "path" in the name will attempt to convert a valid path to an SKPath object.

AutoPath will detect if the path parameter accepts SKPaths -- if not, automatically converts SKPaths to string form!

## Integration Benefits

- **Cross-module compatibility**: All SK modules accept SKPath objects
- **Automatic path normalization**: Consistent path handling across the ecosystem
- **Project structure awareness**: Paths are always relative to detected project root
- **Developer experience**: Zero-configuration magic that "just works"

## Examples

### Basic Usage

```python
from suitkaise import skpath

# get the project root (expects python project necessities)
root = skpath.get_project_root()
# optionally add intended name of project root you'd like to find
# doing this will return None unless a valid root WITH this name is found
root = skpath.get_project_root("Suitkaise")

# create a path object containing both absolute and normalized path
# normalized path: only up to your project root
my_skpath = skpath.SKPath("a/path/goes/here")

# create an SKPath object for the current path with simple initialization
caller_skpath = skpath.SKPath()

# get the SKPath of the file that executed this code with a function
caller_skpath = skpath.get_caller_path()

# get the current directory path that executed this code
current = skpath.get_current_dir()
```

### Path Comparison and Operations

```python
# check if 2 paths are equal with equalpaths
path1 = skpath.get_caller_path()
path2 = skpath.SKPath("a/path/goes/here")

if equalpaths(path1, path2):
    do_something()

# generate a reproducible ID for your path (shorter identification than whole path)
my_path_id = path_id(my_path)
my_path_shortened_id = path_idshort(my_path)
```

### Project Structure Operations

```python
# get all project paths
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want")
# as abspath strings instead of skpaths
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want", as_str=True)
# including all .gitignore and .skignore paths
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want", dont_ignore=True)

# get a nested dictionary representing your project structure
proj_structure = skpath.get_project_structure()
# or a printable, formatted version: (custom_root allows you to only format some of the structure)
fmted_structure = skpath.get_formatted_project_structure(custom_root=None)
```

### AutoPath Decorator Examples

```python
from suitkaise import autopath

# standard autopath functionality
@autopath()
def process_file(path: str | SKPath = None):
    print(f"Processing {path}...")
    # do some processing of the file...

# later...

# relative path will convert to an SKPath automatically before being used
process_file("my/relative/path")

# standard autopath functionality, but function doesn't accept SKPath type!
@autopath()
def process_file(path: str = None): # only accepts strings!
    print(f"Processing {path}...")
    # do some processing of the file...

# later...

# relative path will convert to an absolute path string instead!
process_file("my/relative/path")
```

### Advanced AutoPath Features

```python
# using autofill
@autopath(autofill=True)
def process_files(path: str | SKPath = None):
    print(f"Processing {path}...")
    # do some processing of the file...

# later...

# relative path will convert to an SKPath automatically before being used
# if no path is given, uses caller file path (current file executing this code)
process_file()

# using defaultpath
@autopath(defaultpath="my/default/path")
def save_to_file(data: Any = None, path: str | SKPath = None) -> bool:
    # save data to file with given path...

# later...

# user forgets to add path, or just wants to save all data to same file
saved_to_file = save_to_file(data) # -> still saves to my/default/path!

# NOTE: autofill WILL be ignored if defaultpath is used and has a valid path value!
# autofill WILL be ignored below!
@autopath(autofill=True, defaultpath="a/valid/path/or/skpath_dict")
```