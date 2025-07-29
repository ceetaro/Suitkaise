# fdl - Formatting, Debugging, and Logging for suitkaise

**NOTE: F-strings are not supported by fdl print. Use `<>` syntax instead!**  
**All commands are prefaced by a `/` as well.**

**PERFORMANCE ARCHITECTURE:**
- **Thread-safe design**: Custom progress bars, spinners, and tables avoid Rich's threading bottlenecks
- **Batched updates**: Progress bars use submitted updates with smooth animation
- **Cached terminal detection**: Terminal width/capabilities detected once at startup

## Goal API Design

The FDL API aims to provide powerful formatting, debugging, and logging capabilities with an intuitive command-based syntax:

### Basic Logging
```python
from suitkaise import fdl

# Create reporter from current file
rptr = fdl.log.from_current_file()

# Standard logging with variable substitution
rptr.info("Module initialized: <module_name>", (module_name,))
rptr.error("Connection failed: <error>", (connection_error,))

# Quick context switching
with fdl.log.Quickly("different/module") as lq:
    lq.warning("Temporary issue: <issue>", (issue,))
```

### Advanced Formatting
```python
# Rich text formatting with commands
fdl.print("</bold, red>Critical Error:</end bold, red> System failure detected")

# Time and date formatting
fdl.print("Login at <time:login_timestamp>", (login_timestamp,))
fdl.print("Session lasted <elapsed:start_time>", (start_time,))

# Complex nested structures with smart coloring
fdl.print("Data structure: <nested_data>", (complex_dict,))
```

### Progress Tracking
```python
from suitkaise.fdl import ProgressBar

# Thread-safe progress bars with batched updates
bar = ProgressBar(100)
bar.display_bar(color="green")
bar.update(25, "Processing data...")
```

### Tables and Layout
```python
# Smart table creation with formatting
table = fdl.Table(box="rounded")
table.add_columns(["Process", "Memory", "Status"])
table.populate("worker_1", "Memory", "128MB")
table.display_table()
```

The API emphasizes simplicity and performance while providing Rich-like capabilities with better threading support and cleaner syntax.

## Core Philosophy

FDL transforms complex formatting and logging into intuitive, command-based operations that feel natural while maintaining high performance and thread safety. The system uses caching and batched updates to provide smooth user experiences without the bottlenecks found in other formatting libraries.

## Key Features

### Command-Based Formatting
- Simple syntax: `</bold, red>text</end bold, red>`
- No F-string conflicts - uses `<variable>` syntax
- Cached command processing for performance
- Thread-safe operation

### Smart Time Handling
- Multiple time formats: `<time:>`, `<date:>`, `<elapsed:>`
- Timezone support with daylight savings
- Smart unit selection (days, hours, minutes, seconds)
- Configurable precision and display options

### Advanced Data Visualization
- Nested collection formatting with level-based coloring
- Type-sorted display within collections
- Custom progress bars and spinners
- Flexible table layouts

### Integrated Logging System
- File and key-based reporters
- Multiple output destinations (console, files)
- Configurable message formats
- Context-aware logging with quick switching

### Performance Optimizations
- Cached ANSI code generation
- Batched progress bar updates
- Terminal capability detection at startup
- Thread-safe design throughout