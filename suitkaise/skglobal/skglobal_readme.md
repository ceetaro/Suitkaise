# SKGlobal - Smart Global Variables for Python

SKGlobal is a Python library that lets you create and manage global variables that can be shared across different processes, directories, and even different Python scripts running at the same time. Think of it as a smart, persistent way to store data that multiple parts of your application can access.

## What Does SKGlobal Do?

Imagine you're working on a large Python project with multiple scripts running simultaneously. You need to share data between them - maybe configuration settings, cached results, or status information. Normally, this is complicated and requires databases, files, or complex inter-process communication.

SKGlobal makes this simple by creating "smart global variables" that:
- 📁 **Automatically organize themselves by directory/project**
- 🔄 **Sync between multiple running processes**
- 💾 **Persist to disk (or stay in memory only)**
- ⏰ **Can automatically delete themselves after a set time**
- 🏗️ **Organize in a two-level hierarchy (project-wide and directory-specific)**

## Quick Start

### Basic Usage

```python
from suitkaise.skglobal.skglobal import create_global, get_global

# Create a global variable
my_data = create_global("user_settings", {"theme": "dark", "language": "en"})

# Get the value
settings = my_data.get()
print(settings)  # {'theme': 'dark', 'language': 'en'}

# Update the value
my_data.set({"theme": "light", "language": "es"})

# Access from another script/process
user_settings = get_global("user_settings")
if user_settings:
    current_settings = user_settings.get()
    print(current_settings)  # {'theme': 'light', 'language': 'es'}
```

### Memory-Only Variables (Don't Save to Disk)

```python
# Create a temporary variable that won't be saved to disk
temp_cache = create_global(
    name="temp_cache", 
    value={"expensive_calculation": 42},
    persistent=False  # Won't be saved to disk
)
```

### Auto-Expiring Variables

```python
# Create a variable that deletes itself after 30 seconds
session_data = create_global(
    name="user_session",
    value={"logged_in": True, "user_id": 123},
    remove_in=30.0  # Seconds
)

# After 30 seconds, this will return None
```

## Understanding the Two-Level System

SKGlobal uses a smart two-level storage system:

### TOP Level (Project-Wide)
- Stored at your project root directory
- Can see ALL variables from everywhere in your project
- Perfect for project-wide settings and shared data

### UNDER Level (Directory-Specific)
- Stored in the specific directory where you create them
- Automatically syncs up to the TOP level
- Great for module-specific data that might be useful elsewhere

```python
from suitkaise.skglobal.skglobal import create_global, GlobalLevel

# Create a project-wide variable (DEFAULT)
app_config = create_global(
    name="app_config",
    value={"debug": True, "version": "1.0"},
    level=GlobalLevel.TOP  # This is the default
)

# Create a directory-specific variable
module_cache = create_global(
    name="module_cache", 
    value={"last_update": "2025-01-15"},
    level=GlobalLevel.UNDER  # Specific to this directory
)
```

## Advanced Features

### Working Without Cross-Process Sync

If you don't need to share between processes (maybe just within one script), you can disable syncing for better performance:

```python
# Faster, but won't sync between processes
local_only = create_global(
    name="local_cache",
    value={"data": "important stuff"},
    auto_sync=False  # No cross-process sharing
)
```

### Custom Storage Paths

```python
# Store in a specific directory
custom_global = create_global(
    name="custom_data",
    value={"info": "stored elsewhere"},
    path="/path/to/specific/directory"  # Custom location
)
```

### Delayed Creation

Sometimes you want to set up a global variable but not create it immediately:

```python
from suitkaise.skglobal.skglobal import SKGlobal

# Set up the variable but don't create it yet
my_global, creator_function = SKGlobal.create(
    name="delayed_var",
    value={"status": "ready"},
    auto_create=False  # Don't create immediately
)

# Later, when you're ready...
creator_function()  # Now it's created
```

## Common Patterns

### Configuration Management

```python
# In your main app file
app_config = create_global(
    name="app_config",
    value={
        "database_url": "postgresql://localhost/mydb",
        "api_key": "secret123",
        "debug_mode": False
    }
)

# In any other file in your project
config = get_global("app_config")
if config:
    db_url = config.get()["database_url"]
    # Use the database URL...
```

### Caching Expensive Operations

```python
# Cache results that are expensive to compute
def get_expensive_data():
    cache = get_global("expensive_cache")
    
    if cache:
        cached_result = cache.get()
        if cached_result:
            print("Using cached result!")
            return cached_result
    
    # Compute expensive result
    result = perform_expensive_calculation()
    
    # Cache it for 5 minutes (300 seconds)
    create_global(
        name="expensive_cache",
        value=result,
        remove_in=300.0
    )
    
    return result
```

