# FDL Info

## Module Status
- **Implementation**: In development
- **Priority**: Medium (Gateway module)
- **Dependencies**: None (foundational module)

## Key Components

### Format Functions
- `fd.fprint()` - Display-friendly formatting
- `fd.dprint()` - Debug formatting with type annotations
- `fd.set_dprint_level()` - Debug level filtering

### Data Type Support
- Lists, dictionaries, sets, tuples
- Primitive types (int, float, bool, None)
- Complex types (bytes, complex, range)
- Nested data structures

### Time Formatting
- Default time/date formats
- Custom format strings (`{hms6:now}`, `{datePST:now}`)
- Threshold-based automatic formatting
- Timezone support

## Integration Points
- **All SK Modules**: Universal data formatting
- **Report Module**: Enhanced logging output
- **Debug Systems**: Structured debug information

## Use Cases
- Debug output with type information
- Clean display formatting for end users
- Data structure visualization
- Performance debugging
- Log formatting

## Performance Features
- Efficient recursive formatting
- Configurable detail levels
- Color-coded output support
- Large data structure handling

## Inner Workings and Implementation Details

### Setting up logging
```python
from suitkaise import fdl

# report from current file
rptr = fdl.log.from_current_file()

# or from another file (like a central module depending on this file)
central_rptr = fdl.log.from_file("parent_dir/central_module")

# report from a keyword instead of a file path
bus_rptr = fdl.log.from_this_key("Event_Bus")

# basic logging
rptr.info("Module initialized successfully.")

# using context manager to quickly use a different reporter
# if not a valid in project file path (and not a valid path at all) assumes entry is key
# you could just create another reporter, but...
# this removes the "lq" reporter from memory and looks and feels more intuitive
try:
    # some operation
    pass
except Exception as e:
    with fdl.log.Quickly("a/different/file/path") as lq:
        lq.error("<value1> was set to None so <value2> was not initialized. <e>", (value1, value2, e))

# log same message using multiple reporters
value1 = "database_connection"
value2 = "user_session"
msg = "<value1> was set to None so <value2> was not initialized."
values = (value1, value2)

rptr.warning(msg, values)
central_rptr.warning(msg, values)
bus_rptr.warning(msg, values)
```

### Advanced Formatting Implementation
```python
from suitkaise import fdl

# adding color and text formatting to messages

# adding text formatting
fdl.print("</bold>This is bold text</end bold>")

# adding text color
fdl.print("</red>This is red text</end red>")
fdl.print("</ #FFFFFF>This is white text</end #FFFFFF>")
fdl.print("</rgb(0, 0, 0)>This is black text</end rgb(0, 0, 0)>")

# adding background color
fdl.print("</red, bkg blue>This is red text on a blue background</end red, bkg blue>")

# putting all 3 together
fdl.print(
    "</italic, green, bkg rgb(165, 165, 165)>"
    "This is italicized green text on a light gray background"
    "</end italic, green, bkg rgb(165, 165, 165)>"
    )

# resetting completely using </end all> and </reset>
fdl.print(
    "</italic, green, bkg rgb(165, 165, 165)>"
    "This is italicized green text on a light gray background"
    "</end all>" # or /reset
    )
```

