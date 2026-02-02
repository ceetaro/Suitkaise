# Why you would use `paths`

## TLDR

`paths` exists because path handling in Python is:

1. **Inconsistent** — `\` vs `/`, absolute vs relative, string vs Path
2. **Manual** — find root, resolve, normalize, convert, repeat
3. **Error-prone** — works on your machine, breaks on theirs
4. **Tedious** — same boilerplate in every project

`paths` makes it:

1. **Consistent** — normalized slashes, project-relative paths, cross-platform by default
2. **Automatic** — root detection, type conversion, caller detection
3. **Reliable** — same `rp` on every machine, every OS
4. **Simple** — one line instead of thirteen

Stop fighting with paths. Start using them.

---

File paths are a pain to work with.

Sometimes pure hell, even.

I got gutted the moment I started trying to write cross-platform code. Slashes going the wrong way, paths breaking when my teammate ran the same script, logs full of absolute paths that meant nothing on another machine. Well shit, man. Whoops.

Find the project root, resolve the path, make it relative, normalize the slashes, cast it to a string, pass it in. Over and over. Just to achieve simple cross-platform compatibility.

I don't want to inspect the stack to find the caller path.

I don't want to `.resolve()` every single path.

I just want path handling to be easy, consistent, and have some basic level of standardization.

So I made `paths`.

## `Skpath` paths

Every `Skpath` stores three paths:

- `ap` — absolute path, always forward slashes (`/Users/me/project/data/file.txt`)

- `rp` — normalized path relative to project root (`data/file.txt`)

- `platform` — absolute path with the correct separators for the current platform

`rp` is the same on every machine, every OS, as long as the project structure is the same. Which it should be! Make sure to pull guys! Haha! Resolve those merge conflicts!

On a serious note, this changes everything -- and is a huge jump in path standardization.

## What about just using `pathlib`?

`pathlib` is great. It handles slash differences internally and gives you a nice object to work with.

But it doesn't know about your project. It doesn't auto-detect the root. It doesn't give you a consistent path that works everywhere. And it doesn't convert types for you.

`Skpath` wraps `pathlib.Path` and adds project awareness, so you don't have to make it aware of things yourself.

The `paths` module also adds a bunch of cool things like `@autopath` and `AnyPath` to help you in your quest to make paths easy and standardized for your entire team.

`pathlib.Path` handles cross-platform normalization internally, but the moment you convert to a string (for logging, storing, or passing to a library), you're back to platform-specific slashes. What's the point?

```python
path = Path("config/settings.yaml")
str(path)

# "config/settings.yaml" on Mac, "config\\settings.yaml" on Windows
```

Here is a set of problems that `paths` solves.

### 1. `\` vs `/`

Windows uses `\`, everything else uses `/`. 

While most developers use Mac with Python (it runs better), users will be using your code on both Mac and Windows. So you need to support both.

So, you write code on a Mac, push it, and your teammate on Windows gets broken paths.

```python
# You write this on Mac
config_path = "config/settings.yaml"

# Works fine on Mac
open(config_path)  # ✓

# Your teammate on Windows logs the resolved path
print(Path(config_path).resolve())

# C:\Users\teammate\project\config\settings.yaml

# Later, that path gets stored or compared somewhere
# Now you have mixed slashes in your system
```

With `Skpath`

```python
path = Skpath("config/settings.yaml")

path.ap  # Always forward slashes: "/Users/me/project/config/settings.yaml"

path.rp  # Always forward slashes: "config/settings.yaml"

path.platform  # platform specific

