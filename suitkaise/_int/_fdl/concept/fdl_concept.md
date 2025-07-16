# fdl - Formatting, Debugging, and Logging for suitkaise

**NOTE: F-strings are not supported by fdl print. Use `<>` syntax instead!**  
**All commands are prefaced by a `/` as well.**

**PERFORMANCE ARCHITECTURE:**
- Uses **hybrid approach**: Rich for static elements (Panels, Themes), custom implementations for performance-critical components
- **FDL Format system**: 52x faster than Rich Style, only 3x slower than direct ANSI when cached
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

# can add multiple text formats at once
fdl.print("</bold, underline>This is bolded and underlined text</end bold, underline>")

# order doesn't matter, unlike rich
# but commands must be separated by commas
fdl.print(
    "</italic, bkg green, black, bold>"
    "This is bolded, italicized, black text on a green background."
    "</end bkg green, bold, italic, black>"
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

# you can also set colors and text formatting for all messages
fdl.set_text_color("blue")
fdl.set_background_color("rgb(163, 211, 150)")
fdl.set_bold(True)
fdl.set_italic(True)
fdl.set_underline(True)
fdl.set_strikethrough(True)

# and check what these settings are:
if not fdl.underlining:
    fdl.set_underline(True)

if fdl.bkgcolor != "green"
    fdl.set_background_color("green")

if fdl.using_color:
    fdl.set_text_color(None)
    fdl.set_background_color(None)

# reset defaults
fdl.reset_to_default()

# color certain things
fdl.set_var_format("pink")

# values appear pink
fdl.print("<value1> was set to None so <value2> was not initialized.", (value1, value2))

# string variables appear bold black with green background
fdl.set_str_format(("bkg green", "bold", "black"))

# higlight certain words that aren't <values>
# "None" appears bold white, with red background
fdl.highlight("None", ("bkg red", "bold", "white"))

#
# formatting within the actual string being printed overrides outside settings!!!
#

# and some things, like "None", "True", and "False" have preset formats
# that will override highlighting in debug mode!

# loggers support the same formatting options!
rptr.error(
    "</bold, orange>"
    "<value1> was set to None so <value2> was not initialized.",
    # remember, no need to /end if the whole sentence uses the formatting!
    (value1, value2)
)

# check if a reporter is currently using color or text formatting
if rptr.using_color and rptr.italicizing:
    rptr.set_text_color(None)
    rptr.set_background_color(None)
    rptr.set_italic(False)
```


## Explicit time and date printing

### We have 4 time and date display commands: time, date, datelong, and elapsed.
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

# using a command
# 16:30 -> 4:30 PM (accounts for daylight savings)
fdl.print("</12hr, time:>")

# timezones account for daylight savings
fdl.print("</tz pst, time:from_64_sec_ago>", (from_64_sec_ago,))

# print elapsed time from a timestamp to now in smart format
# automatically shows appropriate units: days, hours, minutes, seconds
# only shows non-zero units for clean output
# ex. timestamp from 2 hours 17 minutes ago -> "2h 17m 54.123456s"
# ex. timestamp from 1 day 5 hours ago -> "1d 5h 23m 12.654321s"  
# ex. timestamp from 30 seconds ago -> "30.123456s"
timestamp_2h_ago = time.time() - 8274.743462
fdl.print("Login was <elapsed:timestamp_2h_ago> ago", (timestamp_2h_ago,))

# use commands to modify elapsed display
fdl.print("</no sec, elapsed:timestamp_2h_ago> ago", (timestamp_2h_ago,))

# you can also add time suffixes directly
fdl.print("Login was </time ago, elapsed:timestamp_2h_ago>", (timestamp_2h_ago,))

# elapsed with current time shows minimal elapsed (nearly 0)
fdl.print("Current moment: <elapsed:>")

# printing time and values
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
```
### Key Object Types:

#### Time Objects:
- `<time:>` - Current time in hh:mm:ss.microseconds format
- `<time:timestamp>` - Specific timestamp in same format
- `<date:timestamp>` - Date and time in dd/mm/yy hh:mm:ss format
- `<datelong:timestamp>` - Long date format like "January 01, 2022"

#### Elapsed Objects:
- `<elapsed:>` - Elapsed time from current moment (essentially 0)
- `<elapsed:timestamp>` - Elapsed time from timestamp to now
- Format: Shows only non-zero units in "3d 2h 15m 30.123456s" style
- Automatically chooses appropriate units (days, hours, minutes, seconds)

#### Time Commands:

- `</12hr>` - Use 12-hour format with AM/PM (removes leading zeros: "4:00 PM" not "04:00 PM")
- `</tz pst>` - Convert to timezone (supports daylight savings)
- `</time ago>` - Add "ago" suffix to time displays
- `</time until>` - Add "until" suffix to time displays
- `</no sec>` - Hide seconds from time display

#### Usage Examples:
```python
# Absolute time formatting
login_time = time.time() - 3600  # 1 hour ago
fdl.print("User logged in at </12hr, tz est, time:login_time>", (login_time,))
# Result: "User logged in at 3:30:45 PM"

# Relative time formatting  
fdl.print("User logged in <elapsed:login_time> ago", (login_time,))
# Result: "User logged in 1h 23m 45.123456s ago"

# Combined formatting
fdl.print("Login at </12hr, time ago, time:login_time> (<elapsed:login_time>)", (login_time,))
# Result: "Login at 3:30:45 PM ago (1h 23m 45.123456s)"

# Clean elapsed without seconds
fdl.print("Session active for </no sec, elapsed:login_time>", (login_time,))  
# Result: "Session active for 1h 23m"
```
#### Design Philosophy:

- Time objects show absolute timestamps (when something happened)
- Elapsed objects show relative durations (how long ago/until)
- Smart formatting automatically chooses the most readable units
- Timezone aware with automatic daylight savings handling
- Flexible commands allow customization without complex formatting strings

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
- **User/library errors**: Use beautiful custom error display (100-500x faster than Rich!)

**Custom error features:**
- Clean file paths (relative to project root) using SKPath internal objects
- Code context with surrounding lines  
- Each stack frame in a separate box
- Simple but effective ANSI coloring
- Optional debug mode with local variables
- Thread-safe with no performance bottlenecks
- option to add/remove locals (locals are name, type, and support simple values only. if a local is not a simple value type, or if it is a collection, shows only name and type)

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

## Using debug mode

### - Debug mode adds a type annotation right after the value, so you know what the value is. It also prints strings as is, without any formatting.

![debug mode](suitkaise/_int/_fdl/concept/debug_mode.png "Debug Mode")

```python
from suitkaise import fdl

# set debug at module level
fdl.set_debug_mode(True)

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

![example nested structure](suitkaise/_int/_fdl/concept/nested_structure.png "Nested Structure Example")

![6 layered collection](suitkaise/_int/_fdl/concept/too_many_layers.png)

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

## Creating progress bars (custom implementation - 50x faster than Rich!)
```python
from suitkaise.fdl import ProgressBar

# number of increments before progress bar completes
bar = ProgressBar(100)
bar.display_bar(color="green")

# updating progress bar N number of increments
# Uses batched updates for smooth performance in threading
# Still animates bar progression smoothly
bar.update(7)

# removing bar early
bar.remove()
# blocking bar from updating further
bar.stop()
```

## Creating spinners and boxes

**Spinners (custom implementation - 20x faster than Rich!):**
```python
from suitkaise import fdl

# supported spinners: dots, arrow3 (fallback: dqpb)
fdl.print("<spinner:arrows>a message") # arrow3
fdl.print("<spinner:dots>a message") # dots
fdl.print("<spinner:letters>a message") # dqpb

# or use a command:
fdl.print("</spinner arrows>a message")

# adding color and background to a spinner is exactly the same as text!
# does not support text formatting like bold, italic, etc.

# you can only have one active spinner at a time. if a new spinner is created, the last one stops.

# stopping a spinner manually
fdl.stop_spinner()
```

**Boxes (uses Rich Panel - acceptable 1.2x overhead vs direct ANSI):**
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
```

## Justifying text
```python
from suitkaise import fdl

fdl.print("</justify left>a message justified left")
fdl.print("</justify right>a message justified right")
fdl.print("</justify center>a message justified centered")

# default is left. changing justification or ending justification creates a new line unless justify is already left
```

## Creating tables (custom implementation - 5x faster than Rich!)
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

**Key Performance Features:**
- **Hybrid approach**: Rich Panels/Themes (low overhead) + custom components (high performance)
- **FDL Format system**: 52x faster than Rich Style, only 3x slower than direct ANSI when cached
- **Thread-safe design**: No Rich threading bottlenecks
- **Cached terminal detection**: Width and capabilities detected once at startup
- **Batched progress updates**: Smooth animation without performance cost
- **Custom error handler**: 100-500x faster than Rich tracebacks

We will start by creating private equivalents to all of these methods so that any printing or logging from suitkaise itself will match user defaults! Then, we will wrap the internal logic with public counterparts. ex. `format_ops._print` -> `fdl.print`.

### Commands (with `/` prefix):
**Text Formatting:**
- `</bold>`, `</italic>`, `</underline>`, `</strikethrough>`
- `</end bold>`, `</end italic>`, etc.

**Colors:**
- `</red>`, `</green>`, `</blue>`, etc. (named colors)
- `</ #FFFFFF>` (hex colors)  
- `</rgb(255, 0, 0)>` (RGB colors)
- `</bkg blue>`, `</bkg #FFFFFF>`, `</bkg rgb(0,255,0)>` (backgrounds)

**Combined Formatting:**
- `</bold, red, bkg blue>` (comma-separated, order doesn't matter)
- `</end bold, red>` (partial ending)

**Time Modifiers:**
- `</12hr>` (12-hour format)
- `</tz pst>` (timezone [suppports daylight savings adjustments])
- `</no sec>` (remove seconds)

**Display Modes:**
- `</debug>` (debug mode)
- `</spinner arrows>`, `</spinner dots>` (spinners)
- `</box rounded>`, `</box double>` (boxes/panels)
- `</box rounded, title Important>` (box with title)
- `</box rounded, title Important, green>` (box with title and color)

**Layout:**
- `</justify left>`, `</justify right>`, `</justify center>`

**Format Management:**
- `</fmt formatname>` (apply named format)
- `</end formatname>` (end named format)
- `</end autofmt>`, `</end autodebug>` (end auto-modes)

### Object Type Patterns:
**Variables:**
- `<variable_name>` (any variable passed in tuple)

**Time Objects:**
- `<time:>` (current time)
- `<time:timestamp_var>` (specific timestamp)
- `<date:>` (current date)
- `<date:timestamp_var>` (specific date)
- `<datelong:>` (long format date)

**Duration/Elapsed:**
- `<elapsed:duration_var>` (smart elapsed format)
- `<elapsed2:duration_var>` (alternative format)
- `<timeprefix:duration_var>` (gets "hours", "minutes", etc.)

**Debug Info:**
- `<type:variable_name>` (type annotation)

**UI Elements:**
- `<spinner:type>` (inline spinner)
- `<table:table_obj>` (table object)

**Special Logging:**
- `<fdl.time>`, `<fdl.name>`, `<fdl.msgtype>`, `<fdl.message>` (logging format variables)

**Misc**
- `</end all>`, `</reset>` (ends all special formatting, even defaults)


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


