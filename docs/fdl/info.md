# FDL Info

## Module Status
- **Implementation**: In development
- **Priority**: Medium (Gateway module)
- **Dependencies**: None (foundational module)

## Key Components

### Format Functions
- `fdl.print()` - Main formatting function with command-based syntax
- `fdl.log.from_current_file()` - File-based reporters
- `fdl.log.from_this_key()` - Key-based reporters
- `fdl.log.Quickly()` - Context manager for temporary reporters

### Data Type Support
- Lists, dictionaries, sets, tuples with nested coloring
- Primitive types with type annotations in debug mode
- Complex nested structures up to 6 levels deep
- Time objects with smart formatting

### Command System
- Text formatting: `</bold>`, `</italic>`, `</underline>`
- Colors: `</red>`, `</#FFFFFF>`, `</rgb(255,0,0)>`
- Background colors: `</bkg blue>`
- Time commands: `</12hr>`, `</tz pst>`, `</no sec>`

## Integration Points
- **All SK Modules**: Universal data formatting
- **SKPath**: Clean file paths in error displays
- **Report Module**: Enhanced logging output
- **Threading**: Thread-safe design throughout

## Use Cases
- Advanced logging with file and key-based reporters
- Rich text formatting with command-based syntax
- Progress tracking with custom bars and spinners
- Complex data structure visualization
- Error handling with beautiful tracebacks

## Performance Features
- Cached ANSI code generation for commands
- Batched progress bar updates for smooth animation
- Terminal capability detection at startup
- Thread-safe operation without Rich bottlenecks
- Smart text wrapping at punctuation boundaries

## Inner Workings and Implementation Details

### FDL System Flow - From Input to Output

The new FDL system uses a registry-based architecture for processing strings from input to final output:

#### Complete Processing Flow Overview

```python
# User Input
fdl.print('</bold, red>User </12hr><username></end red> logged in at <time:login_time>', 
          ("Alice", timestamp))
```

#### Step-by-Step Flow

**Step 1: Public API Entry Point**
```python
# api/public.py - User calls fdl.print()
def print(fdl_string: str, values: Tuple = (), output: str = 'terminal'):
    outputs = _processor.process_string(fdl_string, values)
    # Handle output format and return/print result
```

**Step 2: Main Processor Initialization**
```python
# core/_processor.py - _FDLProcessor.process_string()
def process_string(self, fdl_string: str, values: Tuple = ()) -> Dict[str, str]:
    # 1. Create initial format state
    format_state = _create_format_state(values)
    
    # 2. Parse into sequential elements  
    elements = self._parse_sequential(fdl_string)
    
    # 3. Process each element
    for element in elements:
        format_state = element.process(format_state)
    
    # 4. Apply final formatting
    return format_state.get_final_outputs()
```

**Step 3: Sequential Parsing**
```python
# Input string: '</bold, red>User </12hr><username></end red> logged in at <time:login_time>'

# _parse_sequential() uses regex to find all <...> patterns and splits into:
elements = [
    _CommandElement("bold, red"),        # From </bold, red>
    _TextElement("User "),               # Plain text
    _CommandElement("12hr"),             # From </12hr>  
    _VariableElement("username"),        # From <username>
    _CommandElement("end red"),          # From </end red>
    _TextElement(" logged in at "),     # Plain text
    _ObjectElement("time", "login_time") # From <time:login_time>
]
```

**Step 4: Element Processing Loop**

Each element is processed sequentially, updating the format state:

- **_CommandElement("bold, red")**: Registry routes "bold" and "red" to _TextCommandProcessor
- **_TextElement("User ")**: Adds "User " to all output streams with current formatting
- **_CommandElement("12hr")**: Routes to _TimeCommandProcessor, sets twelve_hour_time = True
- **_VariableElement("username")**: Gets "Alice" from values tuple, adds to outputs
- **_CommandElement("end red")**: Routes to _TextCommandProcessor, removes red color
- **_TextElement(" logged in at ")**: Adds text with current formatting (bold only)
- **_ObjectElement("time", "login_time")**: Routes to _TimeObjectProcessor, formats timestamp

