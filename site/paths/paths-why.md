/*

why the skpath module was created

what problems it solves

each numbered section is a dropdown.

*/

text = "
File paths are a pain to work with.

Sometimes pure hell, even.

I got gutted the moment I started trying to write cross-platform code. Slashes going the wrong way, paths breaking when my teammate ran the same script, logs full of absolute paths that meant nothing on another machine. Oops.

Find the project root, resolve the path, make it relative, normalize the slashes, cast to string, pass it in. Over and over.

So I made `skpath`.

## `SKPath` paths

Every `SKPath` stores three paths:

- `ap` — absolute path, always forward slashes (`/Users/me/project/data/file.txt`)

- `np` — normalized path relative to project root (`data/file.txt`)

- `platform` — absolute path with the correct separators for the current platform

`np` is the same on every machine, every OS, as long as the project structure is the same.

This changes everything, and is a huge jump in path standardization.

## What about `pathlib`?

`pathlib` is great. It handles slash differences internally and gives you a nice object to work with.

But it doesn't know about your project. It doesn't auto-detect the root. It doesn't give you a consistent path that works everywhere. And it doesn't convert types for you.

`skpath` wraps `pathlib` and adds project awareness, so you don't have to make it aware yourself.

It also adds a bunch of cool things like `@autopath` and `AnyPath` to help you in your quest to make paths easy.

`pathlib.Path` handles this internally, but the moment you convert to string (for logging, storing, or passing to a library), you're back to platform-specific slashes.

```python
path = Path("config/settings.yaml")
str(path)

# "config/settings.yaml" on Mac, "config\\settings.yaml" on Windows
```

Here is a set of problems that `skpath` solves.

(start of dropdown section for 1)
1. `\` vs `/`

Windows uses `\`, everything else uses `/`. 

You write code on a Mac, push it, and your teammate on Windows gets broken paths.

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

With `skpath`

```python
path = SKPath("config/settings.yaml")

path.ap  # Always forward slashes: "/Users/me/project/config/settings.yaml"

path.np  # Always forward slashes: "config/settings.yaml"

path.platform  # platform specific

str(path)  # Always forward slashes (same as ap)
```

Need to pass a path to a Windows-specific tool or open a file? Use `path.platform`. Want to log or store paths consistently? Use `path.ap` or `path.np`.

`SKPath` normalizes to forward slashes everywhere, except for `platform`.

(end of dropdown section for 1)

(start of dropdown section for 2)
2. Relative paths

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

With `skpath`
```python
path = SKPath("data/file.txt")
```

So much cleaner.

`SKPaths` are awesome because they actually store 3 paths.

- stores absolute path
- also auto detects the project root and stores the path relative to it

- (also stores platform specific separator absolute path)

`SKPaths` are automatically cross-platform compatible.

When you work with `SKPath` objects across machines or even operating systems, as long as the project root is the same, the paths will work the same.

So now you can just `SKPath` everything and not have to worry about platform issues, or having to manually relate paths to the root.

(end of dropdown section for 2)

(start of dropdown section for 3)
3. Project root related issues

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

With `skpath` - *1 line* 2 different ways

```python
PROJECT_ROOT = get_project_root()
```

```python
PROJECT_ROOT = SKPath().root
```

With `skpath` you can also use different roots quickly and easily.

- you can add a `setup.sk` file to your project root to guarantee detection (it will look for things like `setup.py` even if you don't do this)

- you can use `set_custom_root` to set a custom root that all `SKPath` objects will use

- you can use the `CustomRoot` context manager to temporarily set a custom root for a code block for things like testing

Note that `SKPaths` are created with the project root they were given, so either use a custom root or don't.

(end of dropdown section for 3)

(start of dropdown section for 4)
4. Figuring out if you need to use a `Path` or a `str`

Even if you are in an IDE/code editor, figuring out what type of path you need to use for what function across a whole project base is tedious and annoying.

You have to make everyone use either `Path` or `str`, or let everyone code how they want and then hover over every function using paths to see the expected types.

### `@autopath` does this for you.

```python
from suitkaise.skpath import autopath

@autopath()
def function_that_uses_strs(path: str, ...):

    # changes all Paths to strings for you before passing them in


@autopath()
def function_that_uses_paths(path: Path, ...):

    # changes all strings to Paths for you before passing them in
```

All you have to do is slap `@autopath()` on the function and it will automatically convert the paths to the types that you expect, and automatically normalize them as well.

There is also another way to do this: the `AnyPath` type.

`AnyPath` is a union of `str`, `Path`, and `SKPath`.

This allows you to quickly update your code to use the superior `SKPath` type, while not breaking previous code.

```python
from suitkaise.skpath import AnyPath

def function_that_uses_any_paths(path: AnyPath, ...):

    # allows you to accept all 3 path types 
    # without having to create unions every time
```

And when you combine them...

```python
from suitkaise.skpath import autopath, AnyPath

@autopath()
def function_that_uses_any_paths(path: AnyPath, ...):

    # automatically converts strs and Paths to SKPaths for you
    # gives you access to the more awesome SKPath quickly
```

I do a lot of solo coding, and even I was having trouble standardizing path code! When working in a team, don't even get me started.

I think this is a game changer.

(end of dropdown section for 4)

(start of dropdown section for 5)
5. Comparing paths

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

With `skpath`

```python
from suitkaise.skpath import SKPath, autopath
import json

LOG_FILE = "processed_files.json"

@autopath()
def process_file(path: SKPath, processed: set[SKPath]):

    if path.np in processed:
        print(f"Skipping {path.np}, already processed")
        return
    
    # ... do the actual processing ...
    
    processed.add(path.np)
    save_processed(processed)
```

The log file now contains:

```json
["data/report.csv"]
```

Same on Murphy's Mac. Same on Gurphy's Windows PC. Same on someone else's Linux desktop.

(end of dropdown section for 5)

(start of dropdown section for 6)
6. Caller file pathfinding

Sometimes you need to know which file called your function — for logging, for relative path resolution, for debugging.

Without `skpath` - *13 lines*
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

With `skpath` - *1 line* 3 ways
```python
caller = SKPath()
```

```python
caller = get_caller_path()
```

```python
@autopath(use_caller=True) # 1
def function_that_uses_caller_path(path: SKPath):

    # path will be the caller's file path if not explicitly provided
```

(end of dropdown section for 6)

(start of dropdown section for 7)
7. Using paths as dict keys or in sets

You want to track which files you've seen. Simple, right?

Without `skpath` - *8 lines*
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

# this might mess up and have duplicate paths
len(seen)
```

You have to manually normalize every time you add or check. And if you forget once, you get duplicates or missed lookups.

With `skpath`
```python
from suitkaise import skpath # 1

seen = set() # 2

@skpath.autopath() # 3
def mark_seen(path: skpath.AnyPath):
    seen.add(path)

@skpath.autopath() # 4
def is_seen(path: skpath.AnyPath):
    return path in seen

len(seen) # no duplicates
```

`SKPath` objects hash and compare using their normalized path (`np`), so different representations of the same file are recognized as equal.

Works in sets, works as dict keys, no extra effort.

(end of dropdown section for 7)



