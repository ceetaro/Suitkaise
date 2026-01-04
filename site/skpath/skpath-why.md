/*

why the skpath module was created

what problems it solves

*/

text = "
File paths are a pain to work with.

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

---

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

---

3. Project root related issues

---

4. String manipulation

---

5. Figuring out if you need to use a `Path` or a `str`

---

6. Comparing paths

---

7. Caller file pathfinding




