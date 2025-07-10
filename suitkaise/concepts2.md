right now, my format operations and fdprint are all over the place, and have lost their clean simplicity.

so lets redo it!

overview of rich:
Rich Library - Complete Feature Overview
Core Features
Console Management


Force terminal mode for consistent behavior
Output redirection support (stdout, stderr, files)

Text Styling & Markup

Style objects for reusable formatting
Color support: named colors, hex (#ff0000), RGB (rgb(255,0,0))
Text effects: bold, italic, underline, strikethrough, blink
Background colors and combinations
Text alignment and justification

Syntax Highlighting

100+ programming languages supported via Pygments
35+ built-in themes (monokai, dracula, github-dark, etc.)
Custom theme creation capability
Line numbers, word wrapping, code folding
Automatic language detection
Theme inheritance and extension

Layout Components

Tables: Headers, footers, sorting, alignment, styling, responsive columns
Panels: Borders, titles, subtitles, padding, custom box styles
Columns: Multi-column layouts, responsive design
Layout: Complex grid systems, nested layouts, sizing controls
Align: Left, center, right, justify alignment
Padding: Custom spacing around content

Progress & Status

Progress bars with customizable columns
Multiple concurrent progress tracking
Spinners (70+ animation styles)
Status displays with spinners
Time elapsed, ETA calculations
Custom progress bar styling

Data Display

JSON: Pretty printing with syntax highlighting
Trees: Hierarchical data display with custom styling
Tables: Sortable, filterable, with rich content in cells
Renderables: Custom display objects

Advanced Features

Live Display: Real-time updating content
Markdown: Full markdown rendering in terminal
Logging: Enhanced logging with colors and formatting
Traceback: Beautiful error displays with syntax highlighting
Jupyter: Full Jupyter notebook integration
HTML Export: Convert terminal output to HTML

Text Effects & Styling

Inheritance: Styles can inherit from parent styles

Import-able Libraries (in Rich environment)

lucide-react: Icons and symbols
recharts: Chart components
MathJS: Mathematical calculations
lodash: Utility functions
d3: Data visualization
Plotly: Interactive plots
Three.js: 3D graphics
Papaparse: CSV parsing
SheetJS: Excel file processing
Chart.js: Charts and graphs
Tone: Audio synthesis
mammoth: Word document processing
tensorflow: Machine learning

Output Formats

HTML: Full HTML export with CSS styling
SVG: Vector graphics export
Plain text: Stripped output for logs/files
Jupyter: Rich display in notebooks

Theme System

Built-in themes: 35+ professional themes
Custom themes: Full Pygments theme creation
Theme inheritance: Extend existing themes
Runtime switching: Change themes dynamically
Token-level control: Style individual syntax elements

Performance Features

Lazy rendering: Only processes visible content
Caching: Intelligent caching of expensive operations
Memory efficient: Minimal memory footprint
Fast rendering: Optimized for large outputs
Streaming: Handle large data streams efficiently

Developer Experience

Type hints: Full TypeScript-style type annotations
Documentation: Comprehensive docs and examples
Error handling: Graceful fallbacks and error messages
Extensibility: Plugin architecture for custom components
Testing: Built-in testing utilities

Cross-Platform Support

Windows: Full Windows Terminal support, legacy CMD support
macOS: Terminal.app, iTerm2 support
Linux: All major terminal emulators
WSL: Windows Subsystem for Linux support
CI/CD: GitHub Actions, GitLab CI, Jenkins support

Integration Capabilities

Logging frameworks: Python logging, structlog
Web frameworks: Flask, Django, FastAPI
CLI frameworks: Click, Typer, argparse
Testing: pytest, unittest integration
IDEs: VS Code, PyCharm, Vim, Emacs support

Accessibility Features

Screen readers: Compatible with accessibility tools
High contrast: Support for high contrast modes
Font scaling: Respects system font size settings
Color blindness: Provides alternative styling options

Value Propositions
For Developers

Dramatically improves CLI/terminal application UX
Reduces development time for formatted output
Professional appearance out of the box
Consistent cross-platform behavior
Rich ecosystem and community


we will use rich as a base formatting engine, and wrap it to be simpler.

There are a few things I need to do:

- create clean intuitive that matches the rest of the lib
- create good looking, clean formatted console output using rich as a base
    - rich has its flaws, so we will need to patch them up or fill in the gaps.

## implementation

## step 1: terminal manipulation and ensuring unicode support
- we need to:
-- manipulate the different os terminals, to get all terminal info (done, terminal.py)
-- ensure all unicode characters that rich uses can be supported, and gracefully fall back.

----------
fdprint - a super formatter that can format any standard data type, date and time, and more

fdprint (format/debug print) is a tool that allows users to automatically print data in better formats, formatted for better display or better debugging.

```python
my_list = [
    "hello",
    "world",
    "this",
    "is",
    "a",
    "test",
    "of",
    "the",
    "list",
    "functionality"
]

my_dict = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
    "key4": "value4",
    "key5": "value5"
}

my_set = {
    "apple",
    "banana",
    "cherry",
    "date",
    "elderberry"
}

my_tuple = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth"
)

my_int = 42
my_float = 3.14
my_bool = True
my_none = None
my_bytes = b"byte string"
my_complex = 1 + 2j
my_range = range(10)
my_dict_of_lists = {
    "list1": ["item1", "item2", "item3"],
    "list2": ["item4", "item5", "item6"]
}
my_dict_of_sets = {
    "set1": {"item1", "item2", "item3"},
    "set2": {"item4", "item5", "item6"}
}
my_dict_of_tuples = {
    "tuple1": ("item1", "item2", "item3"),
    "tuple2": ("item4", "item5", "item6")
}

def nlprint(*args, **kwargs):
    """
    Print each argument on a new line.
    
    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments (not used).
    """
    for arg in args:
        try:
            print(arg)
        except Exception as e:
            print(f"Error printing argument {arg}: {e}")


nlprint(
    my_list,
    my_dict,
    my_set,
    my_tuple,
    my_int,
    my_float,
    my_bool,
    my_none,
    my_bytes,
    my_complex,
    my_range,
    my_frozenset,
    my_bytearray,
    my_dict_of_lists,
    my_dict_of_sets,
    my_dict_of_tuples
)

```

result:
['hello', 'world', 'this', 'is', 'a', 'test', 'of', 'the', 'list', 'functionality']
{'key1': 'value1', 'key2': 'value2', 'key3': 'value3', 'key4': 'value4', 'key5': 'value5'}
{'banana', 'apple', 'cherry', 'elderberry', 'date'}
('first', 'second', 'third', 'fourth', 'fifth')
42
3.14
True
None
b'byte string'
(1+2j)
range(0, 10)
{'list1': ['item1', 'item2', 'item3'], 'list2': ['item4', 'item5', 'item6']}
{'set1': {'item2', 'item1', 'item3'}, 'set2': {'item4', 'item6', 'item5'}}
{'tuple1': ('item1', 'item2', 'item3'), 'tuple2': ('item4', 'item5', 'item6')}

result with fmt for display:
hello, world, this, is, a, test, of, the, list, functionality

key1: value1
key2: value2
key3: value3 
key4: value4
key5: value5

banana, apple, cherry, elderberry, date

(first, second, third, fourth, fifth)

42
3.14
True
None
byte string
1 + 2j
0, 10


list1: item1, item2, item3
list2: item4, item5, item6

and with color to more easily see what is being printed.

result with fmt for debugging:
(list) [
    
    'hello', 'world', 'this', 'is', 'a', 'test', 'of', 'the', 'list', 'functionality'

        ] (list)

(dict) {

   'key1': 'value1', 
   'key2': 'value2', 
   'key3': 'value3', 
   'key4': 'value4', 
   'key5': 'value5'

} (dict)

(set) {
    
    'banana', 'apple', 'cherry', 'elderberry', 'date'

} (set)

(tuple) (
    
    'first', 'second', 'third', 'fourth', 'fifth'

) (tuple)

(int) 42
(float) 3.14
(bool) True
(None) None
(bytes) 'byte string'
(complex) ( 1 + 2j )
(range) 0, 10

(dict) {

    (list) ['item1', 'item2', 'item3'],
    (list) ['item4', 'item5', 'item6']

} (dict)

and with color to more easily see what is being printed.

```python
from suitkaise import fdprint as fd
import time

# its as easy as...
value1 = {
    "dict": {a dict}
    "list": []
}

fd.fprint("This is value1: {value1}", value1)

# printing dates or times
now = time.time()

# print using our default time format (see report section for more details)
fd.fprint("Printing {value1} at {time:now}", (value1, now))
# or...
# print using our default date format
fd.fprint("Printing {value1} at {date:now}", (value1, now))

# using custom time and date formats

# print using hours, minutes, seconds and microseconds
fd.fprint("Printing {value1} at {hms6:now}", (value1, now))
# print using date and timezone
fd.fprint("Printing {value1} at {datePST:now}", (value1, now))

# using debugging formats automatically
fd.dprint("Your message with vars", (tuple of vars), priority level 1-5)

# toggling if debug messages should be printed

# will only print messages at level 2 or higher
fd.set_dprint_level(2)
```

----------

-------
report

reports is Suitkaise's custom logging module, that keeps the original logging formula, but adds more convenience methods to auto log some common statements.

```python
from suitkaise import report, skpath

# report from this file (rptr = reporter)
rptr = report.from_current_file()
# or from another file (like a parent file)
target_file = skpath.SKPath("parent_dir/main_dependent_file")
rptr = report.from_other_file(target_file)

# report from a keyword instead of a file path
rptr = report.from_this_key("Event_Bus")

# using context manager to quickly use a different reporter
# if not a valid in project file path (and not a valid path at all) assumes entry is key
# you could just create another reporter, but...
# this removes the "rq" reporter from memory and looks and feels more intuitive
except exception as e:
    with report.Quickly("a/different/file/path") as rq:
        rq.error(f"{Value1} was set to None so {Value2} was not initialized. {e}")

# create 2 different reporters
bus_rptr = report.from_this_key("Event_Bus")
rptr = report.from_current_file()

# use them for the same message and they will log from different sources
# can report the same major error to different sources
rptr.error(f"{Value1} was set to None so {Value2} was not initialized.")
bus_rptr.error(f"{Value1} was set to None so {Value2} was not initialized.")

# toggling what reports you see
paths = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want", as_str=True)
# supports strings and lists of strings
reporters_to_listen_to = [
    paths,
    "Event_Bus",
    "SYSWARNINGS"
]
report.listen_to(reporters_to_listen_to)

# -------------------------
# basic report functions
from suitkaise import report
import time

# all reports take a float timestamp as an argument and convert it into a time and date depending on set rules
report.set_date_threshold(num_of_seconds, format_to_use)
report.set_time_threshold(num_of_seconds, format_to_use)
# time thresholds go from num_of_seconds to 0, so you can set one for minutes at inf and one for seconds at 60
report.set_time_threshold(float('inf'), "minutes")
report.set_time_threshold(60, "seconds")

# time threshold automatically mirrors for negative numbers
# we also have an assumed default (--d --h --m --.----------s)
# which assumes to measure in --h --m --.----------s if value is greater than 3600, for example

# standard logging
report.info("message", info, end=True, time=time.time())
report.debug()
report.warning()
report.error()
report.critical()

# success or fail
report.success()
report.fail()

# quick state messages
report.setToNone()
report.setToTrue()
report.setToFalse()

# save and load
report.savedObject()
report.savedFile()
report.loadedObject()
report.loadedFile()

# general status (will add more)
report.scanning()
report.scanned()
report.queued()
report.leftQueue()
report.leftQueueEarly()

report.custom(rest of regular args, "custom message")

# adding info to the start or end of a group of messages (default: end=False)
# handles correct spaces depending on if you add at start or end
info = f"(Class: {self.__name__}, Function: {__name__})"
with report.Quickly("any_valid_key_or_path", info, end=True) as rq:
    rq.error(f"{Value1} was set to None so {Value2} was not initialized.")

# Looks like "ERROR: number1 was set to None so registry2 was not initialized. (Class: MyClass, Function: __init__)

# or with existing reporter:
rptr.error("message", info, end=TrueOrFalse)


# Thats the basic concept for sk logging functionality
```


```python
from suitkaise import fd # fd = Format and Debug



```


