/*

synced from suitkaise-docs/paths/why.md

*/

rows = 2
columns = 1

# 1.1

title = "Why you would use `paths`"

# 1.2

text = "
## TLDR

`<suitkaise-api>paths</suitkaise-api>` exists because path handling in Python is:

1. **Inconsistent** — `\` vs `/`, absolute vs relative, string vs Path
2. **Manual** — find root, resolve, normalize, convert, repeat
3. **Error-prone** — works on your machine, breaks on theirs
4. **Tedious** — same boilerplate in every project

`<suitkaise-api>paths</suitkaise-api>` makes it:

1. **Consistent** — normalized slashes, project-relative paths, cross-platform by default
2. **Automatic** — root detection, type conversion, caller detection
3. **Reliable** — same `<suitkaise-api>rp</suitkaise-api>` on every machine, every OS
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

So I made `<suitkaise-api>paths</suitkaise-api>`.

### Drop-in upgrade from `pathlib`

`<suitkaise-api>Skpath</suitkaise-api>` wraps `pathlib.Path`. Everything `pathlib.Path` does, `<suitkaise-api>Skpath</suitkaise-api>` does too -- same methods, same interface, same behavior. You don't have to relearn anything.

What `<suitkaise-api>Skpath</suitkaise-api>` adds on top:
- Project-relative paths (`rp`) that are identical on every machine and OS
- Automatic project root detection
- Platform-aware absolute paths
- Reversible path IDs for database storage

If you already use `pathlib`, switching to `<suitkaise-api>Skpath</suitkaise-api>` is a one-word change in your imports with zero risk of breaking existing code.

### Automatic path detection — `<suitkaise-api>Skpath(</suitkaise-api>)` with no arguments

Need to know the path of the current file? Don't inspect the stack yourself.

```python
# get the current file's path as an Skpath, automatically
<suitkaise-api>here</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>)
```

That's it. `<suitkaise-api>Skpath(</suitkaise-api>)` with no arguments detects the caller's file path. Works in scripts, modules, notebooks, and test runners.

## `<suitkaise-api>Skpath</suitkaise-api>` paths

Every `<suitkaise-api>Skpath</suitkaise-api>` stores three paths:

- `ap` — absolute path, always forward slashes (`/Users/me/project/data/file.txt`)

- `rp` — normalized path relative to project root (`data/file.txt`)

- `platform` — absolute path with the correct separators for the current platform

`rp` is the same on every machine, every OS, as long as the project structure is the same.

This changes everything -- and is a huge jump in path standardization.

## `<suitkaise-api>@autopath</suitkaise-api>` — make any function path-safe

The fastest way to make your codebase cross-platform: slap `<suitkaise-api>@autopath</suitkaise-api>()` on any function that takes paths.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>

<suitkaise-api>@autopath</suitkaise-api>()
def process_file(path: <suitkaise-api>AnyPath</suitkaise-api>):
    # path is now an Skpath, regardless of what was passed in
    # str, Path, or Skpath -- all converted automatically
    print(<suitkaise-api>path.rp</suitkaise-api>)  # always cross-platform
```

Pass a `str`, a `Path`, or an `<suitkaise-api>Skpath</suitkaise-api>` -- `<suitkaise-api>@autopath</suitkaise-api>()` reads the type annotation and converts it for you. Your function just works, no matter what the caller gives it.

Combined with `<suitkaise-api>AnyPath</suitkaise-api>` (a union of `str`, `Path`, and `<suitkaise-api>Skpath</suitkaise-api>`), you can upgrade your entire codebase to use `<suitkaise-api>Skpath</suitkaise-api>` incrementally without breaking anything that already passes strings or Paths.

This is the "pit of success" -- once `<suitkaise-api>@autopath</suitkaise-api>()` is on a function, it's impossible to accidentally use a platform-specific path inside it.

## What about just using `pathlib`?

`pathlib` is great. It handles slash differences internally and gives you a nice object to work with.

But it doesn't know about your project. It doesn't auto-detect the root. It doesn't give you a consistent path that works everywhere. And it doesn't convert types for you.

