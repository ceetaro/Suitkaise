"""
SKPath Example - Path Operations and Project Root Detection

This example demonstrates:
- SKPath object creation and usage
- Project root detection
- AutoPath decorator functionality
"""

from suitkaise import skpath, autopath
from typing import Union

def main():
    print("=== Basic SKPath Usage ===")
    
    # Get project root
    root = skpath.get_project_root()
    print(f"Project root: {root}")
    
    # Create SKPath objects
    my_path = skpath.SKPath("docs/examples/sample.txt")
    print(f"SKPath object: {my_path}")
    print(f"Absolute path: {my_path['ap']}")
    print(f"Normalized path: {my_path['np']}")
    
    # Get caller path
    caller_path = skpath.get_caller_path()
    print(f"Caller path: {caller_path}")
    
    # Get current directory
    current_dir = skpath.get_current_dir()
    print(f"Current directory: {current_dir}")
    
    print("\n=== Path Operations ===")
    
    # Path comparison
    path1 = skpath.SKPath("docs/examples/test.py")
    path2 = skpath.SKPath("docs/examples/test.py")
    
    if skpath.equalpaths(path1, path2):
        print("Paths are equal!")
    
    # Path IDs
    path_id = skpath.path_id(path1)
    short_id = skpath.path_idshort(path1)
    print(f"Path ID: {path_id}")
    print(f"Short ID: {short_id}")
    
    print("\n=== Project Structure ===")
    
    # Get all project paths
    try:
        all_paths = skpath.get_all_project_paths(as_str=True)
        print(f"Found {len(all_paths)} files in project")
        
        # Show first few paths
        for i, path in enumerate(all_paths[:5]):
            print(f"  {i+1}. {path}")
        if len(all_paths) > 5:
            print(f"  ... and {len(all_paths) - 5} more")
    except Exception as e:
        print(f"Could not get project paths: {e}")
    
    # Get project structure
    try:
        structure = skpath.get_project_structure()
        print(f"Project structure keys: {list(structure.keys())[:5]}")
    except Exception as e:
        print(f"Could not get project structure: {e}")
    
    print("\n=== AutoPath Decorator Examples ===")
    
    # Basic autopath usage
    @autopath()
    def process_file(file_path: Union[str, dict] = None):
        """Process a file with automatic path conversion"""
        print(f"Processing file: {file_path}")
        if isinstance(file_path, dict):
            print(f"  Absolute: {file_path.get('ap', 'N/A')}")
            print(f"  Normalized: {file_path.get('np', 'N/A')}")
        return f"Processed: {file_path}"
    
    # Test with string path
    result = process_file("docs/examples/test.txt")
    print(f"Result: {result}")
    
    # AutoPath with default path
    @autopath(defaultpath="docs/default.txt")
    def save_data(data, file_path: Union[str, dict] = None):
        """Save data with default path fallback"""
        print(f"Saving data to: {file_path}")
        return f"Saved data to {file_path}"
    
    # Test without providing path (uses default)
    result = save_data("sample data")
    print(f"Result: {result}")
    
    # AutoPath with autofill
    @autopath(autofill=True)
    def backup_file(file_path: Union[str, dict] = None):
        """Backup file with automatic caller path detection"""
        print(f"Backing up: {file_path}")
        return f"Backed up: {file_path}"
    
    # Test without path (uses caller file)
    result = backup_file()
    print(f"Result: {result}")

if __name__ == "__main__":
    main()