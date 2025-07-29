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