str(path)  # Always forward slashes (same as ap)
```

Need to pass a path to a Windows-specific tool or open a file? Use `path.platform`. Want to log or store paths consistently? Use `path.rp` (or `path.ap`).

`Skpath` normalizes to forward slashes everywhere, except for `platform`, which you would want to use for OS-specific operations.

### 2. Relative paths

Writing out the full path to a file sucks.

But relative paths are inconsistent and unclear.

Is the `data/file.txt` path relative to the root? The cwd? What if there are multiple files of the same name under different `/data` directories?

So, you have to do something like this every time.

```python
path = Path("data/file.txt")
path = path.resolve()
path = str(path)
```

You could do it in one long line if you want, I guess.

```python
path = str(Path("data/file.txt").resolve())
```

With `Skpath`, you just create it and it's ready to use cross-platform.

```python
path = Skpath("data/file.txt")
```

So much cleaner, so much simpler.

`Skpath`s are awesome because they actually store 3 paths.

- stores absolute path
- also auto detects the project root and stores the path relative to it
- stores platform specific separator absolute path

`Skpath`s are automatically cross-platform compatible.

When you work with `Skpath` objects across machines or even operating systems, as long as the project root is the same, the paths will work the same.

So now you can just `Skpath` everything and not have to worry about platform issues, or having to manually relate paths to the root.

No more "relative path" confusion. Everything is project root based.

### 3. Project root related issues

Finding the project root recursively is not standardized at all.

Also a drag to do.

Each dev does it slightly differently, and there are inconsistencies.

You end up having to copy paste something like this every time:

```python
def find_project_root():
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")

PROJECT_ROOT = find_project_root()
```

Which is cloudy and relies on exact indicators.

With `Skpath`, you can just do this:

```python
# 1 line into Skpath
PROJECT_ROOT = Skpath().root
```

Or this:

```python
# 1 line into Path
PROJECT_ROOT = Skpath().root_path
```

Or this:

```python
# 1 line into str
PROJECT_ROOT = Skpath().root_str
```

Or this:

```python
# 1 line into Skpath
PROJECT_ROOT = paths.get_project_root()
```

With `paths` you can also use different roots quickly and easily.

- you can add a `setup.sk` file to your project root to guarantee detection (it will look for things like `setup.py` even if you don't do this, but it will look for this first)

- you can use `set_custom_root` to set a custom root that all `Skpath` objects will use

- you can use the `CustomRoot` context manager to temporarily set a custom root for a code block for things like testing

Note that `Skpath`s are created with the project root they were given, so either use a custom root or don't.


### 4. Figuring out if you need to use a `Path` or a `str`

Even if you are in an IDE/code editor, figuring out what type of path you need to use for what function across a whole project base is frustrating.

You have to make everyone use either `Path` or `str`, or let everyone code how they want and then hover over every function using paths to see the expected types.

`@autopath` does this for you.

```python
@autopath()
def function_that_uses_strs(path: str, ...):

    # changes all Paths to strings for you before passing them in
```

```python
@autopath()
def function_that_uses_paths(path: Path, ...):

    # changes all strings to Paths for you before passing them in
```

All you have to do is slap `@autopath()` on the function and it will automatically convert the paths to the types that you expect, and automatically normalize them through `Skpath` as well, guaranteeing cross-platform compatibility.

There is also another way to do this: the `AnyPath` type.

`AnyPath` is a union of `str`, `Path`, and `Skpath`.

This allows you to quickly update your code to use the superior `Skpath` type, while not breaking previous code.

```python
from suitkaise.paths import AnyPath

def function_that_uses_any_paths(path: AnyPath, ...):

    # allows you to accept all 3 path types 
    # without having to create unions every time
```

And when you combine them...

```python
from suitkaise.paths import autopath, AnyPath

@autopath()
def function_that_uses_any_paths(path: AnyPath, ...):

    # automatically converts strs and Paths to Skpaths for you
    # gives you access to the more awesome Skpath quickly
```

I do a lot of solo coding, and even I was having trouble standardizing path code! When working in a team, don't even get me started.

This is a game changer.

### 5. Comparing paths

Say you're writing a script that processes files and saves which ones are done to a log file, so you can skip them on future runs.

```python
from pathlib import Path
import json

LOG_FILE = "processed_files.json"

def load_processed():
    if Path(LOG_FILE).exists():
        return set(json.load(open(LOG_FILE)))
    return set()

def save_processed(processed):
    json.dump(list(processed), open(LOG_FILE, "w"))

def process_file(path, processed):
    path_str = str(Path(path).resolve())
    if path_str in processed:
        print(f"Skipping {path}, already processed")
        return

    # ... do the actual processing ...

    processed.add(path_str)
    save_processed(processed)
