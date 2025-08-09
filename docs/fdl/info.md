# **FDL Processing Flow - Complete Architecture Guide**

## **Core Architecture Components**

### **1. Centralized Formatter (`_Formatter`)**
- **Single orchestrator**: Handles parsing, state management, and all output generation
- **Encapsulates entire FDL pipeline**: No external processors needed
- **Multi-format output**: Terminal, plain text, markdown, HTML
- **State isolation**: Each formatter instance is independent

### **2. Parsed Pieces (Data Structures)**
- **Text pieces**: Plain text like `"Time: "` → `{'type': 'text', 'content': 'Time: '}`
- **Variable pieces**: Variables like `<variable_name>` → `{'type': 'variable', 'content': 'variable_name'}`
- **Command pieces**: Commands like `</cyan, bold>` → `{'type': 'command', 'content': '/cyan, bold'}`
- **Object pieces**: Objects like `<time:>` → `{'type': 'object', 'content': 'time:'}`

### **3. Internal State Management**
- **Formatting state**: Colors, bold, italic, justification (within `_Formatter`)
- **Time settings**: 12hr/24hr, timezone, smart time formatting
- **Box state**: Style, color, title, content tracking
- **Output streams**: Raw output lists + final output strings

### **4. Setup Utilities (Module Level)**
- **`_ColorConverter`**: ANSI color code generation
- **`_TextWrapper`**: Text wrapping with width constraints  
- **`_TextJustifier`**: Left/center/right text alignment
- **`_BoxGenerator`**: Box border and title generation
- **`_terminal`**: Terminal width and capability detection

---

## **Critical Processing Pattern**

### **Content Addition Pattern:**
All plain text (text elements, variables, objects) gets added to raw output as:
```
(ansi code for current format state)(plain text content)(reset code)
```

**Examples:**
- Text: `(cyan+bold ANSI)Time: (reset)`
- Object: `(cyan+bold ANSI)3:45 PM(reset)`
- Variable: `(green+italic ANSI)Online(reset)`

---

## **Complete Processing Flow**

### **Step 1: Initialize Formatter and Parse FDL String**
```python
formatter = _Formatter(
    fdl_string="</cyan, bold>Time: </12hr><time:></end cyan>",
    values=(),
    destinations=[_OutputType.TERMINAL]
)
# Parse into pieces
pieces = formatter._parse_fdl_string()
↓
[
    {'type': 'command', 'content': '/cyan, bold'},    # </cyan, bold>
    {'type': 'text', 'content': 'Time: '},           # "Time: "
    {'type': 'command', 'content': '/12hr'},         # </12hr>
    {'type': 'object', 'content': 'time:'},          # <time:>
    {'type': 'command', 'content': '/end cyan'}      # </end cyan>
]
```

### **Step 2: Process Each Piece Sequentially**

#### **Command Pieces (Type 1: State Update Processing):**
```python
formatter._process_command("/cyan, bold")
↓
# 1. Group detection: "cyan, bold" → Text formatting group
# 2. Route to: _execute_text_formatting_command()
# 3. Modify formatter state ONLY:
formatter.text_color = 'cyan'
formatter.bold = True
# ❌ NEVER adds to raw output
```

#### **Text Pieces (Type 2: Normal Text Processing):**
```python
formatter._process_text("Time: ")
↓
# Generate ANSI from current formatter state
ansi_codes = formatter._generate_ansi_codes()  # cyan + bold
formatted = f"{ansi_codes}Time: \033[0m"

# Add to appropriate output:
if formatter.in_box:
    formatter.box_content.append(formatted)
else:
    formatter.raw_terminal_output.append(formatted)
```

#### **Object Pieces (Type 2: Text Substitution Processing):**
```python
formatter._process_object("time:")
↓
# 1. Get plain text from internal object handler
plain_text = formatter._execute_object("time:")  
# Returns: "3:45 PM" (based on formatter.twelve_hour_time)

# 2. Apply current formatting
ansi_codes = formatter._generate_ansi_codes()  # cyan + bold
formatted = f"{ansi_codes}3:45 PM\033[0m"

# 3. Add to appropriate output:
if formatter.in_box:
    formatter.box_content.append(formatted)
else:
    formatter.raw_terminal_output.append(formatted)
```

