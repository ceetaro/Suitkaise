fdl - Formatting, Debugging, and Logging for suitkaise



Setting up logging
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
except exception as e:
    with fdl.log.Quickly("a/different/file/path") as lq:
        lq.error(
            "{value1} was set to None so {value2} was not initialized. {e}",
            (value1, value2, e)
            )

# log same message using multiple reporters
msg = "{value1} was set to None so {value2} was not initialized."
values = (value1, value2)

rptr.warning(msg, values)
central_rptr.warning(msg, values)
bus_rptr.warning(msg, values)
```

Setting up logging, cont: adjusting default settings
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
lsetup.create_log_file()

# enable/disable color (default=True)
lsetup.use_color(True)
# enable/disable unicode (unicode automatically falls back when outputting to file)
# auto detects unicode support
lsetup.use_unicode(True) # default=True

# wrap words that don't fit in remaining line space by putting them on the next line
lsetup.use_wrapping(True) # default=True

# set default message format
config = {
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
time_fmt = TimeFormat(config)
fmt = '{fdl.time} - {fdl.name} - {fdl.msgtype} - {fdl.message}'

# log format, fdl configs
lsetup.set_format(fmt, (time_fmt))

# set what loggers you want to listen to
# listens to all loggers by default, but you can stop listening to certain ones
lsetup.stop_listening_to("paths_or_keys")

# see what we are ignoring
ignoring = lsetup.not_listening_to
# see what we are listening to
listening = lsetup.listening_to

# return original status
lsetup.listen_to("paths_or_keys_being_ignored")
```

Setting up logging, cont: adjusting logger specific settings
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
rptr_fmt = '{fdl.time} - {fdl.name} - {fdl.msgtype} - {fdl.message}'
rptr.set_format(rptr_fmt, (rptr_time_fmt))
```

Basic logging settings
```python
from suitkaise import fdl

rptr = fdl.log.from_current_file()

# standard logging
rptr.info("value1: {value1}, value2: {value2}", (value1, value2))
rptr.debug()
rptr.warning()
rptr.error()
rptr.critical()

# success or fail
rptr.success()
rptr.fail()

# quick state messages
rptr.setToNone()
rptr.setToTrue()
rptr.setToFalse()

# save and load
rptr.savedObject()
rptr.savedFile()
rptr.loadedObject()
rptr.loadedFile()
rptr.importedObject()
rptr.importedModule()

# general status (will add more)
rptr.scanning()
rptr.scanned()
rptr.queued()
rptr.leftQueue()
rptr.leftQueueEarly()

# custom message type
rptr.custom(
    "value1: {value1}, value2: {value2}", 
    (value1, value2),
    "custom message type"
)
```

Adding color and text formatting to messages
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
# NOTE: using the f"string" pattern is not required, but most IDEs 
#       display bracketed text differently when f is at the start

# adding text formatting
fdl.print(f"{/bold}This is bold text{/end bold}")

# adding text color
fdl.print(f"{/red}This is red text{/end red}")
fdl.print(f"{/ #FFFFFF}This is white text{/end #FFFFFF}")
fdl.print(f"{/rgb(0, 0, 0)}This is black text{/end rgb(0, 0, 0)}")

# adding background color
fdl.print(f"{/red, bkg blue}This is red text on a blue background{/end red, bkg blue}")

# putting all 3 together
fdl.print(
    f"{/italic, green, bkg rgb(165, 165, 165)}"
    "This is italicized green text on a light gray background"
    f"{/end italic, green, bkg rgb(165, 165, 165)}"
    )

# can add multiple text formats at once
fdl.print(f"{/bold, underline}This is bolded and underlined text{/end bold, underline}")

# order doesn't matter, unlike rich
# but must be separated by commas
fdl.print(
    f"{/italic, bkg green, black, bold}"
    "This is bolded, italicized, black text on a green background."
    f"{/end bkg green, bold, italic, black}"
    )

# can remove some but not all
fdl.print(
    # add your color and text formatting
    f"{/italic, bkg green, black, bold}"

    "This is bolded, italicized, black text on a green background.\n"

    # end some of it
    f"{/end black, italic}"

    "This is now bold default color text, still on a green background.\n"

    # you don't have to explicitly end colors, you can just change them
    f"{/blue, strikethrough, bkg yellow}"

    # but you have to explicitly end text formatting, as they wont override each other!   
    f"{/end bold}"

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
fdl.print("{value1} was set to None so {value2} was not initialized.", (value1, value2))

# string variables appear bold black with green background
fdl.set_str_format(("bkg green", "bold", "black"))

# higlight certain words that aren't {values}
# "None" appears bold white, with red background
fdl.highlight("None", ("bkg red", "bold", "white"))

#
# formatting within the actual string being printed overrides outside settings!!!
#

# and some things, like "None", "True", and "False" have preset formats

# loggers support the same formatting options!
rptr.error(
    f"{/bold, orange}"
    "{value1} was set to None so {value2} was not initialized."
    # remember, no need to /end if the whole sentence uses the formatting!
    )

if rptr.using_color and rptr.italicizing:
    rptr.set_text_color(None)
    rptr.set_background_color(None)
    rptr.set_italic(False)
```