```

Murphy runs the script on his Mac:

```python
processed = load_processed()
process_file("data/report.csv", processed)
```

The log file now contains:

```json
["/Users/murphy/projects/myapp/data/report.csv"]
```

Gurphy pulls the latest changes and runs the same script on his Windows machine:

```python
processed = load_processed()
process_file("data/report.csv", processed)
```

His resolved path is `C:\Users\gurphy\projects\myapp\data\report.csv`, which doesn't match Murphy's path in the log.

The same file gets processed twice because absolute paths don't match across machines or operating systems.

You could try to fix this by storing paths relative to the project root:

```python
def process_file(path, processed):
    path_resolved = Path(path).resolve()
    path_relative = str(path_resolved.relative_to(PROJECT_ROOT))
    if path_relative in processed:
        # ...
```

But now you need to find `PROJECT_ROOT` consistently and correctly, and fix the separators to be consistent.

The funniest thing here is that the log file might not even load in the first place because the paths are different.

With `paths`

```python
from suitkaise.paths import Skpath, autopath
import json

LOG_FILE = "processed_files.json"

@autopath()
def process_file(path: Skpath, processed: set[Skpath]):

    if path.rp in processed:
        print(f"Skipping {path.rp}, already processed")
        return
    
    # ... do the actual processing ...
    
    processed.add(path.rp)
    save_processed(processed)
```

The log file now contains:

```json
["data/report.csv"]
```

Same on Murphy's Macbook. Same on Gurphy's Windows PC. Same on Furphy's Linux desktop.

## 6. General path handling is still so manual

General path handling is still so manual and error prone.

You have to normalize paths, resolve them, convert to strings, and more.

Sometimes you need to know which file called your function -- for logging, for relative path resolution, for debugging.

Without `paths` - *13 lines*
```python
import inspect # 1
from pathlib import Path # 2

def get_caller_file(): # 3
    stack = inspect.stack() # 4
    
    for frame in stack[1:]: # 5
        filename = frame.filename # 6
        
        # Skip built-in/frozen modules # 7
        if filename.startswith("<"): # 8
            continue # 9

        more_filtering_logic() # 10
        
        return Path(filename).resolve() # 11
    
    raise RuntimeError("Could not detect caller") # 12

caller = get_caller_file() # 13
```

And this doesn't even handle edge cases like notebook environments, compiled code, or filtering out your own library's frames.

With `paths` - *1 line*
```python
caller = Skpath()
```

Or this:
```python
caller = get_caller_path()
```

Or this:
```python
@autopath(use_caller=True) # 1
def function_that_uses_caller_path(path: Skpath):

    # path will be the caller's file path if not explicitly provided
```

## 7. Path IDs for storage

Storing file paths in a database is a nightmare.

Absolute paths are different on every machine. Relative paths need context. Backslashes break JSON. Forward slashes break some Windows tools.

What if you could store a single, URL-safe string that reconstructs the original path? And have it take up less space than the full path?

```python
path = Skpath("data/reports/2024/q1.csv")

# get a reversible, URL-safe ID
path_id = path.id
# "ZGF0YS9yZXBvcnRzLzIwMjQvcTEuY3N2"

# store it in your database, pass it in URLs, use it as a cache key
db.execute("INSERT INTO files (path_id, ...) VALUES (?, ...)", (path_id, ...))

# later, reconstruct the full path from the ID
same_path = Skpath(path_id)
print(same_path.rp)
# "data/reports/2024/q1.csv"
```

The ID is:
- Base64url encoded (URL-safe, no weird characters)
- Reversible (you can always get the original path back)
- Cross-platform (uses the normalized `rp`, not the absolute path)
- Compact (shorter than most full paths)

Perfect for databases, APIs, cache keys, and anywhere you need to reference a file without storing a full path.

## 8. Finding where code lives

Ever needed to know where a module or class is actually defined?

```python
import json

# where is the json module?
json.__file__
# might be None for built-in modules

# what about a class from a third-party library?
from requests import Session
# ... now what?
```

With `paths`:

```python
from suitkaise import paths
import json
from requests import Session

# get the file path for any module, class, or function
json_path = paths.get_module_path(json)
print(json_path.ap)
# "/usr/lib/python3.11/json/__init__.py"

