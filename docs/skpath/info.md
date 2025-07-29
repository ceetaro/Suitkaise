# SKPath Info

## Module Status
- **Implementation**: In development
- **Priority**: High (Gateway module)
- **Dependencies**: None (foundational module)

## Key Components

### SKPath Object
- Dual-path dictionary structure (absolute + normalized)
- String compatibility for standard library integration
- Cross-platform path handling

### Project Root Detection
- Sophisticated indicator-based algorithm
- Multi-tier confidence scoring system
- Support for various project structures

### AutoPath Decorator
- Automatic path conversion for function parameters
- Type-aware conversion (SKPath vs string)
- Configurable default paths and autofill

### Path Operations
- Path comparison and equality checking
- Path ID generation for shorter identifiers
- Project structure analysis and visualization

## Integration Points
- **All SK Modules**: Universal SKPath object acceptance
- **Project Structure**: Automatic organization based on detected root
- **Cross-Platform**: Consistent behavior across operating systems

## Use Cases
- Project root detection and validation
- Cross-platform path handling
- Automatic path normalization
- Project structure analysis
- Path-based organization systems

## Performance Features
- Cached project root detection
- Efficient path comparison
- Minimal overhead for path operations
- Lazy evaluation of path properties