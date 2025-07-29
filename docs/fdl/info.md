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