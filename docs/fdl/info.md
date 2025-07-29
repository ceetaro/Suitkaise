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

Based on the actual FDL implementation, the system uses:

### Performance Architecture
- **Thread-safe design**: Custom progress bars, spinners, and tables avoid Rich's threading bottlenecks
- **Batched updates**: Progress bars use submitted updates with smooth animation
- **Cached terminal detection**: Terminal width/capabilities detected once at startup

### Command Processing
1. **Parser**: Splits messages into command and text segments
2. **Command processor**: Converts commands to ANSI codes with caching
3. **Renderer**: Combines everything into final output with smart wrapping
4. **Format state**: Tracks formatting, colors, box status, and time settings

### Optimization Strategies
- Simple commands cached on launch
- Color conversions cached on first encounter
- Format objects cached for reuse
- Terminal width measured once with 80-character minimum
- Smart text wrapping at spaces, dashes, periods, commas, and punctuation