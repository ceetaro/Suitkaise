# FDL TODO

## Core Implementation
- [ ] Implement `fprint()` display formatting function
- [ ] Implement `dprint()` debug formatting function
- [ ] Create data type detection and routing system
- [ ] Build recursive formatting engine

## Data Type Formatters
- [ ] List formatter (comma-separated vs structured)
- [ ] Dictionary formatter (key-value vs structured)
- [ ] Set formatter with proper display
- [ ] Tuple formatter
- [ ] Primitive type formatters (int, float, bool, None)
- [ ] Complex type formatters (bytes, complex, range)

## Time and Date Formatting
- [ ] Default time format implementation
- [ ] Default date format implementation
- [ ] Custom format string parser (`{hms6:now}`, `{datePST:now}`)
- [ ] Threshold-based format selection
- [ ] Timezone support and conversion

## Debug System
- [ ] Priority level system (1-5)
- [ ] `set_dprint_level()` filtering
- [ ] Type annotation system
- [ ] Structural indicators (brackets, indentation)
- [ ] Color coding for different types

## Advanced Features
- [ ] Nested structure handling
- [ ] Large data structure optimization
- [ ] Custom formatter registration
- [ ] Output format customization
- [ ] Performance profiling

## Testing & Documentation
- [ ] Unit tests for all data types
- [ ] Format comparison tests
- [ ] Performance benchmarks
- [ ] API documentation
- [ ] Usage examples and tutorials