#### **Variable Pieces (Enhanced Processing):**
```python
formatter._process_variable("name")
↓
value = formatter.get_next_value()  # e.g., "ServerBot" or "</bold>Text"

# Check for embedded FDL commands (Case 2)
if formatter._is_fdl_command_string(value):
    formatter._process_fdl_command_from_variable(value)  # Recursive processing
    return

# - Debug mode processing (Type 3: Debug Text Processing)
if formatter.debug_mode:
    formatter._add_debug_formatted_variable(value)
    # → Type-specific colors, bold, italic + (type) annotation
    # → Ignores current formatter state
    return

# Normal processing (Type 2: Normal Text Processing):
ansi_codes = formatter._generate_ansi_codes()
formatted = f"{ansi_codes}ServerBot\033[0m"

# Add to appropriate output:
if formatter.in_box:
    formatter.box_content.append(formatted)
else:
    formatter.raw_terminal_output.append(formatted)
```

---

## **Critical Raw Output Processing Points**

### **Raw Output Gets Processed BEFORE:**

1. **Starting a Box** (`</box ...>`)
2. **Changing Justification** (`</justify center>`)  
3. **End of Processing** (final cleanup)

### **Raw Output Processing Steps:**
```python
def _process_raw_output(formatter):
    # 1. Combine raw output into single string for each format
    terminal_combined = ''.join(formatter.raw_terminal_output)
    plain_combined = ''.join(formatter.raw_plain_output)
    
    # 2. Apply text wrapping using module-level _text_wrapper
    terminal_wrapped = _text_wrapper.wrap_text(terminal_combined, formatter.terminal_width)
    plain_wrapped = _text_wrapper.wrap_text(plain_combined, formatter.terminal_width)
    
    # 3. Apply justification using module-level _text_justifier
    terminal_justified = _text_justifier.justify_text(terminal_wrapped, formatter.justify)
    plain_justified = _text_justifier.justify_text(plain_wrapped, formatter.justify)
    
    # 4. Add to final output strings
    formatter.terminal_output += terminal_justified
    formatter.plain_output += plain_justified
    formatter.markdown_output += convert_to_markdown(plain_justified)
    formatter.html_output += convert_to_html(plain_justified)
    
    # 5. Clear raw output lists
    formatter.raw_terminal_output.clear()
    formatter.raw_plain_output.clear()
    formatter.raw_markdown_output.clear()
    formatter.raw_html_output.clear()
```

---

## **Special Cases**

### **Box Processing:**
```python
# Before box starts:
formatter._process_raw_output()  # Process any pending raw output

# During box:
formatter.in_box = True
# All content goes to formatter.box_content instead of raw_output

# When box ends (formatter._end_box()):
# 1. Combine box_content → ''.join(formatter.box_content)
# 2. Wrap and center content (default inside boxes is center)
# 3. Create _BoxGenerator with current settings
# 4. Generate box for all output formats
# 5. Add completed box directly to final output strings (bypasses raw output)
# 6. Reset box state
```

### **Justification Changes:**
```python
# Before justification changes:
formatter._process_raw_output()  # Process with current justification
formatter.justify = 'center'      # Set new justification
# Future content uses new justification
```

---

## **Setup File Integration**

### **Within Formatter Methods:**

#### **Command Processing:**
- **`color_conversion.py`**: Validate colors during command execution
- Store validated colors in formatter state only (never direct output)

#### **Content Formatting:**
- **`color_conversion.py`**: Generate ANSI codes from current formatter state
- Apply ANSI formatting before adding to raw output

#### **Raw Output Processing:**
- **`text_wrapping.py`**: Wrap combined raw output to terminal width
- **`text_justification.py`**: Apply justification to wrapped text
- **`terminal.py`**: Get terminal dimensions and capabilities

#### **Box Generation:**
- **`box_generator.py`**: Create boxes around processed box content
- **All setup utilities**: Used for box content processing and border generation

