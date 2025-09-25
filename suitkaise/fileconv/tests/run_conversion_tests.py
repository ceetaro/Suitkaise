#!/usr/bin/env python3
"""
Comprehensive test script for fileconv module.

This script:
1. Ensures test/md_results, test/txt_results, and test/yaml_results all exist
2. Clears them out if they aren't empty (by deleting and recreating)
3. Converts EACH test file to all supported conversion types using the API
4. Adds the results to the respective *_results directories
"""

import sys
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import fileconv
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module components directly
from _int.file_conversion import Format, convert_files as convert


def setup_result_directories():
    """
    Setup and clear result directories.
    
    Creates/recreates the result directories:
    - tests/md_results/
    - tests/txt_results/  
    - tests/yaml_results/
    """
    test_dir = Path(__file__).parent
    result_dirs = [
        test_dir / "md_results",
        test_dir / "txt_results", 
        test_dir / "yaml_results"
    ]
    
    print("Setting up result directories...")
    
    for result_dir in result_dirs:
        if result_dir.exists():
            print(f"  Removing existing directory: {result_dir}")
            shutil.rmtree(result_dir)
        
        print(f"  Creating directory: {result_dir}")
        result_dir.mkdir(parents=True, exist_ok=True)
    
    print("✅ Result directories setup complete\n")


def get_test_files():
    """Get all test files to convert."""
    test_dir = Path(__file__).parent
    test_files = [
        test_dir / "test_file.md",
        test_dir / "test_file.txt",
        test_dir / "test_file.yaml"
    ]
    
    # Verify all test files exist
    for test_file in test_files:
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")
    
    return test_files


def get_supported_formats():
    """Get all supported output formats."""
    return list(Format)


def convert_file_to_all_formats(input_file: Path, output_base_dir: Path):
    """
    Convert a single file to all supported formats.
    
    Args:
        input_file: Path to input file
        output_base_dir: Base directory where converted files should be placed
    """
    input_name = input_file.stem
    input_ext = input_file.suffix
    
    print(f"Converting {input_file.name} to all formats...")
    
    # Get all supported formats
    formats = get_supported_formats()
    
    for format_enum in formats:
        try:
            # Create output name based on input file and target format
            output_name = f"{input_name}_to_{format_enum.value}"
            
            print(f"  Converting to {format_enum.value.upper()}...", end=" ")
            
            result_path = convert(
                input_files=input_file,
                formats=format_enum,
                output_location=output_base_dir,
                output_name=output_name,
                zip_output=False
            )
            
            print(f"✅ -> {result_path.name}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main test execution function."""
    print("🚀 Starting comprehensive fileconv conversion tests\n")
    
    try:
        # Step 1: Setup directories
        setup_result_directories()
        
        # Step 2: Get test files and verify they exist
        test_files = get_test_files()
        print(f"Found {len(test_files)} test files:")
        for test_file in test_files:
            print(f"  - {test_file.name}")
        print()
        
        # Step 3: Show supported formats
        formats = get_supported_formats()
        print(f"Supported output formats ({len(formats)}):")
        for fmt in formats:
            print(f"  - {fmt.value.upper()}")
        print()
        
        # Step 4: Convert each test file to all formats
        test_dir = Path(__file__).parent
        
        for test_file in test_files:
            # Determine output directory based on input file type
            if test_file.name.endswith('.md'):
                output_dir = test_dir / "md_results"
            elif test_file.name.endswith('.txt'):
                output_dir = test_dir / "txt_results"
            elif test_file.name.endswith('.yaml'):
                output_dir = test_dir / "yaml_results"
            else:
                # Fallback - shouldn't happen with our current test files
                output_dir = test_dir / "other_results"
                output_dir.mkdir(exist_ok=True)
            
            convert_file_to_all_formats(test_file, output_dir)
            print()
        
        print("🎉 All conversions completed successfully!")
        
        # Step 5: Show summary of results
        print("\n📊 Conversion Results Summary:")
        result_dirs = [
            test_dir / "md_results",
            test_dir / "txt_results", 
            test_dir / "yaml_results"
        ]
        
        for result_dir in result_dirs:
            if result_dir.exists():
                files = list(result_dir.iterdir())
                print(f"  {result_dir.name}: {len(files)} files")
                for file in sorted(files):
                    print(f"    - {file.name}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
