# FDL - Formatting, Debugging, and Logging for suitkaise

**NOTE: F-strings are not supported by fdl print. Use `<>` syntax instead!**  
**All commands are prefaced by a `/` as well.**

**PERFORMANCE ARCHITECTURE:**
- **Thread-safe design**: Custom progress bars, spinners, and tables avoid Rich's threading bottlenecks
- **Batched updates**: Progress bars use submitted updates with smooth animation
- **Cached terminal detection**: Terminal width/capabilities detected once at startup

## Setting up logging

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

## Setting up logging, cont: adjusting default settings

```python
from suitkaise import fdl

# change overall logging settings during program initialization
lsetup = fdl.log.get_setup()

# auto newline after every log statement (default=True)
lsetup.set_auto_newline(True)

# toggle sending to console (default=False)
lsetup.log.send_to_console(True)

# toggle sending to file (default=False)
lsetup.log.send_to_files(True)

# log to a certain file
lsetup.log_to_file("path/to/file")
# creates a new file every run
lsetup.create_log_file_in("path/to/dir")
# create a file in .sk.logs directory
lsetup.create_log_file() # no args

# enable/disable color (default=True)
lsetup.use_color(True)
# enable/disable unicode (unicode automatically falls back when outputting to file)
# auto detects unicode support and forces false if not supported
lsetup.use_unicode(True) # default=True

# wrap words that don't fit in remaining line space by putting them on the next line
# fdl.print functions automatically wrap! (see next section for fdl.print)
lsetup.use_wrapping(True) # default=True

# set default message format
time_config = {
    # using local time will also display timezone (timezone dimmed)
    'use_local_time': True, # default: UTC

    # if set to false, uses 12 hour cycle (13:20 = 1:20 pm)
    '24_hour_time': False, # default: True

    # dim hour numbers so that it is easier to read rest of timestamp
    'dim_hours': True, # default: False
    'dim_minutes' True, # default: False

    # use this many decimal places after seconds
    'decimal_places_after_seconds': 6
}
time_fmt = TimeFormat(time_config)
fmt = '<fdl.time> - <fdl.name> - <fdl.msgtype> - <fdl.message>'

# log format, fdl configs
lsetup.set_format(fmt, (time_fmt,))

# set what loggers you want to listen to
# listens to all loggers by default, but you can stop listening to certain ones
lsetup.stop_listening_to("paths_or_keys")

# see what we are ignoring
ignoring = lsetup.not_listening_to
# see what we are listening to
listening = lsetup.listening_to

# return original status
lsetup.listen_to("paths_or_keys_being_ignored")
# reset so that all are listened to
lsetup.listen_to()
```

## Setting up logging, cont: adjusting logger specific settings

```python
from suitkaise import fdl

# change individual logger settings, overrides default or SetupLogging behavior
rptr = fdl.log.from_current_file()

rptr.set_auto_newline(True)
rptr.log.send_to_console(True)

rptr.send_to_files(True)
rptr.create_log_file()
rptr.use_color(True)
# unicode is a program level option
rptr.use_wrapping(True)

# set default message format
config = {
    'use_local_time': False,
    '24_hour_time': True,
    'dim_hours': True,
    'dim_minutes' False,
    'decimal_places_after_seconds': 2
}
rptr_time_fmt = TimeFormat(config)
rptr_fmt = '<fdl.time> - <fdl.name> - <fdl.msgtype> - <fdl.message>'
rptr.set_format(rptr_fmt, (rptr_time_fmt,))
```

## Basic logging functions

```python
from suitkaise import fdl

rptr = fdl.log.from_current_file()

# standard logging
rptr.info("value1: <value1>, value2: <value2>", (value1, value2))
rptr.debug("Debug message", (debug_value,))
rptr.warning("Warning message", (warning_data,))
rptr.error("Error occurred", (error_info,))
rptr.critical("Critical issue", (critical_data,))

# success or fail
rptr.success("Operation completed", (result,))
rptr.fail("Operation failed", (error,))

# quick state messages
rptr.setToNone("Variable <var_name> set to None", (var_name,))
rptr.setToTrue("Flag <flag_name> enabled", (flag_name,))
rptr.setToFalse("Flag <flag_name> disabled", (flag_name,))

# save and load
rptr.savedObject("Object saved", (object_info,))
rptr.savedFile("File saved to <path>", (file_path,))
rptr.loadedObject("Object loaded", (object_info,))
rptr.loadedFile("File loaded from <path>", (file_path,))
rptr.importedObject("Imported <obj_name>", (obj_name,))
rptr.importedModule("Imported module <module>", (module_name,))

# general status (will add more)
rptr.scanning("Scanning <directory>", (directory,))
rptr.scanned("Scanned <count> files", (file_count,))
rptr.queued("Task queued", (task_info,))
rptr.leftQueue("Task dequeued", (task_info,))
rptr.leftQueueEarly("Task removed early", (task_info,))

# custom message type
rptr.custom(
    "value1: <value1>, value2: <value2>", 
    (value1, value2),
    "custom message type"
)
```