---

## **Updated Architecture Rules**

1. **Formatter Centralization**: All processing logic contained within `_Formatter` class
2. **Command Processing**: Modifies formatter state ONLY, never touches output streams
3. **Content Processing**: Applies ANSI formatting and adds to raw output or box content
4. **Raw Output**: Gets processed at specific trigger points using setup utilities
5. **Setup Utilities**: Used by formatter methods, instantiated at module level
6. **ANSI Pattern**: Always `(ansi_codes)(content)(reset)` for consistent formatting
7. **State Isolation**: Each formatter instance maintains independent state
8. **Multi-format Support**: Single processing generates terminal, plain, markdown, HTML output

This centralized architecture ensures complete encapsulation and predictable processing flow.

---

## **Debug Mode Processing (Type 3)**

### **Debug Mode Overview**

Debug mode is a special processing type where:
- **Variables are displayed with type-specific colors and formatting** (bold, italic)
- **Type annotations** are shown in dimmed text `(type)`
- **All other text (including from commands) is rendered as plain text** (no formatting)
- **Only debug commands (</debug>, </end debug>) are processed**
- **Text wrapping and justification still work normally**
- **Enhanced smart time formatting** (10 units instead of 3)

## **Timestamp Philosophy**

**FDL and Suitkaise in general use pure float-based Unix timestamps for everything.** No datetime objects, ISO formats, or complex time libraries are used. All timestamps are Unix floats (seconds since epoch), and formatting is done manually for finer control and cleaner output.

### **Benefits:**
- **Precise decimal control**: Support for 0-10 decimal places in timestamp display
- **Simpler timezone logic**: Basic offset calculations without complex DST rules  
- **Consistent behavior**: All time operations use the same float-based approach
- **Finer control**: Manual formatting gives exact control over output format
- **Performance**: No overhead from datetime object creation/manipulation

### **Format Examples:**
- **Clean format (default)**: `2:03 AM` or `02:03` (no seconds, use_seconds_in_timestamp = False)
- **With seconds**: `2:03:46 AM` or `02:03:46` (when seconds enabled, decimals = 0)
- **With decimals**: `2:03:46.1234 AM` or `02:03:46.1234` (seconds + 4 decimal places default)
- **High precision**: `2:03:46.123456 AM` or `02:03:46.123456` (seconds + 6 decimal places)
- **Seconds toggle**: `/seconds` enables, `/end seconds` disables seconds display
- **Decimal control**: `/decimals N` sets precision (only applies when seconds enabled)

### **Activation and Deactivation**
```python
# Enable debug mode
formatter._execute_debug_command("debug")
formatter.debug_mode = True

# Disable debug mode  
formatter._execute_debug_command("end debug")
formatter.debug_mode = False
```

### **Debug Variable Formatting**

When `formatter.debug_mode = True`, variables get special type-based formatting:

#### **Integer Values:**
```python
value = 42
# Output: [cyan, bold, italic]42[reset] [dimmed](int)[reset]
debug_content = f"\033[36;1;3m{value}\033[0m \033[2m(int)\033[0m"
```

#### **Boolean Values:**
```python
value = True   # Green, bold, italic
value = False  # Red, bold, italic
# Output: [green/red, bold, italic]True/False[reset] [dimmed](bool)[reset]
```

#### **None Values:**
```python
value = None
# Output: [blue, bold, italic]None[reset] [dimmed](NoneType)[reset]
debug_content = f"\033[34;1;3m{value}\033[0m \033[2m(NoneType)\033[0m"
```

#### **Float Values:**
```python
value = 3.14
# Output: [cyan, bold, italic]3.14[reset] [dimmed](float)[reset]
debug_content = f"\033[36;1;3m{value}\033[0m \033[2m(float)\033[0m"
```

#### **String Values (Special Handling):**
```python
value = "Hello World"
# Output: [green, bold]"[reset]Hello World[green, bold]"[reset] [dimmed](str)[reset]
# Important: String content is printed AS-IS (no FDL processing)
debug_content = f'\033[32;1m"\033[0m{value}\033[32;1m"\033[0m \033[2m(str)\033[0m'
```

