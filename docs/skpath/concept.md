# SKPath Concept

## Table of Contents

1. [Overview](#1-overview)
2. [Core Philosophy](#2-core-philosophy)
3. [SKPath Class and Structure](#3-skpath-class-and-structure)
4. [Key Features](#4-key-features)
5. [Project Root Detection](#5-project-root-detection)
6. [AutoPath Decorator](#6-autopath-decorator)
7. [Integration Benefits](#7-integration-benefits)
8. [Examples](#8-examples)
9. [Factory Functions](#9-factory-functions)
10. [Additional Functions](#10-additional-functions)
11. [Importing skpath](#11-importing-skpath)
12. [Real Usage Examples](#12-real-usage-examples-placeholder)

## 1. Overview

skpath provides easy, intuitive path operations that ensure good developer habits and make paths easier to work with. It's designed as a foundational gateway module that provides immediate utility outside of the SK umbrella while integrating seamlessly with other SK modules.

## 2. Core Philosophy

SKPath is a special path object that maintains both absolute and normalized paths, providing the best of both worlds for cross-platform compatibility and project organization.

The skpath module uses this object, but is also compatible with pathlib.Path objects and path strings.

This was designed to get rid of a lot of headache when it comes to path discovery, manipulation, comparison, and visualization.

Developers who set up a project correctly should find that `get_project_root` should automatically detect their project root without any hassle, as long as skpath was imported under that root.

There are also simple, no arguments needed functions to:
- get caller file path, or its directory
- get the current working directory
- compare 2 path objects with one simple function
- get all of your project paths
    - looks at your .gitignore file and ignores its content automatically
    - can return in a list (for checking valid paths), a dict (for structure and data organization), or even a printable tree
    - can use custom root to only get paths from a certain directory
- and a decorator that will automatically convert relative paths to SKPaths, or strings if SKPaths aren't accepted.

## 3. SKPath Class and Structure

SKPath is a class with properties that expose two path views:

- `ap`: Absolute filesystem path (string), with separators normalized (all /)
- `np`: Normalized path relative to your project root (string)

To access them, simply do:

```python
from suitkaise.skpath import SKPath

# no args automatically gets caller file path
path = SKPath()

abspath = path.ap
normpath = path.np

# or...
abspath = SKPath().ap
normpath = SKPath().np
```

SKPath objects have a bunch of properties that make them easy to work with:

```python
from suitkaise.skpath import SKPath

path = SKPath("a/path/goes/here")

# get the absolute path
abs_path = path.ap

# get the normalized path
norm_path = path.np

# get the root
root = path.root

# get the final component of the path
file_name = path.name

# get the parent directory
parent_dir = path.parent

# get the final component without the suffix
file_stem = path.stem

# get the suffix
file_suffix = path.suffix

# get all suffixes
file_suffixes = path.suffixes

# get the path parts as a tuple
path_parts = path.parts

# check if the path exists
path_exists = path.exists()

# check if the path is a file
is_file = path.is_file()

# check if the path is a directory
is_dir = path.is_dir()

# check if the path is absolute
is_absolute = path.is_absolute()

# check if the path is a symlink
is_symlink = path.is_symlink()

# get the stat information for the path
stat = path.stat()

# get the lstat information for the path
lstat = path.lstat()

# iterate over the directory contents
for item in path.iterdir():
    print(item)

# find all paths matching a pattern
matching_paths = path.glob("*.txt")

# recursively find all paths matching a pattern
matching_paths = path.rglob("*.txt")

# get the relative path to another path
relative_path = path.relative_to(other_path)

# get the path with a different name
new_path = path.with_name("new_name.txt")

# get the path with only a different stem
new_path = path.with_stem("new_stem")

# get the path with only a different suffix
new_path = path.with_suffix(".txt")

# get the dict view of the path
path_dict = path.as_dict()

# get the path as a string
path_str = str(path)

# get the path as a repr string
path_repr = repr(path)

# check if the path is equal to another path
is_equal = path == other_path

# get a hash of the path
path_hash = hash(path)

# supports true division (path / "other/path")

# supports os.fspath()
```

## 4. Key Features

- **Dual-path architecture**: Absolute + normalized path in one object
- **Automatic project root detection**: Uses sophisticated indicator-based algorithm
- **String compatibility**: `str(skpath)` returns absolute path for standard library compatibility
- **Cross-module integration**: All SK modules accept SKPath objects seamlessly
- **Zero-argument initialization**: `SKPath()` automatically detects caller's file

## 5. Project Root Detection

`get_project_root` requires you to have necessary files in your project root to safely recognize it.

### Essential Project Files (Necessary)
For detection to work correctly, at least one of each of these is required:
- **License file**: LICENSE, LICENSE.txt, license, etc.
- **README file**: README, README.md, readme.txt, etc.
- **Requirements file**: requirements.txt, requirements.pip, etc.

These are standard project files. For quick scripts, there is an option to use a custom root.

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

## 6. AutoPath Decorator

The autopath decorator automatically converts valid paths to SKPaths before running a function. Any parameter with "path" in the name will attempt to convert a valid path to an SKPath object.

AutoPath will detect if the path parameter accepts SKPaths -- if not, automatically converts SKPaths to string form!

This is great for beginners, or developers that want to not have to worry about remembering to convert paths to SKPaths (less error prone). However, manual conversion is faster and more efficient.

Remember that `autopath` only converts params that are strings, Path objects, or SKPaths, and that have 'path' in the name.

### AutoPath Decorator Examples

```python
from suitkaise.skpath import autopath

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

# relative path will convert only to an absolute path string instead!
process_file("my/relative/path")
```

### Advanced AutoPath Features

```python
# using autofill
from suitkaise import skpath

@skpath.autopath(autofill=True)
def process_file(path: str | SKPath = None):
    print(f"Processing {path}...")
    # do some processing of the file...

# later...

# relative path will convert to an SKPath automatically before being used
process_file() # uses caller file path because we are autofilling

# using defaultpath
@skpath.autopath(defaultpath="my/default/path")
def save_to_file(data: Any = None, path: str | SKPath = None) -> bool:
    # save data to file with given path...

# later...

# user forgets to add path, or just wants to save all data to same file
saved_to_file = save_to_file(data) # -> still saves to my/default/path!

# NOTE: autofill WILL be ignored if defaultpath is used and has a valid path value!

# autofill WILL be ignored below!
@skpath.autopath(autofill=True, defaultpath="a/valid/path/or/skpath_dict")
```

## 7. Why using SKPath is great

- **Cross-module compatibility:** All SK modules accept SKPath objects

- **Cross-system comaptibility:** SKPath.np is the same whether you are running a project from Windows or Mac/Linux, allowing your team to use their preferred OS

- **Automatic path normalization:** Relative paths are a thing of the past. Every path contains its absolute and normalized data automatically, making comparisons and checks single lines of code.

- **Automatic root detection:** Project roots are automatically detected, allowing your programs to run smoothly regardless of what environment they are in. All root related functions can also take a custom root, allowing for finer control and better testing.

- **Developer experience:** Import, use single lines of code, and get rid of time and effort wasted on creating path handling boilerplate. Fast, easy, efficient.

- **AI friendly:** AI agents and chatbots don't have to worry about replicating complex path handling when working with code, they can just use it simply like you do.

## 8. Examples

### Basic Usage

```python
from suitkaise import skpath

# get the project root (expects python project necessities)
root = skpath.get_project_root()

# optionally, add intended name of project root you'd like to find
# doing this will return None unless a valid root WITH this name is found
root = skpath.get_project_root("Suitkaise")

# create a path object containing both absolute and normalized path
# normalized path: only up to your project root
my_skpath = skpath.SKPath("a/path/goes/here")
# or...
my_skpath = skpath.create("a/path/goes/here") # returns SKPath

# create an SKPath object for the current caller path with simple initialization
caller_skpath = skpath.SKPath()
# or...
caller_skpath = skpath.get_caller_path()

# get the current directory path that executed this code
current = skpath.get_current_dir()

# get the current working directory
cwd = skpath.get_cwd()
```

### Path Comparison and Other Operations

```python
# generate a reproducible ID for your path (shorter identification than whole path)
# same path will always generate same ID
my_path_id = skpath.path_id(my_path)


# check if 2 paths are equal with equalpaths
path1 = skpath.get_caller_path()
path2 = skpath.SKPath("a/path/goes/here")

if skpath.equalpaths(path1, path2):
    do_something()

else:
    # generate ID in short form (8 chars long)
    error_path_code = skpath.path_id_short()
    file_name = f"error_{error_path_code}.log" # ex. error_12345678.log
    with open(file_name, "a") as f:
        # if file is empty...
        if os.path.getsize(file_name) == 0:
            f.write(f"Path: {skpath.get_caller_path()}\n")
        f.write(f"Error: Initialization failed due to path mismatch: {path1} and {path2}\n")

    raise ValueError(f"Initialization failed due to path mismatch: {path1} and {path2}")
```

Note: `equalpaths` compares normalized project paths first and falls back to absolute path comparison when needed. 

Then, you can use the ID to organize your error logs by point of origin, without having extremely long file names.

### Project Structure Operations

```python
# get all project paths, except paths starting with this/one/path/i/dont/want
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want")

# as abspath strings instead of skpaths
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want", as_str=True)

# including all .gitignore, .dockerignore, and .skignore paths
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want", dont_ignore=True)

# get a nested dictionary representing your project structure
proj_structure = skpath.get_project_structure()

# or a printable, formatted tree: (custom_root allows you to start from subdirectories)
fmted_structure = skpath.get_formatted_project_tree(custom_root=None)
```

### Object tracing using `get_module_path`

```python
# in one file, "/path/to/my/file.py"

class MyClass:
    def __init__(self):
        self.name = "MyClass"
        self.favorite_number = 92
        self.a_cool_dict = {"a": 1, "b": 2, "c": 3}
        self.fail = False

        rint = random.randint(1, 10)
        if rint == 10:
            self.fail = True

    def __repr__(self):
        if self.fail:
            raise ValueError("Obligatory example failure")

# in another file, "/path/to/my/other/file.py"
try:
    my_class = MyClass()
    my_class.repr()

except Exception as e:
    print(f"Error: {e} caused by {my_class.__class__.__name__}")
    print(f"Path to class: {skpath.get_module_path(MyClass)}")
```

## 9. Factory Functions

```python
from suitkaise import skpath

# Create SKPath from an explicit path
sp = skpath.create("/path/to/my/file.txt")

# Create SKPath using the caller file as the anchor
sp_caller = skpath.create()

# Create SKPath with a custom project root override
sp_custom = skpath.create("/path/to/my/file.txt", custom_root="/path/to/project")
```

## 11. Importing skpath

Two supported import styles:
```python
from suitkaise import skpath               # recommended in examples
# or
from suitkaise.skpath import SKPath, autopath, get_project_root  # direct names from module
```

## 12. Real Usage Examples

### Beginner/Learning Projects

#### 1. Python Script That Reads a Text File
**Problem:** Script works in root folder but breaks when moved to organize code.
```python
from suitkaise import skpath

@skpath.autopath()
def analyze_data(file_path):
    with open(file_path) as f:  # autopath converts "data.txt" to SKPath automatically!
        content = f.read()
    return len(content.split('\n'))

# Always finds data.txt in project root, regardless of script location
file = "data.txt"
lines = analyze_data(file)
print(f"{file} has {lines} lines")
```

#### 2. Game Development - Loading Assets
**Problem:** Game assets break when code is reorganized into folders.
```python
from suitkaise import skpath
import pygame

class GameAssets:
    def __init__(self):
        self.sprite_path = skpath.SKPath("images")
        self.sound_path = skpath.SKPath("sounds")
        
    def load_sprite(self, sprite_name):
        sprite_path = skpath.SKPath(self.sprite_path / sprite_name)
        return pygame.image.load(sprite_path)  # autopath handles the conversion!
    
    def load_sound(self, sound_name):
        sound_path = skpath.SKPath(self.sound_path / sound_name)
        return pygame.mixer.Sound(sound_path)

# Usage - works from anywhere in project
assets = GameAssets()
player_sprite = assets.load_sprite("player.png")
jump_sound = assets.load_sound("jump.wav")

# find all sprites and sounds in the project
sprites = skpath.get_all_project_paths(custom_root=assets.sprite_path)
sounds = skpath.get_all_project_paths(custom_root=assets.sound_path)

core_sprites = [sprite for sprite in sprites if sprite.parts[-1].startswith("core")]
core_sounds = [sound for sound in sounds if sound.parts[-1].startswith("core")]

for sprite in core_sprites:
    sprite = assets.load_sprite(sprite)

for sound in core_sounds:
    sound = assets.load_sound(sound)
```

#### 3. Personal Automation Scripts
**Problem:** Log files and outputs end up scattered across filesystem.
```python
from suitkaise import skpath
import shutil
from datetime import datetime

@skpath.autopath()
def backup_photos(source_dir: str = "~/Pictures", backup_path=None, log_path=None):
    # autopath converts these to SKPaths automatically!
    if not backup_path:
        backup_path = skpath.SKPath("backups/photos")
    if not log_path:
        log_path = skpath.SKPath("backup.log")
    
    # Backup the photos
    shutil.copytree(source_dir, backup_path)
    
    # Log the backup
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"{timestamp}: Backup completed from {source_dir}\n")

backup_photos()  # Always works, always saves to same location
```

#### 4. School/Learning Projects
**Problem:** Tutorial projects break when files are organized into folders.
```python
from suitkaise import skpath
import json
import pandas as pd

class StudentGrades:
    def load_students(self):
        # Always finds files relative to project root
        with open(skpath.SKPath("data/students.json")) as f:
            return json.load(f)

    def load_grades(self):
        return pd.read_csv(skpath.SKPath("data/grades.csv"))

    def generate_report(self):
        # load the students
        students = self.load_students()

        # load the grades
        grades = self.load_grades()

        # generate the report
        report = f"Student Report\n\n"
        for student in students:
            student_grade = grades[grades['name'] == student['name']]['grade'].iloc[0]
            report += f"{student['name']}: {student_grade}\n"
        return report

    def save_report(self):
        report_file = skpath.SKPath("reports/final_grades.txt")
        report_file.parent.mkdir(exist_ok=True)  # Create reports dir if needed
        
        with open(report_file, 'w') as f:  # SKPath works directly!
            f.write(self.generate_report())

# Usage - simple and clean

# after you update the grades in file...
StudentGrades().save_report()
```

#### 5. Simple Web Scraper with Output
**Problem:** Results scattered across computer, hard to find latest data.
```python
from suitkaise import skpath
import json
import requests
from datetime import datetime

@skpath.autopath()
def scrape_and_save(url: str, output_path=None):
    # autopath converts output_path to SKPath automatically!
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"results/scrape_{timestamp}.json"
    
    # Ensure results directory exists
    output_path.parent.mkdir(exist_ok=True)
    
    # Scrape and save data
    response = requests.get(url)
    data = response.json()
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Results saved to: {output_path.np}")

scrape_and_save("https://api.example.com/data")
```

### Professional/Advanced Projects

#### 6. Django/Flask App Asset Loading
**Problem:** Template and static file loading breaks across different deployment environments.
```python
from suitkaise import skpath
from flask import Flask

app = Flask(__name__)

def load_email_template(template_name: str):

    template_path = skpath.SKPath(f"templates/emails/{template_name}")
    return template_path.read_text()

def send_email(email_content: str) -> bool:
    # Send email logic here...
    return True # if email is sent, return True, otherwise False

@app.route('/send-welcome')
def send_welcome_email() -> bool:
    # Works whether app runs from project root, subdirectory, or server
    email_content = load_email_template("welcome.html")

    # Send email logic here...
    email_sent = send_email(email_content)

    return email_sent
```

#### 7. Data Science Notebook Path Consistency
**Problem:** Jupyter notebooks can't find datasets when moved between folders.
```python
from suitkaise import skpath
import pandas as pd

# Works in any notebook, anywhere in project structure
def load_dataset(dataset_name: str, data_type: str = "raw"):
    data_path = skpath.SKPath(f"data/{data_type}/{dataset_name}")
    
    if data_path.suffix == ".csv":
        return pd.read_csv(data_path)
    elif data_path.suffix == ".json":
        return pd.read_json(data_path)
    else:
        raise ValueError(f"Unsupported file type: {data_path.suffix}")

# Usage in any notebook
customers_df = load_dataset("customers.csv")  # Always finds data/raw/customers.csv
processed_df = load_dataset("cleaned_data.json", "processed")
```

#### 8. Test Fixture Discovery
**Problem:** Tests fail when run from different directories or in CI/CD.
```python
from suitkaise import skpath
import json
import pytest

def load_test_data(fixture_name: str):
    fixture_path = skpath.SKPath(skpath.get_current_dir() / "fixtures" / fixture_name)
    
    with open(fixture_path, 'r') as f:
        return json.load(f)

class TestUserAPI:
    def test_user_creation(self):
        # Always finds fixture data, regardless of test execution context
        user_data = load_test_data("sample_user.json")
        
        # Test logic here
        assert user_data["email"].endswith("@example.com")
```

#### 9. Docker Build Context Management
**Problem:** COPY commands fail because paths differ between local and CI environments.
```python
from suitkaise import skpath

def generate_dockerfile():
    """Generate Dockerfile with correct paths for any build context."""

    # if you have .*ignore files, you can do this, as ignore=True is the default
    project_files = skpath.get_all_project_paths()

    # if no .*ignore files are present, you can do this:
    # project_files = skpath.get_all_project_paths(
    #     except_paths=["venv", "node_modules", ".git", "__pycache__"] # etc.
    # )
    
    dockerfile_lines = ["FROM python:3.11-slim", "WORKDIR /app", ""]
    
    # Copy requirements first for better layer caching
    for file_path in project_files:
        if file_path.name.startswith("requirements"):
            dockerfile_lines.append(f"COPY {file_path.np} /app/{file_path.np}")
    
    dockerfile_lines.extend(["RUN pip install -r requirements.txt", ""])
    
    # Copy application code
    for file_path in project_files:
        if file_path.suffix == ".py":
            dockerfile_lines.append(f"COPY {file_path.np} /app/{file_path.np}")
    
    return "\n".join(dockerfile_lines)

# Generate Dockerfile that works in any build context
dockerfile_content = generate_dockerfile()
with open(skpath.SKPath("Dockerfile"), 'w') as f:  # Save to project root
    f.write(dockerfile_content)
```

#### 10. Environment-Specific Configuration Loading
**Problem:** Apps need different configs for dev/staging/prod but path resolution breaks across environments.
```python
from suitkaise import skpath
import yaml
import os
from pathlib import Path

def load_config():
    """Load configuration with intelligent fallback chain."""
    env = os.environ.get('ENVIRONMENT', 'development')
    
    # Check locations in priority order - all relative to project root
    config_locations = [
        skpath.SKPath(f"config/{env}.yaml"),          # Environment-specific
        skpath.SKPath("config/default.yaml"),         # Project default
        Path.home() / ".myapp" / "config.yaml",       # User-specific
        skpath.SKPath("config.yaml")                  # Legacy location
    ]
    
    for config_path in config_locations:
        if config_path.exists():
            print(f"Loading config from: {config_path.np}")
            with open(config_path) as f:  # SKPath works directly!
                return yaml.safe_load(f)
    
    raise FileNotFoundError("No configuration file found in any expected location")

# Usage - works in development, staging, production, or any deployment scenario
config = load_config()
database_url = config["database"]["url"]
```

## 13. Function-by-Function Examples

### Core Path Functions

#### `get_current_dir()` - Stop Wrestling with Frame Inspection
```python
# The painful way - inspecting call stack manually
import inspect
import os
frame = inspect.currentframe()
caller_file = frame.f_back.f_globals['__file__']
current_dir = os.path.dirname(os.path.realpath(caller_file))

# The SKPath way - one line
from suitkaise import skpath
current_dir = skpath.get_current_dir()

# Real use case: Loading config files next to your script
config_file = skpath.get_current_dir() / "config.json"
```

#### `get_cwd()` - Current Working Directory with Project Context
```python
# Regular way - just gives you the working directory
import os
cwd = os.getcwd()  # But where is this relative to your project?

# SKPath way - working directory with project context
cwd = skpath.get_cwd()
print(f"Working from: {cwd.np}")  # Shows "scripts/" instead of "/home/user/myproject/scripts"

# Real use case: Saving relative output files
output_file = skpath.get_cwd() / "output.txt"
print(f"Saving to: {output_file.np}")  # User sees "scripts/output.txt", not full path
```

#### `get_caller_path()` - Know Where You Were Called From
```python
# The painful way - manual stack inspection
import inspect
def save_debug_info():
    frame = inspect.currentframe().f_back
    caller_file = frame.f_globals['__file__']
    # ... more frame manipulation

# The SKPath way
def save_debug_info():
    caller = skpath.get_caller_path()
    debug_file = caller.parent / f"debug_{caller.stem}.log"

# Real use case: Error logging that shows where problems occur
def log_error(message):
    caller = skpath.get_caller_path()
    error_log = skpath.get_project_root() / "logs" / f"error_{caller.stem}.log"
    with open(error_log, "a") as f:
        f.write(f"{caller.np}: {message}\n")
```

### Path Comparison and ID Functions

#### `equalpaths()` - Intelligent Path Comparison
```python
# The problematic way - paths that should be equal aren't
import os
path1 = "/home/user/project/data/file.txt"
path2 = "data/file.txt"  # Same file, different representation
print(path1 == path2)  # False! But they're the same file

# The painful way - manual comparison
from pathlib import Path
path1 = Path("/home/user/project/data/file.txt").resolve()
path2 = Path("data/file.txt").resolve()  # Same file, different representation
print(path1 == path2)  # True, but lengthy code lines

# SKPath way - smart comparison
path1 = "/home/user/project/data/file.txt"
path2 = "data/file.txt"  # Same file, different representation
print(skpath.equalpaths(path1, path2))  # True! Compares project-relative paths first

# Real use case: Checking if uploaded file conflicts with existing files
def check_file_conflict(uploaded_path, existing_files):
    for existing in existing_files:
        if skpath.equalpaths(uploaded_path, existing):
            return f"File already exists at {existing.np}"
    return None
```

#### `path_id()` and `path_id_short()` - Reproducible Path Fingerprints
```python
# The manual way - creating consistent identifiers
import hashlib
def make_file_id(filepath):
    abs_path = os.path.abspath(filepath)
    hash_obj = hashlib.md5(abs_path.encode())
    # ... lots of string manipulation

# SKPath way - instant reproducible IDs
file_id = skpath.path_id("/path/to/file.txt")  # "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
short_id = skpath.path_id_short("/path/to/file.txt")  # "a1b2c3d4"

# Real use case: Creating unique cache keys for processed files
def process_image(image_path):
    cache_key = skpath.path_id_short(image_path)
    cache_file = skpath.get_project_root() / "cache" / f"processed_{cache_key}.jpg"
    
    if cache_file.exists():
        return cache_file  # Already processed
    
    # Process image and save to cache...
```

### Module and Object Inspection

#### `get_module_path()` - Find Where Objects Are Defined
```python
# The manual way - hunting down object definitions
import inspect
def find_object_source(obj):
    try:
        module = inspect.getmodule(obj)
        if module and hasattr(module, '__file__'):
            return module.__file__
    except:
        return None

# SKPath way - one line with error handling
source_path = skpath.get_module_path(MyClass)

# Real use case: Dynamic plugin loading with source tracking
def load_plugins():
    plugins = []
    for plugin_class in discover_plugins():
        plugin_source = skpath.get_module_path(plugin_class)
        plugins.append({
            'class': plugin_class,
            'source': plugin_source.np if plugin_source else 'built-in',
            'last_modified': plugin_source.stat().st_mtime if plugin_source else None
        })
    return plugins
```

### Project Structure Analysis

#### `get_all_project_paths()` - Smart File Discovery
```python
# The painful way - manual directory walking with ignore logic
import os
def get_project_files():
    files = []
    for root, dirs, filenames in os.walk('.'):
        # Manually implement .gitignore logic
        if '.git' in dirs:
            dirs.remove('.git')
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        # ... lots more manual exclusions
        
# SKPath way - automatic .gitignore integration
project_files = skpath.get_all_project_paths()  # Respects .gitignore automatically
python_files = [f for f in project_files if f.suffix == '.py']

# Real use case: Code analysis tools
def analyze_code_complexity():
    python_files = skpath.get_all_project_paths()
    complexity_report = {}
    
    for file_path in python_files:
        if file_path.suffix == '.py':
            # Analyze file...
            complexity_report[file_path.np] = calculate_complexity(file_path)
    
    return complexity_report
```

#### `get_project_structure()` - Hierarchical Project Data
```python
# The manual way - building nested dictionaries
def build_project_tree():
    structure = {}
    for root, dirs, files in os.walk('.'):
        # Complex nested dictionary building...
        
# SKPath way - instant nested structure
structure = skpath.get_project_structure()

# Real use case: Interactive file explorer UI
def create_file_tree_widget(structure, parent_widget=None):
    """Create a GUI tree widget from project structure."""
    for name, content in structure.items():
        if isinstance(content, dict):
            # It's a directory
            folder_widget = FolderWidget(name, parent_widget)
            create_file_tree_widget(content, folder_widget)  # Recursive
        else:
            # It's a file
            FileWidget(name, parent_widget)
```

#### `get_formatted_project_tree()` - Pretty Terminal Output
```python
# The manual way - ASCII art generation
def print_directory_tree(path, prefix=""):
    # Lots of string manipulation for tree characters...
    
# SKPath way - instant pretty output
tree = skpath.get_formatted_project_tree(max_depth=2)
print(tree)

# Real use case: Project documentation generation
def generate_project_overview():
    """Generate markdown documentation with project structure."""
    tree = skpath.get_formatted_project_tree(
        show_files=False,  # Just directories for overview
        max_depth=3
    )
    
    readme_content = f"""
# Project Structure

```
{tree}
```

## Key Directories
- `src/`: Main application code
- `tests/`: Test suite
- `docs/`: Documentation
    """
    
    readme_path = skpath.get_project_root() / "PROJECT_STRUCTURE.md"
    readme_path.write_text(readme_content)
```

### Project Root Management

#### `force_project_root()` - Override for Special Cases
```python
# Use case: Testing with temporary directories
import tempfile

def test_file_operations():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up test project structure
        test_project = Path(temp_dir) / "test_project"
        test_project.mkdir()
        (test_project / "LICENSE").touch()
        (test_project / "README.md").touch()
        (test_project / "requirements.txt").touch()
        
        # Force SKPath to use our test directory
        skpath.force_project_root(test_project)
        
        # Now all SKPath operations use the test directory
        test_file = skpath.get_project_root() / "test_data.json"
        # ... run tests
        
        # Clean up
        skpath.clear_forced_project_root()
```

#### `get_forced_project_root()` - Check Override Status
```python
# Use case: Debugging path issues
def debug_project_setup():
    forced_root = skpath.get_forced_project_root()
    if forced_root:
        print(f"⚠️  Project root is manually set to: {forced_root}")
        print("This might be why paths aren't working as expected.")
    else:
        detected_root = skpath.get_project_root()
        print(f"✅ Project root auto-detected as: {detected_root}")
```

### Factory Functions

#### `create()` - SKPath Factory with Options
```python
# Use case: Creating SKPaths with custom project context
def process_user_uploads(upload_dir, custom_project_root=None):
    """Process files with different project context."""
    
    for file_path in upload_dir.iterdir():
        # Create SKPath with custom project root for processing
        skpath_file = skpath.create(file_path, custom_root=custom_project_root)
        
        # Now file.np shows path relative to the custom root
        print(f"Processing: {skpath_file.np}")
        
        # Process file...
```

## Performance and Convenience Features

All project analysis functions (`get_all_project_paths`, `get_project_structure`, `get_formatted_project_tree`) include smart optimizations:

- **Automatic .gitignore parsing** - No manual ignore logic needed
- **Selective exclusion** - `except_paths` parameter for custom filtering  
- **Performance control** - `max_depth` limits for large projects
- **Memory efficiency** - `as_str=True` option to avoid creating SKPath objects when not needed

```python
# Fast scanning for large projects
large_project_files = skpath.get_all_project_paths(
    except_paths=["node_modules", "venv"],  # Skip heavy directories
    as_str=True  # Don't create SKPath objects, just return strings
)

# Focused analysis
docs_tree = skpath.get_formatted_project_tree(
    custom_root=skpath.get_project_root() / "docs",
    max_depth=2,
    show_files=False  # Just show directory structure
)
```