Explicit time and date printing

we have 3 time and date display commands: time, date, and elapsed.
```python
from suitkaise import fdl
import time

from_64_sec_ago = time.time() - 64

elapsed = now - from_64_sec_ago

# print current time in default timestamp format (hh:mm:ss.123456)
fdl.print("{time:}")
# print a given timestamp in default timestamp format
fdl.print("{time:from_64_sec_ago}", from_64_sec_ago)

# print current time in default date form (dd/mm/yy hh:mm:ss)
fdl.print("{date:}")
# print a given timestamp in date form
fdl.print("{date:from_64_sec_ago}", from_64_sec_ago)

# print a given timestamp in a different format
# July 4, 2025
fdl.print("{datelong:}")

# using a command
# 16:30 -> 4:30 PM (accounts for daylight savings)
fdl.print(f"{/12hr, time:}")

# timezones account for daylight savings
fdl.print(f"{/tz pst, time:from_64_sec_ago}", from_64_sec_ago)

# print a given elapsed time value in a smart format
# single digit hours only show one digit
# ex. 8274 -> 2:17:54
# ex. 2492 -> 0:41:32
# ex. 82000 -> 22:46:40
time_ago = 8274.743462
# result: 2:17:54.743462 hours ago
fdl.print("{elapsed:time_ago} {timeprefix:time_ago} ago", time_ago)

time_until = 82000
# use a different elapsed format to display in __h __m __.______s
# result: 22h 46m 40.000000s until next meeting
fdl.print("{elapsed2:time_until} until next meeting", time_until)

# use a command to get rid of seconds (f"" is for IDE display, not required)
fdl.print(f"{/no sec, elapsed2:time_until} until next meeting", time_until)


# printing time and values
import os
pid = os.pid()
value1 = True
fdl.print(
    "Process {pid} ({time:from_64_sec_ago}): value1 set to {value1}.",
    (pid, from_64_sec_ago, value1)
    )
# or... without an explicit time value
fdl.print(
    "Process {pid} ({time:}): value1 set to {value1}.",
    (pid, value1)
    )
```

Creating Format objects
```python
from suitkaise import fdl

# create a format (f"" not required, only for IDE visualization)
greentext_bluebkg = fdl.Format(
    name="greentext_bluebkg", 
    format=f"{/green, bkg blue}"
)
# use a format
fdl.print(
    f"{/fmt greentext_bluebkg}"
    "This is green text with a blue background"
)

# create a format from a Format 
# (cannot override previously set formatting (text color, bkg color))
format2 = fdl.Format(
    name="format2",
    format=f"{/fmt greentext_bluebkg, bold, italic}
)
fdl.print(
    f"{/fmt format2, underline}"
    "This is green, bolded, italicized, underlined text on a blue background."
    f"{/end format2}"
    "This is now just underlined text."
)
```

Raising errors with fdl: all errors and tracebacks are automatically formatted using rich's traceback formatting!!!

Using debug mode

Debug mode adds a type annotation right after the value, so you know what the value is. It also prints strings as is, without any formatting.

```python
from suitkaise import fdl

# set debug at module level
fdl.set_debug_mode(True)

value1 = 32

# use direct function
fdl.dprint("value1 was set to {value1}.", value1)

# use formatting
fdl.print(f"{/debug}value1 was set to {value1}.", value1)
# result: see "debug_mode.png"

# get type annotation individually
fdl.print("value1 was set to {type:value1}.", value1)
```


Printing code blocks and markdown files
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

# printing a .md file
fdl.mdfileprint("path/to/file.md")
```


Printing out complex, nested value structures
```python
from suitkaise import fdl

# when we have a nested structure of collections (dicts, lists, tuples, and sets), we format them in a way that makes them easier to read.

# complex structures get printed to the 6th level of nesting
# based on how many levels a collection is nested, we color its brackets/parentheses a different color

# level 1 (outermost collection) is red, then orange, yellow, green, blue, and purple.