#### **Other Types:**
```python
value = [1, 2, 3]  # or any other type
# Output: [bold, italic][1, 2, 3][reset] [dimmed](list)[reset]
debug_content = f"\033[1;3m{value}\033[0m \033[2m(list)\033[0m"
```

### **Debug Processing Flow**

```python
# Normal variable processing
if not formatter.debug_mode:
    formatted = f"{ansi_codes}{value}\033[0m"
    formatter._add_formatted_content_to_raw_output(formatted, use_current_formatting=True)

# Debug variable processing  
else:
    formatter._add_debug_formatted_variable(value)
    # → Applies type-specific formatting
    # → Ignores current formatter state (colors, bold, etc.)
    # → Adds directly to raw output with debug formatting
```

### **Debug Mode Integration with Commands**

- **Most commands render as literal text**: Colors, bold, italic, etc. commands appear as plain text in output
- **Only debug commands work**: `</debug>` and `</end debug>` are the only processed commands
- **Variables use debug formatting**: Always use type-specific colors/formatting, ignore formatter state
- **Objects render as plain text**: `<time:>`, etc. produce plain text output (no formatting applied)
- **Text is always plain**: All text content renders without any ANSI codes or formatting
- **Wrapping/justification still work**: Layout commands like wrapping and justification are applied during final processing
- **String variables bypass FDL**: No embedded command processing in debug strings

#### **Debug Mode Example:**
```python
# Debug mode active
fdl.print("</debug></bold, red>Status: <status> at <time:>", "active")
```
**Normal mode result:**
`[bold, red]Status: [reset][bold, red]active[reset][bold, red] at [reset][bold, red]14:30:25[reset]`

**Debug mode result:**
`</bold, red>Status: [green, bold]"[reset]active[green, bold]"[reset] [dimmed](str)[reset] at 14:30:25`

Key differences in debug mode:
- `</bold, red>` appears as literal text in output
- `Status:` and ` at ` are plain text
- `<status>` gets debug formatting (green quotes for string)
- `<time:>` produces plain text timestamp

#### **Complete Debug Example:**
```python
# Your exact example
fdl.print("</debug></bold, italic>Hello, <value>!", "World")
```
**Result:** `</bold, italic>Hello, [green, bold]"[reset]World[green, bold]"[reset] [dimmed](str)[reset]!`

The command `</bold, italic>` appears as literal text, while the variable `<value>` gets special debug formatting.

### **Debug Object Processing**

#### **Type Objects (`<type:variable>`):**
```python
# In debug mode, <type:variable> shows type annotation
formatter._execute_object("type:username")
# Returns: " (str)" - dimmed type annotation
```

### **Smart Time in Debug Mode**

When debug mode is active:
- **Smart time units**: Increased from 3 to 10 for more detail
- **Enhanced precision**: More time components shown
- **Debug time objects**: Include additional debugging information

---

## **Command Group Processing Architecture**

### **Group-Oriented Command System**

Commands are split into **command groups** based on their purpose and type. Each command string can only contain commands from **one group type** (except end commands).

**Command Groups:**
- **Text Formatting**: `bold`, `italic`, `underline`, `strikethrough`, colors, `justify`
- **Time Commands**: `12hr`, `24hr`, `tz pst`, `smart time 2`
- **Debug Commands**: `debug`, `end debug`
- **Box Commands**: `box rounded`, `title Important`, `color current`
- **End Commands**: Can span multiple groups in one string

### **Group Processing Rules**

**✅ Correct behavior:**
```fdl
</bold, cyan>           # Text formatting group
</tz pst, smart time 2> # Time command group  
</debug>                # Debug command group
```

**❌ Incorrect behavior (will fail):**
```fdl
</bold, cyan, tz pst, smart time 2, debug>  # Mixed groups!
```

**✅ End commands are special - they can mix groups:**
```fdl
</end bold, cyan>                           # Single group
</end bold, cyan, tz pst, smart time 2>     # Mixed groups OK
</end debug>                                # Single group
```