## Adding color and text formatting to messages

```python
from suitkaise import fdl

# getting available default colors, which are:
# red, orange, yellow, green, blue, purple
# magenta, cyan, pink, brown, tan,
# black, dark gray, gray, light gray, white
fdl.get_default_color_names()

# getting default text formatting
# bold, italics, underline, strikethough
fdl.get_default_text_formatting()

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

# can add multiple text formats at once
fdl.print("</bold, underline>This is bolded and underlined text</end bold, underline>")

# order doesn't matter, unlike rich
# but commands must be separated by commas
fdl.print(
    "</italic, bkg green, black, bold>"
    "This is bolded, italicized, black text on a green background."
    "</reset>"
    )

# can remove some but not all
fdl.print(
    # add your color and text formatting
    "</italic, bkg green, black, bold>"

    "This is bolded, italicized, black text on a green background.\n"

    # end some of it
    "</end black, italic>"

    "This is now bold default color text, still on a green background.\n"

    # you don't have to explicitly end colors, you can just change them
    "</blue, strikethrough, bkg yellow>"

    # but you have to explicitly end text formatting, as they wont override each other!   
    "</end bold>"

    "This is now blue strikethough text on a yellow background"

    # if you aren't going to change the color/text anymore, you don't have to explicitly end things
    )

# loggers support the same formatting options!
rptr.error(
    "</bold, orange>"
    "<value1> was set to None so <value2> was not initialized.",
    # remember, no need to /end if the whole sentence uses the formatting!
    (value1, value2)
)
```

## Explicit time and date printing

### We have 7 time and date display commands: time, date, datelong, elapsed, time_ago, time_until, and day.

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

# use commands to modify elapsed display
fdl.print("Logged in at</no sec><time_ago:self.login_time>", (self.login_time,))

# <elapsed:>, <time_until:>, and <time_ago:> are NOT supported

# printing time and values. VALUE ORDER MATTERS!
import os
pid = os.getpid()
value1 = True
fdl.print(
    "Process <pid> (<time:from_64_sec_ago>): value1 set to <value1>.",
    (pid, from_64_sec_ago, value1)
)
# or... without an explicit time value (<time:> uses current time!)
fdl.print(
    "Process <pid> (<time:>): value1 set to <value1>.",
    (pid, value1)
)

# variable name doesn't matter inside string, but please add the names to avoid errors!
# could technically do... won't cause issues if attribute names change
fdl.print(
    "Process <process> (<time:a_time>): value1 set to <1>.",
    (pid, from_64_sec_ago, value1)
)
```

### Key Object Types:

#### Time Objects:
- `<time:>` - Current time in hh:mm:ss.microseconds format
- `<time:timestamp>` - Specific timestamp in same format
- `<date:>` - Current time in date format
- `<date:timestamp>` - Date and time in dd/mm/yy hh:mm:ss format
- `<datelong:>` - Current time in datelong format
- `<datelong:timestamp>` - Long date format like "January 01, 2022"

#### Elapsed Objects:
- `<elapsed:timestamp>` - Elapsed time between timestamp and current time
- `<time_ago:timestamp>` - Elapsed time between timestamp and current time + "ago"
    fails if timestamp is greater than current time
- `<time_until:timestamp>` - Elapsed time between timestamp and current time + "until"
    fails if timestamp is less than current time
- Format: Shows only non-zero units in "3d 2h 15m 30.123456s" style
- Automatically chooses appropriate units (days, hours, minutes, seconds)

#### Time Commands:
- `</12hr>` - Use 12-hour format with AM/PM (removes leading zeros: "4:00 PM" not "04:00 PM")
- `</tz pst>` - Convert to timezone (supports daylight savings)
- `</no secs>` - Hide seconds from time display, unless timestamp is less than 60 seconds
- `</round>` - round to nearest second
- `</round N>` - round to nearest Nth of a second (round 2 = round to hundredths place)
- `</no mins>` - Hide minutes and seconds from time display if greater than 1 hour
- `</no hrs>` - Hide hrs, mins, secs from time display if greater than 1 day
- `</no days>` - Hide days from time display and just display more than 24 hours (ex. 38 hours). gets overridden by /no hrs
- `</smart time 1>` - only display the largest unit of measurement (ex. display hours if >60 min and <1 day)
- `</smart time 2` - display the 2 largest units of measurement for that timestamp

#### Usage Examples:
```python
# Absolute time formatting
login_time = # a login time
fdl.print("User logged in at </12hr, tz est><time:login_time>", (login_time,))
# Result: "User logged in at 3:30:45 PM"