**Step 5: Registry-Based Command Processing**
```python
# _CommandRegistry.process_command("bold", format_state)

# Registry iterates through registered processors in priority order:
for processor_class in [_TextCommandProcessor, _TimeCommandProcessor, _BoxCommandProcessor]:
    if processor_class.can_process("bold"):
        return processor_class.process("bold", format_state)

# _TextCommandProcessor.can_process("bold") returns True
# _TextCommandProcessor.process("bold", format_state) sets bold=True
```

**Step 6: Registry-Based Object Processing**
```python
# _ObjectRegistry.process_object("time", "login_time", format_state)

# Registry has mapping: {"time": _TimeObjectProcessor, "spinner": _SpinnerObjectProcessor}
processor_class = _type_to_processor["time"]  # Gets _TimeObjectProcessor
return processor_class.process_object("time", "login_time", format_state)

# _TimeObjectProcessor handles all time-related objects:
# time, date, date_words, day, time_elapsed, time_ago, time_until
```

**Step 7: Multi-Format Output Generation**
```python
# _ElementProcessor._add_to_outputs()
def _add_to_outputs(self, format_state, content):
    # Terminal (ANSI codes)
    terminal_content = f"{self._generate_ansi_codes(format_state)}{content}"
    format_state.terminal_output.append(terminal_content)
    
    # Plain text (no formatting)
    format_state.plain_output.append(content)
    
    # Markdown (** for bold, * for italic)
    markdown_content = self._apply_markdown_formatting(content, format_state)
    format_state.markdown_output.append(markdown_content)
    
    # HTML (spans with CSS classes)
    html_content = f'<span class="bold red">{content}</span>'
    format_state.html_output.append(html_content)
```

**Step 8: Final Assembly and Output**
```python
# After all elements processed, format_state contains:
format_state.terminal_output = [
    "\033[1m\033[31mUser ",      # Bold red "User "
    "\033[1m\033[31mAlice",      # Bold red "Alice"  
    "\033[1m logged in at ",     # Bold " logged in at "
    "\033[1m2:30 PM",            # Bold "2:30 PM"
    "\033[0m"                    # Reset code
]

# Final assembly:
return {
    'terminal': ''.join(format_state.terminal_output),
    'plain': ''.join(format_state.plain_output),
    'markdown': ''.join(format_state.markdown_output),  
    'html': ''.join(format_state.html_output)
}
```

### Key System Characteristics

#### Registry-Based Routing
- **Commands**: Registry maps commands to processors automatically
- **Objects**: Registry maps object types to processors automatically  
- **No hardcoded lists**: Adding new processors just requires decoration

#### Sequential Processing
- **Order matters**: Elements processed in the order they appear
- **State flows**: Each element receives and updates the format state
- **No complex routing**: Simple for-loop through elements

#### Simultaneous Multi-Format
- **All formats together**: Terminal, plain, markdown, HTML generated simultaneously
- **Same processing**: One pass generates all output types
- **Consistent results**: All formats reflect same formatting decisions

#### Modular Architecture
- **Single responsibility**: Each element/processor handles one thing
- **Easy testing**: Each component can be tested independently
- **Easy extension**: New features require no core modifications

### Flow Summary
```
User Input (fdl.print)
    ↓
Public API (delegates to processor)
    ↓  
Main Processor (creates state, parses, processes)
    ↓
Sequential Parsing (regex → element list)
    ↓
Element Processing Loop:
    ├── Commands → Registry → Processor → Update State
    ├── Text → Add to Outputs (all formats)
    ├── Variables → Get Value → Add to Outputs  
    └── Objects → Registry → Processor → Add to Outputs
    ↓
Final Assembly (join output streams)
    ↓
Return Results (terminal/plain/markdown/html)
```

This registry-based flow makes the system predictable, extensible, and maintainable while providing high performance and consistent multi-format output.