# brackets/parentheses are also bolded. keys of dicts are bolded and colored the same color as their dict's brackets

# additionally, we sort data in collections by type, and annotate the type after we have listed out all of that collection's values of said type.

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

# see "nested_structure.png" for result

# example of a nested collection that goes past 6 layers

my_unsupported_collection = { # level 1 - red
    'a': { # level 2 - orange
        'b': { # level 3 - yellow
            'c': { # level 4 - green
                'd': { # level 5 - blue
                    'e': { # level 6 - purple
                        'f': "this layer will not show any data in a collection
                    }
                }
            }
        }
    }
}

# see "too_many_layers.png" for result
```

Using decorators to set formats for functions
```python
from suitkaise import fdl

@fdl.autoformat(f"{/bkg dark gray}")
def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        pass
    else: n = fibonacci(n-1) + fibonacci(n-2)
    # auto applies format
    fdl.print("Result: {n}", n)
    # disable autoformat
    fdl.print(f"{/end autofmt}Result: {n}", n)
    return n

# ❌ does not auto apply format to return value ❌
# (still applies format to print statements inside)
fdl.print(fibonacci(8))

# applies format to print statements inside function!
fibonacci(9)

# automatically set debug mode
@fdl.autodebug()
def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        pass
    else: n = fibonacci(n-1) + fibonacci(n-2)
    # auto applies debug mode
    fdl.print("Result: {n}", n)
    # disable autodebug
    fdl.print(f"{/end autodebug}Result: {n}", n)
    return n
```

Creating progress bars
```python
from suitkaise.fdl import ProgressBar

# number of increments before progress bar completes
bar = ProgressBar(100)
bar.display_bar(color="green")

# updating progress bar N number of increments
bar.update(7)

# removing bar early
bar.remove()
# blocking bar from updating further
bar.stop()
```

Creating spinners and boxes (rich's Panels)
```python
from suitkaise import fdl

# supported spinners: dots (only first one), arrow3 (fallback: dqpb)
fdl.print("{spinner:arrows}a message") # arrow3
fdl.print("{spinner:dots}a message") # dots
fdl.print("{spinner:letters}a message") # dqpb

# or use a command:
fdl.print(f"{/spinner arrows}a message")

# adding color and background to a spinner is exactly the same as text!
# does not support text formatiing like bold, italic, etc.

# you can only have one active spinner at a time. if a new spinner is created, the last one stops.

# stopping a spinner manually
# later... lets say a progress bar completes
fdl.stop_spinner()

# creating boxes
# supported: square, rounded, double, heavy, heavy_head, horizontals 
# (fallback: ascii)

# print a whole message in one box
fdl.print(f"{/box rounded}a message")

# or some in a box and some out
fdl.print(
    f"{/box double}
    "a message in a box"
    f"{/end box}"
    "\na message outside the box"
)

# adding a title to the box
fdl.print(f"{/box rounded, title Important}a message")

# adding a color to the box (if no color, takes current text color)
fdl.print(f"{/box rounded, title Important, green}a message")
```

Justifying text
```python
from suitkaise import fdl

fdl.print(f"{/justify left}a message justified left")
fdl.print(f"{/justify right}a message justified right")
fdl.print(f"{/justify center}a message justified centered")

# default is left. changing justification or ending justification creates a new line unless justify is already left
```

Creating tables
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

# populate cells using int coords
table1.populate(1,1, "str" or str(value))
# populate cells using row and column names (order doesnt matter as long as rows and colums have unique names
table1.populate("Parser Process", "Memory Usage", "str" or str(value))

# set formatting for rows, columns, or cells
table1.set_cell_format(format=fdl.Format)
table1.set_row_format(format=fdl.Format)
table1.set_column_format(format=fdl.Format)

# printing table
fdl.print("{table1}", table1)
# or...
table1.display_table()
```

We have created a simpler, command based system that allows all formatting to be done right in the string. it is clearer than rich, and keeps it simpler so that overhead is less and users are not as overwhelmed. it gives options to adjust settings at the module level, the function level, and the individual string level. all formatting options are supported by our logging system as well! A logging system that improves on the standard logging and rich logging with simpler, fine tuned behavior.

Is there anything I am missing? Is there anything that you think could be simpler?

We will start by creating private equivalents to all of these methods so that any printing or logging from suitkaise itself will match user default! Then, we will wrap the internal logic with public counterparts. ex. format_ops._print -> fdl.print.

Can you help me by listing all of the commands and {objtype:obj} patterns (ex. {time:a_time}) out together?

Do you think this is a good concept?






