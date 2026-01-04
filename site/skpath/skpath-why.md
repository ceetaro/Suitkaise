/*

why the skpath module was created

what problems it solves

each numbered section is a dropdown.

*/

text = "
File paths are a pain to work with.

(start of dropdown section for 1)
1. `\` vs `/`

Windows uses `\`, everything else uses `/`. You write code on a Mac, push it, and then everything breaks on Windows.

Or even worse, you have cross platform compatibility issues on a live build.

Let's make a function that opens and reads a file, scanning it for a specific string.

```python
def scan_file_for_matches(file_path: str, search_string: str):

    # open and read file
    with open(file_path, "r") as f:
        content = f.read()

    # scan for matches
    matches = [line for line in content.split("\n") if search_string in line]

    return matches
```

Without `skpath` - *14 lines*
```python
from pathlib import Path # 1
# import os works similarily

def find_project_root(): # 2
    current = Path(__file__).resolve().parent # 3
    while current != current.parent: # 4
        if (current / "pyproject.toml").exists(): # 5
            return current # 6
        if (current / ".git").exists(): # 7
            return current # 8
        current = current.parent # 9
    raise RuntimeError("Could not find project root") # 10

PROJECT_ROOT = find_project_root() # 11

def scan_file_for_matches(file_path: str | Path, search_string: str):

    # normalize string
    p = Path(file_path) # 12
    p = p.resolve() # 13
    p = p.relative_to(PROJECT_ROOT) # 14

    # # open and read file
    # with open(p, "r") as f:
    #     content = f.read()

    # # scan for matches
    # matches = [line for line in content.split("\n") if search_string in line]

    # return matches

```
The most annoying part of this is that you have to manually find or calculate the project root each time, and every dev likely does it slightly differently.

You can't just use a hardcoded file path for the root either because each person running the code will likely have a different path to the project.

And, the moment you log, print, or store the path in a different file, it goes back to the original platform's slashes.

Also, everyone has to do this each time.

And, third-party libraries are a total crapshoot when it comes to even possibly accepting `pathlib.Path` objects.

Most of the time, you either have to convert it and fix it before passing it in as a string, or pass in the original string path and work with the path in the function.

Pure hell.


With `skpath` - *2 lines*
```python
from suitkaise.skpath import autopath # 1

@autopath() # 2
def scan_file_for_matches(file_path: str, search_string: str):

    # # open and read file
    # with open(file_path, "r") as f:
    #     content = f.read()

    # # scan for matches
    # matches = [line for line in content.split("\n") if search_string in line]

    # return matches
```

`@autopath` does all of what was happening above. 

Then, it passes the normalized path into the function, choosing the correct type based on the param type annotation.

No need to edit any function code to make paths work.

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

`SKPaths` are awesome because they actually store 2 paths.

- stores absolute path
- also auto detects the project root and stores the path relative to it

(`SKPaths` are also automatically cross-platform compatible)

Then, when you work with `SKPath` objects across machines or even operating systems, as long as the project root is the same, the paths will work the same.

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
4. String manipulation

(end of dropdown section for 4)


(start of dropdown section for 5)
5. Figuring out if you need to use a `Path` or a `str`

(end of dropdown section for 5)

(start of dropdown section for 6)
6. Comparing paths

(end of dropdown section for 6)

(start of dropdown section for 7)
7. Caller file pathfinding

(end of dropdown section for 7)


