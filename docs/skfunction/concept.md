# SKFunction Concept

## Overview

SKFunction will remain somewhat the same, but with a slightly different approach that makes for broader usage opportunities and isolates it from other suitkaise modules (before, it was dependent on skglobals).

SKFunctions are packaged instances consisting of a callable, args with set values, kwargs with set values, and metadata that helps us reference, find, and do other things with an SKFunction.

## Core Features

- **Preset Arguments**: Allows you to call a function with preset arg values at different times
- **Function Storage**: Store all of a function in one object
- **Delayed Execution**: Delay calling a function until needed
- **Clean Execution**: Cleaner, less time consuming execution through use of callable

Instead of adding args positionally, you can add them just by param name as key and value you want to put in that parameter as value. You can even make a dictionary of args to add to a callable and organize it cleanly!

## Key Benefits

✅ **Encapsulation** - Complete execution context in one object
✅ **Reusability** - Define once, use many times with variations
✅ **Testability** - Isolated, repeatable function objects
✅ **Maintainability** - Centralized parameter management
✅ **Composition** - Build complex operations from simple ones
✅ **Registry Pattern** - Global function discovery and reuse

## Developer Experience Benefits

✅ **No parameter juggling** - Named parameter injection
✅ **State preservation** - Exact execution context saved
✅ **Lazy evaluation** - Define now, execute later
✅ **Performance tracking** - Built-in metrics and monitoring
✅ **Cross-process support** - Serializable function objects

## Before vs After SKFunction

### Before SKFunction:
❌ Remember all parameters every time
❌ Copy-paste settings between scripts
❌ Hard to share setups with team
❌ Re-run expensive reports accidentally

### With SKFunction:
✅ Set up once, use everywhere
✅ Override only what you need to change
✅ Share with entire team automatically
✅ Cache results to save time
✅ Build complex workflows from simple pieces

## Integration with Other Modules

- **SKTree/SKGlobal**: Function registries and discovery
- **XProcess**: Cross-process function execution
- **Caching**: Built-in result caching with metadata flags

## Philosophy

The beginner-friendly part: You don't need to understand multiprocessing, serialization, or caching - you just create functions with presets and the system handles the complexity!

## Goal API Design

The SKFunction API aims to provide intuitive function object creation and management:

```python
# Simple function creation with presets
report_func = skfunction.create("sales_report", generate_report, {
    "format": "PDF",
    "include_charts": True
})

# Call with parameter overrides
result = report_func.call(start_date="2024-01-01", end_date="2024-01-31")

# Function registry and discovery
tree = sktree.connect()
tree.add_to_funcrej("sales_report", report_func)
discovered_func = tree.get_from_funcrej("sales_report")

# Caching decorator
@skfunction.cache_results(ttl=3600)
def expensive_computation(data):
    # Complex processing here
    return result
```

The API should make function reusability effortless while providing powerful caching and discovery features.