### **Group Detection Algorithm**

1. **Parse command string**: Split by commas
2. **Check first command**: Determines the group type for the entire string
3. **Route all commands**: All commands in the string go to the same group handler
4. **Validate consistency**: If any command doesn't belong to the detected group → Error

**Example:** `</box rounded, title Important, green>`
- First command: `"box rounded"` → **Box group detected**
- All commands routed to: `_execute_box_command()`
- Processing: `box rounded` → start box, `title Important` → set title, `green` → set color

---

## **Variable Handling in Commands**

### **Case 1: Variables Within Command Strings**

**Usage:** Dynamic command injection
```python
fdl.print("</bold, <user_color>>Dynamic color", "red")
```

**Processing:**
1. **Parse**: `"</bold, <user_color>>"`
2. **Resolve**: `"bold, <user_color>"` → `"bold, red"` (consumes tuple value)
3. **Group**: Text formatting group
4. **Execute**: `bold` + `red` commands

**Use Cases:**
- Dynamic timezone: `</tz <user_timezone>>`
- User preferences: `</bkg <user_bg>, <user_text_color>>`
- Runtime configuration: `</12hr, tz <location_tz>>`

### **Case 2: Variables Containing FDL Strings**

**Usage:** Reusable format patterns
```python
error_fmt = "</bkg red, white, bold>ERROR: "
fdl.print("<error_fmt>Connection failed", error_fmt)
```

**Processing:**
1. **Variable substitution**: Get `"</bkg red, white, bold>ERROR: "`
2. **FDL detection**: Recognize embedded FDL commands
3. **Isolated processing**: Create separate formatter instance
4. **State isolation**: Embedded commands don't affect main formatter state
5. **Output integration**: Add isolated result to main output

**State Isolation Behavior:**
- **Embedded commands are isolated**: Commands in the embedded string (like `</bold, italic>`) only affect content within that string
- **Main state unchanged**: The main formatter's state attributes remain unmodified
- **Independent formatting**: The embedded string produces formatted output independent of current state
- **Clean integration**: The formatted result is added to the main output without side effects

**Example:**
```python
# Main formatter has red text
fdl.print("</color red>Before: ")
# Embedded string with independent formatting
formatted_str = "</bold, italic>Hello, World!"
fdl.print("<formatted_str>", formatted_str)  # White text, bold + italic
# Main formatter still has red text
fdl.print(" After")
# Result: "Before: Hello, World! After" (Before/After = red, Hello = white bold italic)
```

**Use Cases:**
- Format libraries: Pre-defined styling patterns
- Conditional formatting: Different formats based on conditions
- Template systems: Reusable message formats
- Component isolation: Self-contained formatted components

### **Recursive Processing Safety**

- **State preservation**: Original formatter state maintained during recursion
- **Value consumption**: Variables in embedded FDL consume from the same tuple
- **Group validation**: Embedded commands follow same group rules
- **Infinite loop protection**: Embedded FDL strings are processed once (no re-embedding)

---

Here is a full run-through of the flow.

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

Before starting, we will measure the initial terminal width. assuming a hard minimum width of 60.

First, we create a blank _FormatState object. This tracks everything that is needed in order to process and generate formatted output from fdl strings.

Next, we parse this message, now concatenated to:

`"</cyan, bold>Time: </12hr, tz pst, no sec><time:></end cyan></box rounded, color current, bkg gray, title <self.name>></green, italic>Online</reset> since </cyan><time:self.time_connected_at></end box></reset></format warning></justify center>Warning: This is an example warning outside of the status box."`

And split it like this:

1. `</cyan, bold>` (text command)
2. `'Time: '` (plain text string)
3. `</12hr, tz pst, no sec>` (time command)
4. `<time:>` (time object)
5. `</end cyan>` (text command)
6. `</box rounded, color current, title <self.name>>` (box command)
7. `</green, italic>` (text command)
8. `'Online'` (plain text string)
9. `</reset>` (misc command)
10. `' since '` (plain text string)
11. `</cyan>` (misc command)
12. `<time:self.time_connected_at>` (time object)
13. `</end box>` (box command)
14. `</reset>` (misc command)
15. `</format warning>` (format command)
16. `</justify center>` (layout command)
17. `'Warning: This is an example warning outside of the status box.'` (plain text string)