session_path = paths.get_module_path(Session)
print(session_path.ap)
# "/home/user/.venv/lib/python3.11/site-packages/requests/sessions.py"

# works with your own code too
from myapp.utils import MyHelper
my_path = paths.get_module_path(MyHelper)
print(my_path.rp)
# "myapp/utils.py"
```

Useful for debugging, documentation generation, or even if you are just curious about where a module is actually defined.

## 9. Project structure at a glance

Need to see what's in your project? Generate a file list? Create documentation?

```python
from suitkaise import paths

# get all files in your project (respects .gitignore automatically)
all_files = paths.get_project_paths()
py_files = [f for f in all_files if f.suffix == ".py"]
print(f"Found {len(py_files)} Python files")

# get a nested dictionary structure
structure = paths.get_project_structure()
# {
#     "src": {
#         "main.py": {},
#         "utils": {
#             "helpers.py": {},
#             "config.py": {}
#         }
#     },
#     "tests": {...}
# }

# or a nice tree string for documentation
tree = paths.get_formatted_project_tree(depth=2)
print(tree)
# myproject/
# ├── src/
# │   ├── main.py
# │   └── utils/
# └── tests/
#     └── test_main.py
```

All of these respect `.gitignore` by default, so you don't get flooded with `node_modules` or `.venv` files.

## 10. Filename validation and sanitization

User uploads a file called `<script>alert('xss')</script>.txt`. Or `CON.txt` (reserved on Windows). Or `файл с пробелами.txt` (Cyrillic with spaces).

Now what?

```python
from suitkaise.paths import is_valid_filename, streamline_path, streamline_path_quick

# check if a filename is valid on all platforms
is_valid_filename("report.pdf")           # True
is_valid_filename("file<name>.txt")       # False - contains < and >
is_valid_filename("CON")                  # False - Windows reserved name
is_valid_filename("file\twith\ttabs.txt") # False - contains tabs

# sanitize a filename to be safe everywhere
clean = streamline_path_quick("My Report (Final) — версия 2.pdf")
# "My_Report__Final______2.pdf"

# more control over sanitization
clean = streamline_path(
    "User Upload: <script>.txt",
    replacement_char="-",
    lowercase=True,
    max_len=20
)
# "user-upload---script.txt"
```

Never trust user input. Sanitize everything. `paths` makes it easy.

## 11. Temporary root override for testing

Testing code that uses project paths is annoying. Your tests run from a different directory, your CI runs from yet another place.

```python
from suitkaise.paths import CustomRoot, Skpath

# in your test file
def test_config_loading():
    # temporarily set a custom root for this test
    with CustomRoot("/tmp/test_project"):
        # all Skpath operations now use /tmp/test_project as root
        config = Skpath("config/settings.yaml")
        assert config.root_str == "/tmp/test_project"
        
        # your code that depends on project root works correctly
        result = load_config()
        assert result["setting"] == "test_value"
    
    # outside the block, normal root detection resumes
```

No more patching, no more environment variables, no more test fixtures that set up fake directory structures.

### 12. Using paths as dict keys or in sets

You want to track which files you've seen. Simple, right?

Without `paths` - *8 lines*
```python
from pathlib import Path # 1

seen = set() # 2

def mark_seen(path: str):

    # Normalize to avoid duplicates
    normalized = Path(path) # 3
    normalized = normalized.resolve() # 4
    normalized = str(normalized) # 5
    seen.add(normalized)

def is_seen(path: str):
    normalized = Path(path) # 6
    normalized = normalized.resolve() # 7
    normalized = str(normalized) # 8
    return normalized in seen

# this STILL might mess up and have duplicate paths
len(seen)
```

You have to manually normalize every time you add or check. And if you forget once, you get duplicates or missed lookups.

With `paths`
```python
from suitkaise import paths # 1

seen = set() # 2

@paths.autopath() # 3
def mark_seen(path: paths.AnyPath):
    seen.add(path)

@paths.autopath() # 4
def is_seen(path: paths.AnyPath):
    return path in seen

len(seen) # no duplicates
```

`Skpath` objects hash and compare using their normalized path (`rp`), so different representations of the same file are recognized as equal.

Works in sets, works as dict keys, no extra effort.