`<suitkaise-api>Skpath</suitkaise-api>` wraps `pathlib.Path` and adds project awareness, so you don't have to make it aware of things yourself.

The `<suitkaise-api>paths</suitkaise-api>` module also adds a bunch of cool things like `<suitkaise-api>@autopath</suitkaise-api>` and `<suitkaise-api>AnyPath</suitkaise-api>` to help you in your quest to make paths easy and standardized for your entire team.

`pathlib.Path` handles cross-platform normalization internally, but the moment you convert to a string (for logging, storing, or passing to a library), you're back to platform-specific slashes. What's the point?

```python
path = Path("config/settings.yaml")
str(path)

# "config/settings.yaml" on Mac, "config\\settings.yaml" on Windows
```

Here is a set of problems that `<suitkaise-api>paths</suitkaise-api>` solves.

(start of dropdown "1. `\` vs `/`")
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

**With `<suitkaise-api>Skpath</suitkaise-api>`**

```python
<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"config/settings.yaml")

<suitkaise-api>path.ap</suitkaise-api>  # Always forward slashes: "/Users/me/project/config/settings.yaml"

<suitkaise-api>path.rp</suitkaise-api>  # Always forward slashes: "config/settings.yaml"

<suitkaise-api>path.platform</suitkaise-api>  # platform specific

str(path)  # Always forward slashes (same as ap)
```

Need to pass a path to a Windows-specific tool or open a file? Use `<suitkaise-api>path.platform</suitkaise-api>`. Want to log or store paths consistently? Use `<suitkaise-api>path.rp</suitkaise-api>` (or `<suitkaise-api>path.ap</suitkaise-api>`).

`<suitkaise-api>Skpath</suitkaise-api>` normalizes to forward slashes everywhere, except for `platform`, which you would want to use for OS-specific operations.

(end of dropdown "1. `\` vs `/`")

(start of dropdown "2. Relative paths")
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

With `<suitkaise-api>Skpath</suitkaise-api>`, you just create it and it's ready to use cross-platform.

```python
<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"data/file.txt")
```

So much cleaner, so much simpler.

`Skpaths` are awesome because they actually store 3 paths.

- Stores absolute path
- Also auto detects the project root and stores the path relative to it
- Stores platform specific separator absolute path

`Skpaths` are automatically cross-platform compatible.

When you work with `<suitkaise-api>Skpath</suitkaise-api>` objects across machines or even operating systems, as long as the project root is the same, the paths will work the same.

So now you can just `<suitkaise-api>Skpath</suitkaise-api>` everything and not have to worry about platform issues, or having to manually relate paths to the root.

No more "relative path" confusion. Everything is project root based.

(end of dropdown "2. Relative paths")

(start of dropdown "3. Project root related issues")
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

With `<suitkaise-api>Skpath</suitkaise-api>`, you can just do this:

```python
<suitkaise-api>PROJECT_ROOT</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>).<suitkaise-api>root</suitkaise-api>
```

One line. Auto-detects the project root. Need a different type? `<suitkaise-api>Skpath(</suitkaise-api>).<suitkaise-api>root_path</suitkaise-api>` for `pathlib.Path`, `<suitkaise-api>Skpath(</suitkaise-api>).<suitkaise-api>root_str</suitkaise-api>` for `str`, or `<suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_root</suitkaise-api>()` as a standalone function.

With `<suitkaise-api>paths</suitkaise-api>` you can also use different roots quickly and easily.