### Inter-Process Communication

```python
# Process 1: Data producer
status_monitor = create_global(
    name="process_status",
    value={"status": "starting", "progress": 0}
)

# Update status as work progresses
status_monitor.set({"status": "processing", "progress": 50})
status_monitor.set({"status": "complete", "progress": 100})

# Process 2: Data consumer
import time

def monitor_other_process():
    while True:
        status = get_global("process_status")
        if status:
            current_status = status.get()
            print(f"Other process: {current_status}")
            
            if current_status.get("status") == "complete":
                break
        
        time.sleep(1)  # Check every second
```

## Utility Functions

### Check System Health

```python
from suitkaise.skglobal.skglobal import health_check, get_system_stats

# Check if everything is working properly
health = health_check()
print(f"System status: {health['status']}")

# Get detailed statistics
stats = get_system_stats()
print(f"Total operations: {stats}")
```

### File Management

```python
from suitkaise.skglobal.skglobal import get_sk_file_info, print_sk_file_info

# See what files SKGlobal has created
print_sk_file_info()

# Get detailed file information
file_info = get_sk_file_info()
print(f"Storage files: {file_info['file_count']}")
```

## Testing and Cleanup

### Safe Testing

```python
from suitkaise.skglobal.skglobal import test_session

# Automatically clean up test files
with test_session() as session:
    # Create test globals
    test_var = create_global("test_data", {"test": True})
    
    # Do your testing...
    
    # Files automatically cleaned up when exiting the 'with' block
```

### Manual Cleanup

```python
from suitkaise.skglobal.skglobal import cleanup_test_files

# See what would be deleted (dry run)
cleanup_info = cleanup_test_files(dry_run=True)
print(f"Would delete {cleanup_info['total_deleted']} files")

# Actually delete test files
cleanup_info = cleanup_test_files(dry_run=False)
print(f"Deleted {cleanup_info['total_deleted']} files")
```

## Error Handling

```python
from suitkaise.skglobal.skglobal import SKGlobalError, create_global

try:
    # This might fail if the name already exists
    duplicate_var = create_global("existing_name", "some value")
except SKGlobalError as e:
    print(f"SKGlobal error: {e}")
    # Handle the error appropriately
```

## Best Practices

### 1. Use Descriptive Names
```python
# Good
user_session_data = create_global("user_session_data", {...})

# Avoid
x = create_global("x", {...})
```

### 2. Set Appropriate Expiration Times
```python
# Short-lived session data
session = create_global("session", {...}, remove_in=3600)  # 1 hour

# Long-lived configuration
config = create_global("config", {...})  # No expiration
```

### 3. Use Non-Persistent for Temporary Data
```python
# Don't save temporary calculations to disk
temp_result = create_global(
    "temp_calc", 
    expensive_result, 
    persistent=False
)
```

### 4. Handle Missing Variables Gracefully
```python
def get_user_setting(setting_name, default=None):
    user_config = get_global("user_config")
    if user_config:
        config_data = user_config.get()
        return config_data.get(setting_name, default)
    return default
```

## Troubleshooting

### "Project root not found" Error
This happens when SKGlobal can't figure out your project's root directory. Make sure you have common project files like:
- `setup.py`
- `pyproject.toml`
- `requirements.txt`
- `.git` directory

### Variables Not Syncing Between Processes
1. Make sure `auto_sync=True` (this is the default)
2. Check that both processes can write to the same directory
3. Verify that your data is serializable (can be converted to JSON)

### Performance Issues
1. Use `auto_sync=False` for variables that don't need cross-process sharing
2. Use `persistent=False` for temporary data
3. Set appropriate `remove_in` times to prevent accumulation

### File Permission Errors
Make sure your Python process has read/write permissions to:
- Your project directory
- The `.sk` subdirectory (created automatically)

## How It Works Under the Hood

1. **Storage**: SKGlobal creates a `.sk` directory in your project root to store variable data
2. **Serialization**: Data is stored as JSON files with metadata
3. **Locking**: File locking prevents conflicts when multiple processes access the same data
4. **Hierarchy**: TOP level storage aggregates all UNDER level storages
5. **Cleanup**: Background threads handle automatic variable removal

## What Gets Created

When you use SKGlobal, it creates:
- A `.sk` directory in your project root
- JSON files with names like `gs_dirname_top_abc123.sk`
- Temporary lock files during write operations
- Backup files for safety

All of these can be safely deleted when you're done with your project.

---

**Need Help?** SKGlobal is designed to be simple and reliable. Most common issues are related to file permissions or project structure. Check the troubleshooting section above, and don't hesitate to clean up test files regularly during development!