Next, we sequentially process each split piece, updating the format state.

1. `</cyan, bold>`
- Updates `text_color` to cyan and `bold` to True in _FormatState.

2. `"Time: "`
- Adds `(ansi code for cyan and bold text)Time: (reset code)` to raw outputs, according to _FormatState.

3. `</12hr, tz pst, no sec>`
- Sets `twelve_hour_time` to true, `timezone` to 'pst', and `use_seconds` to False in _FormatState.

4. `<time:>`
- Adds the current time to the raw outputs displayed as 12 hour time (vs standard 24 hour time), accounting for the Pacific time zone, and adding bold and cyan to the text. 
- `(ansi code for cyan and bold text)(current timestamp formatted)(reset code)`

5. `</end cyan>`
- Sets `text_color` to None in _FormatState.

6. `</box rounded, color current, title <self.name>>`
To output:
- we need to format and handle previous text before we start the box.
- adds a \n.
- combines list of strings into one string.
- Wraps and justifies all raw output so far using _TextWrapper and _TextJustifier, and adds to the regular outputs.

In _FormatState:
- sets `in_box` to True, 
- sets `box_style` to "rounded"
- sets `box_color` to the current text color.
- sets `box_title` to `self.name`, as long as the user provides self.name as a variable after the fdl string. removes the variable from the tuple.

7. `</green, italic>`
- Sets `text_color` to green and `italic` to True in _FormatState.

8. `"Online"`
- Adds 'Online' in green italics to `box_content` list. 
- `(ansi code for green and italic text)Online(reset code)`

9. `</reset>`
- In _FormatState, resets all variables that have a direct impact on output except box related ones.

10. `" since "`
- Adds ' since ' to box_text, with no formatting because we just reset it. 
- ` since (reset code)`

11. `</cyan>`
- Sets text color to cyan in _FormatState.

12. `<time:self.time_connected_at>`
- Adds the next value in the tuple as a formatted timestamp as long as it is a float. 
- If it isnt a float, we display `</ERROR>`
- Our format is still 12 hour time in the PST timezone from earlier.
- `(ansi code for cyan)(formatted given timestamp)(reset code)`
- Removes second value from tuple.



17. `'Warning: This is an example warning outside of the status box.'`

13. `</end box>`
- This is when the entire box gets generated and added to outputs.
- combine `box_content` list of strings. Wrap combined string across lines according to the _TextWrapper and center text using the _TextJustifier.
- measure maximum width of wrapped text (a list of strings). the `actual_box_width` will be 6 more than that, to account for 2 spaces of padding on both sides and the borders.
- generates and colors borders and title according to `box_style` and `box_title`, around our existing content, adding a newline at the end of the bottom right corner.
- strip whitespace on both sides of box. combine list of box lines into one string.
- reprocess box through text wrapper and justifier, justify box according to active text justification.
- completed box gets directly added to finished output.
- reset all box related variables to defaults.

14. `</reset>`
- In _FormatState, resets all variables that have a direct impact on output except box related ones.

15. `</format warning>`
- Gets warning format ('</bkg yellow, black, bold>') from the _FormatRegistry.
- parses and splits string just like main flow (in this case, we just have one command type).
- applies <> commands to _FormatState (adds yellow to `background_color`, black to `text_color`, and sets `bold` to True.)

16. `</justify center>`
- processes all text in raw outputs according to the current justification, processing it with the text wrapper and the text justifier.
- Sets `justify` to center in _FormatState.

17. `"Warning: This is an example warning outside of the status box."`
- Adds the string in black, bold text, with a yellow background and centered.
- `(ansi code)Warning: This is an example warning outside of the status box.(reset code)`

Once we realize we have no more pieces to process:
- we process the rest of the raw output through the text wrapper and justifier.
- output the finished content to the output streams.

No need to check what needs to be reset, as we can just release this object from memory and create a new one for the next fdl print!