- You can add a `setup.<suitkaise-api>sk</suitkaise-api>` file to your project root to guarantee detection (it will look for things like `setup.py` even if you don't do this, but it will look for this first)

- You can use `<suitkaise-api>set_custom_root</suitkaise-api>` to set a custom root that all `<suitkaise-api>Skpath</suitkaise-api>` objects will use

- You can use the `<suitkaise-api>CustomRoot</suitkaise-api>` context manager to temporarily set a custom root for a code block for things like testing

Note that `Skpaths` are created with the project root they were given, so either use a custom root or don't.

(end of dropdown "3. Project root related issues")

(start of dropdown "4. Figuring out if you need to use a `Path` or a `str`")
### 4. Figuring out if you need to use a `Path` or a `str`

Even if you are in an IDE/code editor, figuring out what type of path you need to use for what function across a whole project base is frustrating.

You have to make everyone use either `Path` or `str`, or let everyone code how they want and then hover over every function using paths to see the expected types.

`<suitkaise-api>@autopath</suitkaise-api>` does this for you.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>

<suitkaise-api>@autopath</suitkaise-api>()
def upload_file(local_path: <suitkaise-api>AnyPath</suitkaise-api>, bucket: str):
    # local_path is always Skpath, no matter what the caller passed
    print(f"Uploading {local_path.<suitkaise-api>rp</suitkaise-api>} to s3://{bucket}/{local_path.name}")

upload_file("data/report.csv", "my-bucket")           # caller passes str
upload_file(Path("data/report.csv"), "my-bucket")      # caller passes Path
upload_file(<suitkaise-api>Skpath(</suitkaise-api>"data/report.csv"), "my-bucket")    # caller passes Skpath

# all three work. zero type errors. zero manual conversion.
```

Slap `<suitkaise-api>@autopath</suitkaise-api>()` on any function and it automatically converts the paths to the types your annotations expect, normalizing through `<suitkaise-api>Skpath</suitkaise-api>` for cross-platform compatibility.

There is also another way to do this: the `<suitkaise-api>AnyPath</suitkaise-api>` type.

`<suitkaise-api>AnyPath</suitkaise-api>` is a union of `str`, `Path`, and `<suitkaise-api>Skpath</suitkaise-api>`.

This allows you to quickly update your code to use the superior `<suitkaise-api>Skpath</suitkaise-api>` type, while not breaking previous code.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>AnyPath</suitkaise-api>

def function_that_uses_any_paths(path: <suitkaise-api>AnyPath</suitkaise-api>, ...):

    # allows you to accept all 3 path types 
    # without having to create unions every time
```

And when you combine them...

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>autopath</suitkaise-api>, <suitkaise-api>AnyPath</suitkaise-api>

<suitkaise-api>@autopath</suitkaise-api>()
def function_that_uses_any_paths(path: <suitkaise-api>AnyPath</suitkaise-api>, ...):

    # automatically converts strs and Paths to Skpaths for you
    # gives you access to the more awesome Skpath quickly
```

I do a lot of solo coding, and even I was having trouble standardizing path code! When working in a team, don't even get me started.

This is a game changer.

(end of dropdown "4. Figuring out if you need to use a `Path` or a `str`")

(start of dropdown "5. Comparing paths")
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

**With `<suitkaise-api>paths</suitkaise-api>`**

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>, <suitkaise-api>autopath</suitkaise-api>
import json

LOG_FILE = "processed_files.json"

def load_processed():
    if <suitkaise-api>Skpath(</suitkaise-api>LOG_FILE).<suitkaise-api>exists</suitkaise-api>:
        return set(<suitkaise-api>Skpath(</suitkaise-api>rp) for rp in json.load(open(LOG_FILE)))
    return set()

def save_processed(processed):
    json.dump([p.<suitkaise-api>rp</suitkaise-api> for p in processed], open(LOG_FILE, "w"))

<suitkaise-api>@autopath</suitkaise-api>()
def process_file(path: <suitkaise-api>Skpath</suitkaise-api>, processed: set):

    if path in processed:
        print(f"Skipping {path.<suitkaise-api>rp</suitkaise-api>}, already processed")
        return
    
    # ... do the actual processing ...
    
    processed.add(path)
    save_processed(processed)
```

`<suitkaise-api>Skpath</suitkaise-api>` hashes and compares by `<suitkaise-api>rp</suitkaise-api>`, so the set deduplication works automatically — no need to manually extract `.<suitkaise-api>rp</suitkaise-api>`.

The log file now contains:

```json
["data/report.csv"]
```

Same on Murphy's Macbook. Same on Gurphy's Windows PC. Same on Furphy's Linux desktop.

(end of dropdown "5. Comparing paths")

(start of dropdown "6. General path handling is still so manual")
## 6. General path handling is still so manual

General path handling is still so manual and error prone.

You have to normalize paths, resolve them, convert to strings, and more.

Sometimes you need to know which file called your function -- for logging, for relative path resolution, for debugging.

**Without it** - *13 lines*
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

**With `<suitkaise-api>paths</suitkaise-api>`** - *1 line*
```python
<suitkaise-api>caller</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>)
```

That's it. Also available as `<suitkaise-api>get_caller_path</suitkaise-api>()`, or via `<suitkaise-api>@autopath</suitkaise-api>(use_caller=True)` for automatic injection.

(end of dropdown "6. General path handling is still so manual")

(start of dropdown "7. Path IDs for storage")
## 7. Path IDs for storage

Storing file paths in a database is a nightmare.

Absolute paths are different on every machine. Relative paths need context. Backslashes break JSON. Forward slashes break some Windows tools.

What if you could store a single, URL-safe string that reconstructs the original path? And have it take up less space than the full path?

```python
<suitkaise-api>path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"data/reports/2024/q1.csv")

# get a reversible, URL-safe ID
path_id = path.<suitkaise-api>id</suitkaise-api>
# "ZGF0YS9yZXBvcnRzLzIwMjQvcTEuY3N2"

# store it in your database, pass it in URLs, use it as a cache key
db.execute("INSERT INTO files (path_id, ...) VALUES (?, ...)", (path_id, ...))

# later, reconstruct the full path from the ID
<suitkaise-api>same_path</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>path_id)
print(<suitkaise-api>same_path.rp</suitkaise-api>)
# "data/reports/2024/q1.csv"
```

The ID is:
- Base64url encoded (URL-safe, no weird characters)
- Reversible (you can always get the original path back)
- Cross-platform (uses the normalized `rp`, not the absolute path)
- Compact (shorter than most full paths)

Perfect for databases, APIs, cache keys, and anywhere you need to reference a file without storing a full path.

(end of dropdown "7. Path IDs for storage")

(start of dropdown "8. Finding where code lives")
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

With `<suitkaise-api>paths</suitkaise-api>`:

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>
import json
from requests import Session

# get the file path for any module, class, or function
json_path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_module_path</suitkaise-api>(json)
print(json_path.ap)
# "/usr/lib/python3.11/json/__init__.py"

session_path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_module_path</suitkaise-api>(Session)
print(session_path.ap)
# "/home/user/.venv/lib/python3.11/site-packages/requests/sessions.py"

# works with your own code too
from myapp.utils import MyHelper
my_path = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_module_path</suitkaise-api>(MyHelper)
print(my_path.rp)
# "myapp/utils.py"
```

Useful for debugging, documentation generation, or even if you are just curious about where a module is actually defined.

(end of dropdown "8. Finding where code lives")

(start of dropdown "9. Project structure at a glance")
## 9. Project structure at a glance

Need to see what's in your project? Generate a file list? Create documentation?

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api>

# get all files in your project (respects .gitignore automatically)
all_files = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_paths</suitkaise-api>()
py_files = [f for f in all_files if f.suffix == ".py"]
print(f"Found {len(py_files)} Python files")

# get a nested dictionary structure
structure = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_project_structure</suitkaise-api>()
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
tree = <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>get_formatted_project_tree</suitkaise-api>(depth=2)
print(tree)
# myproject/
# ├── src/
# │   ├── main.py
# │   └── utils/
# └── tests/
#     └── test_main.py
```

All of these respect `.gitignore` by default, so you don't get flooded with `node_modules` or `.venv` files.

(end of dropdown "9. Project structure at a glance")

(start of dropdown "10. Filename validation and sanitization")
## 10. Filename validation and sanitization

User uploads a file called `<script>alert('xss')</script>.txt`. Or `CON.txt` (reserved on Windows). Or `файл с пробелами.txt` (Cyrillic with spaces).

Now what?

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>is_valid_filename</suitkaise-api>, <suitkaise-api>streamline_path</suitkaise-api>, <suitkaise-api>streamline_path_quick</suitkaise-api>

# check if a filename is valid on all platforms
<suitkaise-api>is_valid_filename</suitkaise-api>("report.pdf")           # True
<suitkaise-api>is_valid_filename</suitkaise-api>("file<name>.txt")       # False - contains < and >
<suitkaise-api>is_valid_filename</suitkaise-api>("CON")                  # False - Windows reserved name
<suitkaise-api>is_valid_filename</suitkaise-api>("file\twith\ttabs.txt") # False - contains tabs

# sanitize a filename to be safe everywhere
clean = <suitkaise-api>streamline_path_quick</suitkaise-api>("My Report (Final) — версия 2.pdf")
# "My_Report__Final______2.pdf"

# more control over sanitization
clean = <suitkaise-api>streamline_path</suitkaise-api>(
    "User Upload: <script>.txt",
    replacement_char="-",
    lowercase=True,
    max_len=20
)
# "user-upload---script.txt"
```

Never trust user input. Sanitize everything. `<suitkaise-api>paths</suitkaise-api>` makes it easy.

(end of dropdown "10. Filename validation and sanitization")

(start of dropdown "10b. File operations without the boilerplate")
## 10b. File operations without the boilerplate

Moving or copying files shouldn't require three imports and five lines.

**Without `<suitkaise-api>paths</suitkaise-api>`**
```python
import shutil
from pathlib import Path

source = Path("data/report.csv")
dest = Path("backup/2024/report.csv")
dest.parent.mkdir(parents=True, exist_ok=True)
if dest.exists():
    dest.unlink()
shutil.copy2(source, dest)
```

**With `<suitkaise-api>paths</suitkaise-api>`**
```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>Skpath</suitkaise-api>

<suitkaise-api>source</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"data/report.csv")
source.<suitkaise-api>copy_to</suitkaise-api>("backup/2024/report.csv", overwrite=True, parents=True)
```

One line. Creates parent directories, handles overwrites, returns the destination `<suitkaise-api>Skpath</suitkaise-api>`. Same API for `<suitkaise-api>move_to</suitkaise-api>`.

(end of dropdown "10b. File operations without the boilerplate")

(start of dropdown "11. Temporary root override for testing")
## 11. Temporary root override for testing

Testing code that uses project paths is annoying. Your tests run from a different directory, your CI runs from yet another place.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>paths</suitkaise-api> import <suitkaise-api>CustomRoot</suitkaise-api>, <suitkaise-api>Skpath</suitkaise-api>

# in your test file
def test_config_loading():
    # temporarily set a custom root for this test
    with <suitkaise-api>CustomRoot(</suitkaise-api>"/tmp/test_project"):
        # all Skpath operations now use /tmp/test_project as root
        <suitkaise-api>config</suitkaise-api> = <suitkaise-api>Skpath(</suitkaise-api>"config/settings.yaml")
        assert config.root_str == "/tmp/test_project"
        
        # your code that depends on project root works correctly
        result = load_config()
        assert result["setting"] == "test_value"
    
    # outside the block, normal root detection resumes
```

No more patching, no more environment variables, no more test fixtures that set up fake directory structures.

(end of dropdown "11. Temporary root override for testing")

(start of dropdown "12. Using paths as dict keys or in sets")
### 12. Using paths as dict keys or in sets

You want to track which files you've seen. Simple, right?

**Without it** - *8 lines*
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

**With `<suitkaise-api>paths</suitkaise-api>`**
```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>paths</suitkaise-api> # 1

seen = set() # 2

<suitkaise-api>@paths</suitkaise-api>.<suitkaise-api>autopath</suitkaise-api>() # 3
def mark_seen(path: <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>AnyPath</suitkaise-api>):
    seen.add(path)

<suitkaise-api>@paths</suitkaise-api>.<suitkaise-api>autopath</suitkaise-api>() # 4
def is_seen(path: <suitkaise-api>paths</suitkaise-api>.<suitkaise-api>AnyPath</suitkaise-api>):
    return path in seen

len(seen) # no duplicates
```

`<suitkaise-api>Skpath</suitkaise-api>` objects hash and compare using their normalized path (`rp`), so different representations of the same file are recognized as equal.

Works in sets, works as dict keys, no extra effort.

(end of dropdown "12. Using paths as dict keys or in sets")

"
