# SKPath Examples

## Basic Usage

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

## Path Comparison and Operations

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

## Project Structure Operations

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

## AutoPath Decorator Examples

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

## Advanced AutoPath Features

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