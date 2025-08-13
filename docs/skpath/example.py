#!/usr/bin/env python3
"""
SKPath Examples - Runnable demonstrations of SKPath functionality

Run this file to see SKPath in action with various real-world scenarios.
Each example can be run independently by uncommenting the desired section.
"""

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Import SKPath
try:
    from suitkaise import skpath
    print("✅ SKPath imported successfully!")
except ImportError as e:
    print(f"❌ Error importing SKPath: {e}")
    print("Make sure suitkaise is installed and in your Python path")
    exit(1)

def separator(title):
    """Print a nice separator for examples"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def example_basic_usage():
    """Demonstrate basic SKPath usage"""
    separator("Basic SKPath Usage")
    
    # Create SKPath objects
    current_file = skpath.SKPath()  # Auto-detects this file
    project_root = skpath.get_project_root()
    
    print(f"Current file (auto-detected):")
    print(f"  Absolute path: {current_file.ap}")
    print(f"  Normalized path: {current_file.np}")
    print(f"  Project root: {project_root}")
    
    # Create SKPath from string
    readme_path = skpath.SKPath("README.md")
    print(f"\nREADME.md path:")
    print(f"  Absolute path: {readme_path.ap}")
    print(f"  Normalized path: {readme_path.np}")
    print(f"  Exists: {readme_path.exists()}")

def example_autopath_decorator():
    """Demonstrate the @autopath decorator"""
    separator("AutoPath Decorator Magic")
    
    @skpath.autopath()
    def read_file_content(file_path):
        """Function that automatically converts path strings to SKPaths"""
        print(f"  Processing: {file_path.np}")
        print(f"  Type: {type(file_path)}")
        if file_path.exists():
            with open(file_path) as f:
                content = f.read()
            return len(content.split('\n'))
        return 0
    
    # Test with different path formats
    print("Testing autopath with different inputs:")
    
    # String path - gets converted to SKPath automatically
    lines = read_file_content("docs/skpath/concept.md")
    print(f"  Lines in concept.md: {lines}")
    
    # Already an SKPath - passed through
    info_path = skpath.SKPath("docs/skpath/info.md")
    lines = read_file_content(info_path)
    print(f"  Lines in info.md: {lines}")

def example_path_comparison():
    """Demonstrate intelligent path comparison"""
    separator("Intelligent Path Comparison")
    
    # Different representations of the same file
    path1 = "docs/skpath/concept.md"
    path2 = skpath.SKPath("docs/skpath/concept.md")
    path3 = skpath.get_project_root() / "docs" / "skpath" / "concept.md" # type: ignore
    
    print("Comparing different path representations:")
    print(f"  Path 1: {path1} (string)")
    print(f"  Path 2: {path2.np} (SKPath)")
    print(f"  Path 3: {Path(path3).relative_to(skpath.get_project_root())} (pathlib)") # type: ignore
    
    print(f"\nComparisons using equalpaths():")
    print(f"  path1 == path2: {skpath.equalpaths(path1, path2)}")
    print(f"  path2 == path3: {skpath.equalpaths(path2, path3)}")
    print(f"  path1 == path3: {skpath.equalpaths(path1, path3)}")

def example_path_ids():
    """Demonstrate path ID generation"""
    separator("Path ID Generation")
    
    files = [
        "docs/skpath/concept.md",
        "docs/skpath/info.md", 
        "docs/skpath/example.py",
        "suitkaise/skpath/api.py"
    ]
    
    print("Generating reproducible path IDs:")
    for file_path in files:
        if skpath.SKPath(file_path).exists():
            full_id = skpath.path_id(file_path)
            short_id = skpath.path_id_short(file_path)
            print(f"  {file_path}")
            print(f"    Short ID: {short_id}")
            print(f"    Full ID:  {full_id}")

def example_project_structure():
    """Demonstrate project structure analysis"""
    separator("Project Structure Analysis")
    
    print("Getting all project paths:")
    project_paths = skpath.get_all_project_paths()
    print(f"  Total files found: {len(project_paths)}")
    
    # Show first few paths
    print(f"  First 10 files:")
    for path in project_paths[:10]:
        print(f"    {path.np}")
    
    print(f"\nFiltered by extension (.py files):")
    py_files = [p for p in project_paths if p.suffix == '.py'] # type: ignore
    print(f"  Python files found: {len(py_files)}")
    for path in py_files[:5]:
        print(f"    {path.np}")

def example_project_tree():
    """Demonstrate formatted project tree"""
    separator("Formatted Project Tree")
    
    print("Project structure (max depth 2, directories only):")
    tree = skpath.get_formatted_project_tree(
        max_depth=2,
        show_files=False
    )
    print(tree)

def example_caller_detection():
    """Demonstrate magical caller detection"""
    separator("Magical Caller Detection")
    
    def inner_function():
        """Function that detects its caller"""
        caller = skpath.get_caller_path()
        current_dir = skpath.get_current_dir()
        cwd = skpath.get_cwd()
        
        print(f"Called from: {caller.np}")
        print(f"Current directory: {current_dir.np}")
        print(f"Working directory: {cwd.np}")
    
    print("Calling function that detects caller location:")
    inner_function()

def example_temporary_files():
    """Demonstrate SKPath with temporary files"""
    separator("Working with Temporary Files")
    
    @skpath.autopath()
    def create_temp_file(temp_path=None):
        """Create a temporary file using SKPath"""
        if not temp_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_path = f"temp_example_{timestamp}.txt"
        
        # Create the file
        content = f"This is a temporary file created at {datetime.now()}"
        with open(temp_path, 'w') as f:
            f.write(content)
        
        print(f"Created temporary file: {temp_path.np}")
        print(f"File exists: {temp_path.exists()}")
        
        # Read it back
        with open(temp_path) as f:
            read_content = f.read()
        print(f"Content: {read_content}")
        
        # Clean up
        temp_path.path_object.unlink()
        print(f"Cleaned up: {temp_path.np}")
    
    create_temp_file()

def example_forced_project_root():
    """Demonstrate forced project root functionality"""
    separator("Forced Project Root")
    
    # Show current project root
    current_root = skpath.get_project_root()
    print(f"Current project root: {current_root}")
    
    # Check if there's a forced root
    forced = skpath.get_forced_project_root()
    print(f"Forced project root: {forced}")
    
    # Create a temporary directory to use as forced root
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create required files for project root detection
        (temp_path / "LICENSE").touch()
        (temp_path / "README.md").touch()
        (temp_path / "requirements.txt").touch()
        
        print(f"\nForcing project root to: {temp_path}")
        skpath.force_project_root(temp_path)
        
        # Now SKPath operations use the forced root
        test_path = skpath.SKPath("test_file.txt")
        print(f"Test path with forced root: {test_path.ap}")
        print(f"Normalized path: {test_path.np}")
        
        # Clear the forced root
        skpath.clear_forced_project_root()
        print(f"\nCleared forced root")
        
        # Back to normal
        normal_path = skpath.SKPath("test_file.txt")
        print(f"Test path after clearing: {normal_path.ap}")

def example_module_inspection():
    """Demonstrate module path inspection"""
    separator("Module Path Inspection")
    
    # Get path of various modules
    modules_to_check = [
        'json',          # Built-in module
        'pathlib',       # Standard library
        'suitkaise',     # Our package (if available)
    ]
    
    print("Inspecting module locations:")
    for module_name in modules_to_check:
        try:
            module_path = skpath.get_module_path(module_name)
            if module_path:
                print(f"  {module_name}: {module_path.np}")
            else:
                print(f"  {module_name}: Built-in module (no file)")
        except ImportError:
            print(f"  {module_name}: Not found")
    
    # Get path of this example function
    example_module = skpath.get_module_path(example_module_inspection)
    print(f"\nThis function is defined in: {example_module.np}")

def show_menu():
    """Display the interactive menu"""
    print("\n" + "="*60)
    print("  SKPath Examples - Interactive Menu")
    print("="*60)
    print("  1. Basic SKPath Usage")
    print("  2. AutoPath Decorator Magic")
    print("  3. Intelligent Path Comparison")
    print("  4. Path ID Generation")
    print("  5. Project Structure Analysis")
    print("  6. Formatted Project Tree")
    print("  7. Magical Caller Detection")
    print("  8. Working with Temporary Files")
    print("  9. Forced Project Root")
    print(" 10. Module Path Inspection")
    print(" 11. Run All Examples")
    print("  0. Exit")
    print("="*60)

def get_user_choice():
    """Get user input with validation"""
    while True:
        try:
            choice = input("\nEnter your choice (0-11): ").strip()
            if choice.isdigit() and 0 <= int(choice) <= 11:
                return int(choice)
            else:
                print("❌ Please enter a number between 0 and 11")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            return 0

def run_all_examples():
    """Run all examples in sequence"""
    separator("Running All Examples")
    
    examples = [
        ("Basic Usage", example_basic_usage),
        ("AutoPath Decorator", example_autopath_decorator),
        ("Path Comparison", example_path_comparison),
        ("Path IDs", example_path_ids),
        ("Project Structure", example_project_structure),
        ("Project Tree", example_project_tree),
        ("Caller Detection", example_caller_detection),
        ("Temporary Files", example_temporary_files),
        ("Forced Project Root", example_forced_project_root),
        ("Module Inspection", example_module_inspection),
    ]
    
    for name, func in examples:
        print(f"\n🚀 Running: {name}")
        try:
            func()
            print(f"✅ {name} completed successfully")
        except Exception as e:
            print(f"❌ {name} failed: {e}")
        
        # Pause between examples
        uinput = input("\nPress Enter to continue to next example...\nPress 0 to exit...\n")
        if uinput == "0":
            # exit the loop
            break
    
    print(f"\n{'='*60}")
    print("  🎉 All examples completed!")
    print(f"{'='*60}")

def main():
    """Main interactive loop"""
    print("Welcome to SKPath Examples!")
    print("This interactive demo will show you how SKPath works.")
    
    # Check if SKPath is working
    try:
        root = skpath.get_project_root()
        print(f"✅ SKPath is working! Project root: {root}")
    except Exception as e:
        print(f"❌ SKPath error: {e}")
        return
    
    # Menu mapping
    examples = {
        1: ("Basic SKPath Usage", example_basic_usage),
        2: ("AutoPath Decorator Magic", example_autopath_decorator),
        3: ("Intelligent Path Comparison", example_path_comparison),
        4: ("Path ID Generation", example_path_ids),
        5: ("Project Structure Analysis", example_project_structure),
        6: ("Formatted Project Tree", example_project_tree),
        7: ("Magical Caller Detection", example_caller_detection),
        8: ("Working with Temporary Files", example_temporary_files),
        9: ("Forced Project Root", example_forced_project_root),
        10: ("Module Path Inspection", example_module_inspection),
        11: ("Run All Examples", run_all_examples),
    }
    
    while True:
        show_menu()
        choice = get_user_choice()
        
        if choice == 0:
            print("\n👋 Thanks for exploring SKPath! Goodbye!")
            break
        
        if choice in examples:
            name, func = examples[choice]
            print(f"\n🚀 Running: {name}")
            try:
                func()
                print(f"\n✅ {name} completed successfully!")
            except Exception as e:
                print(f"\n❌ {name} failed: {e}")
            
            # Pause before returning to menu
            input("\nPress Enter to return to menu...")
        else:
            print("❌ Invalid choice, please try again.")

if __name__ == "__main__":
    main()