# Relative time formatting  
fdl.print("User logged in <time_ago:login_time>", (login_time,))
# Result: "User logged in 1h 23m 45.123456s ago"
```

## Creating Format objects

```python
from suitkaise import fdl

# create a format (uses fast FDL Format system - 52x faster than Rich Style!)
greentext_bluebkg = fdl.Format(
    name="greentext_bluebkg", 
    format="</green, bkg blue>"
)
# use a format
fdl.print(
    "</fmt greentext_bluebkg>"
    "This is green text with a blue background"
)

# create a format from a Format 
# (cannot override previously set formatting (text color, bkg color))
format2 = fdl.Format(
    name="format2",
    format="</fmt greentext_bluebkg, bold, italic>"
)
fdl.print(
    "</fmt format2, underline>"
    "This is green, bolded, italicized, underlined text on a blue background."
    "</end format2>"
    "This is now just underlined text."
)
```

## Error handling with fdl

**fdl uses a hybrid error handling approach:**
- **fdl internal errors**: Use standard Python traceback (for debugging fdl itself)
- **User/library errors**: Use beautiful custom error display

**Custom error features:**
- Clean file paths (relative to project root) using SKPath internal objects
- Code context with surrounding lines  
- Each stack frame in a separate box
- Simple but effective ANSI coloring
- Optional debug mode with local variables
- Thread-safe with no performance bottlenecks
- option to add/remove locals (locals are name, type, and support simple values only. if a local is not a simple value type, or if it is a collection, shows only name and type)

```
TRACEBACK (red and bold)
═════════════════════════════════════════════════════════════════════

╭──────────────────────────── Frame 1 ──────────────────────────────╮
│ src/myproject/main.py, line 45                                    │
│                                                                   │
│   42 │ def level_1():                                             │
│   43 │     session_id = "abc123"                                  │
│   44 │     timestamp = 1641234567                                 │
│ ❱ 45 │     return level_2()                                       │
│   46 │                                                            │
│                                                                   │
│ Local variables:                                                  │
│   session_id (str) = 'abc123'                                     │
│   timestamp (int) = 1641234567                                    │
╰───────────────────────────────────────────────────────────────────╯

╭──────────────────────── Frame 2 (current) ────────────────────────╮
│ src/myproject/utils.py, line 12                                   │
│                                                                   │
│   10 │     data = [1, 2, 3]                                       │
│   11 │     config = {"debug": True}                               │
│ ❱ 12 │     return data[10]  # IndexError                          │
│   13 │                                                            │
│                                                                   │
│ Local variables:                                                  │
│   username (str) = 'alice'                                        │
│   data (list) = [...]                                             │
│   config (dict) = {...}                                           │
╰───────────────────────────────────────────────────────────────────╯

╭─────────────────────────── Exception ─────────────────────────────╮
│ IndexError: list index out of range                               │
╰───────────────────────────────────────────────────────────────────╯
```

## Using debug mode

### - Debug mode adds a type annotation right after the value, so you know what the value is. It also prints strings as is, without any formatting.

![debug mode](debug_mode.png "Debug Mode")

```python
from suitkaise import fdl
value1 = 32

# use direct function
fdl.dprint("value1 was set to <value1>.", (value1,))