### Time and Date Implementation
```python
from suitkaise import fdl
import time

from_64_sec_ago = time.time() - 64

# print current time in default timestamp format (hh:mm:ss.123456)
fdl.print("<time:>")

# print a given timestamp in default timestamp format
fdl.print("<time:from_64_sec_ago>", (from_64_sec_ago,))

# print current time in default date form (dd/mm/yy hh:mm:ss)
fdl.print("<date:>")
# print a given timestamp in date form
fdl.print("<date:from_64_sec_ago>", (from_64_sec_ago,))

# print a given timestamp in a different format
# July 4, 2025
fdl.print("<datelong:>")

# print the day of the week
# resutls in day of the week
fdl.print("<day:>")
fdl.print("<day:from_64_sec_ago>", (from_64_sec_ago,))

# using a command
# 16:30 -> 4:30 PM (accounts for daylight savings)
fdl.print("</12hr, no sec><time:>")

# timezones account for daylight savings
fdl.print("</tz pst><time:from_64_sec_ago>", (from_64_sec_ago,))

# print elapsed time from a timestamp to now in smart format
# automatically shows appropriate units: days, hours, minutes, seconds
# only shows non-zero units for clean output
# ex. timestamp from 2 hours 17 minutes ago -> "2h 17m 54.123456s"
# ex. timestamp from 1 day 5 hours ago -> "1d 5h 23m 12.654321s"  
# ex. timestamp from 30 seconds ago -> "30.123456s"

self.login_time = time.time() - 8274.743462
# "Login was (some time) ago"
fdl.print("Login was <time_ago:self.login_time>", (self.login_time,))

next_meeting = time.time() + 8274.743462
# "(some time) until"
fdl.print("<time_until:self.login_time> next meeting", (next_meeting,))

# "Time to complete: (some time)"
# elapsed finds absolute value of difference between given time float and current time
execution_started_at = time.time() - 68
fdl.print("Time to complete: <elapsed:execution_started_at>", (execution_started_at,))
```

### Complex Data Structure Formatting
```python
from suitkaise import fdl

my_nested_collection = { # level 1
    'my_list': [ # level 2
        1, 2, 3, 4, 5, 6
    ], # level 2
    'my_nested_set': set( # level 2
        ( # level 3
            1, 2, 'banana', 3.14
        ), # level 3
        { # level 3
            'name': 'Alice',
            'occupation': 'Barista',
            'scores': { # level 4
                'q1': [88, 82, 83],
                'q2': [87, 72, 78],
                'q3': [80, 81, 79],
                'q4': [78, 75, 84]
            } # level 4
        } # level 3
    ), # level 2
    'my_tuple': (
        # set and list are level 3
        "1", 38.26, set('a', MyClass, 'c'), ["hello", "world"]
    ) # level 2
} # level 1

fdl.print("<nested_collection>", (my_nested_collection,))
```

### Progress Bars and Tables Implementation
```python
from suitkaise.fdl import ProgressBar

# number of increments before progress bar completes
bar = ProgressBar(100)
bar.display_bar(color="green")

# updating progress bar N number of increments
# Uses batched updates for smooth performance in threading
# Still animates bar progression smoothly
# message goes under the bar, and line with message gets replaced when another message comes in.
bar.update(7, "message")

# if this bar reaches 100, text can be outputted again.

# blocking bar from updating further (stays in output, but does not complete.)
# allows text to be outputted again.
bar.stop()

# Creating tables
table1 = fdl.Table(box="rounded")
# add a single column (max: 3)
table1.add_column("UI Process")
# add multiple (takes a list or tuple)
table1.add_columns(["Parser Process", "Event Hub Process"])

# add rows the same way (max: 10)
table1.add_row("Memory Usage")
table1.add_rows(["Num Threads", "Time Created", "Time Ended"])

# populate cells using int coords (1-based)
table1.populate(1, 1, "str or str(value)")
# populate cells using row and column names (order doesn't matter as long as rows and columns have unique names)
table1.populate("Parser Process", "Memory Usage", "str or str(value)")

# printing table
fdl.print("<table1>", (table1,))
# or...
table1.display_table()
```

### Error Handling Implementation
FDL uses a hybrid error handling approach:
- **fdl internal errors**: Use standard Python traceback (for debugging fdl itself)
- **User/library errors**: Use beautiful custom error display

Custom error features:
- Clean file paths (relative to project root) using SKPath internal objects
- Code context with surrounding lines  
- Each stack frame in a separate box
- Simple but effective ANSI coloring
- Optional debug mode with local variables
- Thread-safe with no performance bottlenecks

### Performance Architecture Details
The system uses several optimization strategies:
1. **Cached ANSI codes**: Simple commands cached on launch
2. **Color conversion caching**: Hex and RGB colors cached on first encounter
3. **Format object caching**: fdl.Format objects cached for reuse
4. **Batched updates**: Progress bars use batched updates for smooth animation
5. **Terminal detection**: Width and capabilities detected once at startup
6. **Smart text wrapping**: Handles spaces, dashes, periods, commas, and other punctuation