# use formatting
fdl.print("</debug>value1 was set to <value1>.", (value1,))

# get type annotation individually
fdl.print("value1 was set to <type:value1>.", (value1,))
```

## Printing code blocks and markdown files

```python
from suitkaise import fdl # line 1

def fibonacci(n): # line 3
    """Calculate fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2) # line 7

# print code from line 3-7 in paraiso dark theme
fdl.codeprint(3, 7, "paraiso-dark")

# available syntax themes from rich:
# material, monokai, native, fruity, vim, rrt,
# paraiso-dark, solarized-dark, github-dark,
# nord, nord-darker, gruvbox-dark

# printing markdown text in a python file
fdl.mdprint(start_line, end_line)

# printing a .md file (will print as code if not a MarkDown file)
fdl.mdfileprint("path/to/file.md")
```

## Printing out complex, nested value structures

When we have a nested structure of collections (dicts, lists, tuples, and sets), we format them in a way that makes them easier to read.

Complex structures get printed to the 6th level of nesting. Based on how many levels a collection is nested, we color its brackets/parentheses a different color.

Level 1 (outermost collection) is red, then orange, yellow, green, blue, and purple. The colors are designed to be colorblind friendly.

Brackets/parentheses are also bolded. Keys of dicts are bolded and colored the same color as their dict's brackets.

Additionally, we sort data in collections by type, and annotate the type after we have listed out all of that collection's values of said type.

![example nested structure](nested_structure.png "Nested Structure Example")

![6 layered collection](too_many_layers.png)

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

## Using decorators to set formats for functions

```python
from suitkaise import fdl

@fdl.autoformat("</bkg dark gray>")
def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        pass
    else: 
        n = fibonacci(n-1) + fibonacci(n-2)
    # auto applies format
    fdl.print("Result: <n>", (n,))
    # disable autoformat
    fdl.print("</end autofmt>Result: <n>", (n,))
    return n

# ❌ does not auto apply format to return value ❌
# (still applies format to print statements inside)
fdl.print("<result>", (fibonacci(8),))

# applies format to print statements inside function!
fibonacci(9)

# automatically set debug mode
@fdl.autodebug()
def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        pass
    else: 
        n = fibonacci(n-1) + fibonacci(n-2)
    # auto applies debug mode
    fdl.print("Result: <n>", (n,))
    # disable autodebug
    fdl.print("</end autodebug>Result: <n>", (n,))
    return n
```

## Creating progress bars

Progress bars can be created, and when they do, you cannot print anything new to the terminal until it completes, is removed, or stopped (except for progress bar messages)

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
```

## Creating spinners and boxes

**Spinners**
```python
from suitkaise import fdl

fdl.print("<spinner:arrows>a message") 
fdl.print("<spinner:dots>a message")
fdl.print("<spinner:letters>a message")

# or use a command:
fdl.print("</spinner arrows>a message")

# adding color and background to a spinner is exactly the same as text!
# does not support text formatting like bold, italic, etc.

# you can only have one active spinner at a time. if a new spinner is created, the last one stops.

# stopping a spinner manually
fdl.stop_spinner()
```

**Boxes**
```python
from suitkaise import fdl

# supported: square, rounded, double, heavy, heavy_head, horizontals 
# (fallback: ascii)

# print a whole message in one box
fdl.print("</box rounded>a message")

# or some in a box and some out
fdl.print(
    "</box double>"
    "a message in a box"
    "</end box>"
    "\na message outside the box"
)

# adding a title to the box
fdl.print("</box rounded, title Important>a message")

# adding a color to the box (if no color, takes current text color)
fdl.print("</box rounded, title Important, green>a message")

# justifying box (boxes are left by default, but box text is centered by default!)
fdl.print("</box rounded, title Important, green, justify right>a message")
```

## Justifying text

```python
from suitkaise import fdl

fdl.print("</justify left>a message justified left")
fdl.print("</justify right>a message justified right")
fdl.print("</justify center>a message justified centered")

# default is left. changing justification or ending justification creates a new line unless justify is already left. default inside boxes is center
```

## Creating tables

```python
from suitkaise import fdl

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

# or a mix of both:
table1.populate("Event Hub Process", 3, "str or str(value)")

# set formatting for rows, columns, or cells
table1.set_cell_format(format=fdl.Format)
table1.set_row_format(format=fdl.Format)
table1.set_column_format(format=fdl.Format)

# column only table
table2 = fdl.ColumnTable()
# can only add columns, and a max of 10 rows down are available
table2.add_column("Component")
# or...
table2.add_columns("Component", "Status")

# populate cells by adding them to columns
# add a value to column 1 (adds to lowest y coordinate empty cell)
table2.populate_first_column(1, "CPU") # add to column 1, "row" 1 (1, 1)
# then, if you were to...
table2.populate_first_column(1, "GPU") # added to 1, 2 automatically

# adding to other columns requires you to add via (column 1 value, other column name)
table2.populate("CPU", "Status", "Very Busy")
# or...
table2.populate("CPU", 2, "Very Busy")

# row only table
table2 = fdl.RowTable()
# can only add rows, and a max of 3 columns over are available
table2.add_row("Component")
# or...
table2.add_rows("Component", "Status")

# populate cells by adding them to rows
# add a value to row 1 (adds to lowest x coordinate empty cell)
table2.populate_first_row(1, "CPU") # add to row 1, "column" 1 (1, 1)
# then, if you were to...
table2.populate_first_row(1, "GPU") # added to 2, 1 automatically

# adding to other rows requires you to add via (row 1 value, other row name)
table2.populate("CPU", "Status", "Very Busy")
# or...
table2.populate("CPU", 2, "Very Busy")

# depopulating and repopulating cells (does not update in real time)
table.depopulate(1, 3)
# cells CANNOT be overridden unless repopulate is used
table.repopulate(2, "Status", "Not Busy")

# printing table
fdl.print("<table1>", (table1,))
# or...
table1.display_table()
```

## Performance Architecture Summary

We have created a simpler, command-based system that allows all formatting to be done right in the string. It is clearer than Rich, and keeps it simpler so that overhead is less and users are not as overwhelmed. It gives options to adjust settings at the module level, the function level, and the individual string level. All formatting options are supported by our logging system as well! A logging system that improves on the standard logging and Rich logging with simpler, fine-tuned behavior.

We will start by creating private equivalents to all of these methods so that any printing or logging from suitkaise itself will match user defaults! Then, we will wrap the internal logic with public counterparts. ex. `format_ops._print` -> `fdl.print`.

## Implementation Plan

### Basic fdl printing 
1. Parser - DONE FOR NOW
2. Command processor and reconstructor
- converts simple commands (`</red>`, `</bold>`) directly to ANSI
- caches all simple command ANSI equivalents on launch

- converts simple combinations (`</red>, bold>`) directly to ANSI by combining cached simple command ANSI
- does not cache combinations, inefficient

- caches color conversions (`</ #FFFFFF>`, `</rgb(255, 0, 0)>`) on first encounter, storing reference to color code and ANSI equivalent

- supports IDE friendly hexing, where adding a `' ' ` after the `/` allows you to change color easily, and standard `</#FFFFFF>` without a space after `/`.

- caches `fdl.Formats` on first creation, and lookups later when user does `</fmt (an fdl.Format)>`

- for complex combinations like `</fmt base, rgb(255,0,0)>`, attempts lookups first for each entry and then combines ANSI. If a newly encountered color needs to be converted and cached for the first time, does that first and then combines.

3. fdl Format class DONE
4. Renderer - Combine everything into final output
- also handle output to other destinations (files, MarkDown and HTML)
5. Internal `_print()` functions that tie basic execution together

### Advanced objects
6. Time objects - `<time:>`, `<elapsed:duration>` handling DONE
7. Custom progress bar - using cached terminal width and batched updates with smooth animation
8. Custom spinners - global state, simple animation
9. Custom tables - pre-calculated layout, row/column limits
10. Error handler - custom, lightweight traceback system

### Logging system
11. Reporters - file and key based loggers
12. Message Types - Standard logging levels and other convenience messages (success, setToNone, etc.)
13. special Format classes - TimeFormat, NameFormat (WIP), TypeFormat (WIP), and message format (`fdl.Format`)

### Finishing Renderer
14. finish MarkDown and HTML output support

### API
15. Decorators - `@fdl.autoformat`, `@fdl.autodebug`
16. Public API - wrapping internal functions with public interface to match this conceptual code
17. Optimizations - reviewing and adjusting caching, speed, and resource usage

## Changes and Updates

All text now wraps smartly when encountering spaces, dashes, periods, commas, colons, semicolons, both slashes, question marks and exclamation points.

Removing user defaults. All formatting should be done inside strings using fdl format.

Box color does not inherit from text color automatically, must be set itself but you can do `</box ..., color current>` to get the same color.

Elapsed splits into 'time_elapsed', 'time_ago', and 'time_until', getting rid of respective commands.

Time commands are now set independently from time objects.

### New Processing Flow Example

Here would be the new flow:

User does something like this (i have separated lines for clearer viewing, python will concatenate this string):

```python
if self._is_online:
    fdl.print(
        '</cyan, bold>Time: </12hr, tz pst, no sec><time:></end cyan>'
        '</box rounded, color current, bkg gray, title <self.name>>'
        '</green, italic>Online</reset> since </cyan><time:self.time_connected_at>'
        '</end box></reset>'
        '</format warning>'
        '</justify center>'
        'Warning: This is an example warning outside of the status box.',
        (self.name, self.time_connected_at)
    )
```

Since we aren't using defaults anymore, we can always just create a new blank formatting state for every print, and don't have to worry about things like resetting.

Before starting, we will measure the initial terminal width. assuming a hard minimum width of 80.

First, we create a blank format state object. This tracks everything, including text formatting, text color and bkg color, values to append, if we are inside a box, box background color, time format settings, if we use days, hours, minutes, seconds, how many decimal points after seconds, and possibly more. we additionally have a ready to print variable, that tracks if encountered text pieces can be printed immediately, or if they are inside a box and have to wait. Then, we will store the tuple of variables given if variables were given.

Next, the parser will take this message, now concatenated to: 

`</cyan, bold>Time: </12hr, tz pst, no sec><time:></end cyan></box rounded, color current, bkg gray, title <self.name>></green, italic>Online</reset> since </cyan><time:self.time_connected_at></end box></reset></format warning></justify center>Warning: This is an example warning outside of the status box.`

And split it like this:

1. `</cyan, bold>`
2. `'Time: '`
3. `</12hr, tz pst, no sec>`
4. `<time:>`
5. `</end cyan>`
6. `</box rounded, color current, bkg gray, title <self.name>>`
7. `</green, italic>`
8. `'Online'`
9. `</reset>`
10. `' since '`
11. `</cyan>`
12. `<time:self.time_connected_at>`
13. `</end box>`
14. `</reset>`
15. `</format warning>`
16. `</justify center>`
17. `'Warning: This is an example warning outside of the status box.'`

Next, we sequentially process each split piece, updating the format state.

1. Updates text color to cyan and bold to true.
2. Prints `(ansi code for cyan and bold text)Time: ` making sure to handle text wrapping if needed.
3. Sets twelve_hour_time to true, timezone to 'pst', and use_secs to False.
4. Prints the current time using the current formatting settings and our time format.
5. Sets text color back to None.
6. Sets in box to True, text color remains the same, box bkg color to gray (text bkg color remains what it was), box title to str(self._values[1]), removes first value from tuple, and sets ready to print to false.
7. Sets text color to green and italic to true. stores ansi code string for current formatting in a box_text tracker.
8. Adds 'Online' to box_text.
9. Resets all text and background formatting other than box related vars. adds '(ansi reset code)' to box_text.
10. Adds ' since ' to box_text.
11. Sets text color to cyan. adds ansi code for cyan to box_text.
12. Adds formatted timestamp of the second value, removes value from tuple in format state obj
13. Generates box with smart text wrapping according to format state and box text string. resets all box vars.
14. Resets all text and background formatting other than box related vars.
15. Gets warning format ('</bkg yellow, black, bold>') and then processes it. this sets bkg color to yellow, sets text color to black, and bold to True.
16. Sets justify to center. sets ready to print to false.
17. Prints '(ansi code)Warning: This is an example warning outside of the status box.' after calculating justififcation and checking box status (currently not in a box). using terminal width to calculate text centering for each line. this is done by first applying text wrapping, then centering each line after.

No need to check what needs to be reset, as we can just release this object from memory and create a new one. if this is suboptimal performance wise, we can add hard reset logic to execute after all pieces have been processed, and use the same object. i think making new ones makes sense for multithreading purposes.