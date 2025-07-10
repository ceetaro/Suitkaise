#!/usr/bin/env python3
"""
Test script for terminal detection and Unicode support.

This script tests both the terminal information detection and Unicode feature
support to ensure everything is working correctly.

Run this script to see what your terminal supports:
    python test_terminal_unicode.py
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import your modules with actual project paths
try:
    from suitkaise._int.formatting.terminal import _terminal, TerminalWidthError
    from suitkaise._int.formatting.unicode import (
        _get_unicode_support, 
        _supports_box_drawing, 
        _supports_unicode_spinners, 
        _supports_progress_blocks,
        _get_capabilities
    )
    IMPORTS_OK = True
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running from the correct directory and suitkaise package is available")
    print("Expected structure:")
    print("  suitkaise/")
    print("    _int/")
    print("      core/")
    print("        formatting/")
    print("          terminal.py")
    print("          unicode_support.py")
    IMPORTS_OK = False


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")


def print_property(name: str, value: Any, unit: str = "") -> None:
    """Print a property in a formatted way."""
    status = "✅" if value else "❌" if isinstance(value, bool) else "ℹ️"
    print(f"{status} {name:20}: {value}{unit}")


def test_terminal_info() -> Dict[str, Any]:
    """Test terminal information detection."""
    print_header("TERMINAL INFORMATION")
    
    terminal_info = {}
    
    try:
        # Test width (critical property)
        width = _terminal.width
        terminal_info['width'] = width
        print_property("Width", width, " characters")
    except TerminalWidthError as e:
        terminal_info['width'] = None
        print_property("Width", f"ERROR: {e}")
    
    try:
        # Test other properties
        height = _terminal.height
        terminal_info['height'] = height
        print_property("Height", height, " characters")
    except Exception as e:
        terminal_info['height'] = None
        print_property("Height", f"ERROR: {e}")
    
    try:
        is_tty = _terminal.is_tty
        terminal_info['is_tty'] = is_tty
        print_property("Is TTY", is_tty)
    except Exception as e:
        terminal_info['is_tty'] = None
        print_property("Is TTY", f"ERROR: {e}")
    
    try:
        supports_color = _terminal.supports_color
        terminal_info['supports_color'] = supports_color
        print_property("Supports Color", supports_color)
    except Exception as e:
        terminal_info['supports_color'] = None
        print_property("Supports Color", f"ERROR: {e}")
    
    try:
        encoding = _terminal.encoding
        terminal_info['encoding'] = encoding
        print_property("Encoding", encoding)
    except Exception as e:
        terminal_info['encoding'] = None
        print_property("Encoding", f"ERROR: {e}")
    
    return terminal_info


def test_unicode_support() -> Dict[str, Any]:
    """Test Unicode feature support."""
    print_header("UNICODE FEATURE SUPPORT")
    
    try:
        # Get the Unicode support instance
        unicode_support = _get_unicode_support()
        
        # Test individual features
        box_drawing = _supports_box_drawing()
        spinners = _supports_unicode_spinners()
        progress = _supports_progress_blocks()
        
        print_property("Box Drawing", box_drawing)
        print_property("Unicode Spinners", spinners)
        print_property("Progress Blocks", progress)
        
        # Get full capabilities summary
        capabilities = _get_capabilities()
        
        print("\nDetailed Capabilities:")
        for feature, supported in capabilities.items():
            if feature not in ['is_tty', 'encoding']:  # Already shown above
                print_property(f"  {feature.replace('_', ' ').title()}", supported)
        
        return capabilities
        
    except Exception as e:
        print_property("Unicode Support", f"ERROR: {e}")
        return {}


def test_unicode_characters() -> None:
    """Test actual Unicode character rendering."""
    print_header("UNICODE CHARACTER TEST")
    
    if not IMPORTS_OK:
        print("❌ Cannot test characters - imports failed")
        return
    
    # Test box drawing characters
    print("Box Drawing Characters:")
    if _supports_box_drawing():
        print("  Square: ┌─┐")
        print("          │ │") 
        print("          └─┘")
        print("  Rounded: ╭─╮")
        print("           │ │")
        print("           ╰─╯")
        print("  Double: ╔═╗")
        print("          ║ ║")
        print("          ╚═╝")
        print("  Heavy: ┏━┓")
        print("         ┃ ┃")
        print("         ┗━┛")
    else:
        print("  ASCII fallback: +─+")
        print("                  │ │")
        print("                  +─+")
    
    # Test spinner characters
    print("\nSpinner Characters:")
    if _supports_unicode_spinners():
        print("  Dots: ⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧")
        print("  Arrow3: ▹ ▸ ▹")
    else:
        print("  ASCII fallback: d q p b")
    
    # Test progress characters
    print("\nProgress Characters:")
    if _supports_progress_blocks():
        print("  Smooth: ▏▎▍▌▋▊▉█")
        print("  Full/Empty: ▰▱")
    else:
        print("  ASCII fallback: #-")


def test_environment_info() -> None:
    """Show relevant environment information."""
    print_header("ENVIRONMENT INFORMATION")
    
    # Python version
    print_property("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Platform
    import platform
    print_property("Platform", platform.system())
    
    # Environment variables that affect terminal behavior
    env_vars = ['TERM', 'COLORTERM', 'NO_COLOR', 'COLUMNS', 'LINES', 'FORCE_TERMINAL_FALLBACK']
    print("\nRelevant Environment Variables:")
    for var in env_vars:
        value = os.environ.get(var, "Not set")
        print_property(f"  {var}", value)


def run_comprehensive_test() -> None:
    """Run all tests and provide a summary."""
    print("🧪 Terminal Detection and Unicode Support Test")
    print("=" * 60)
    
    if not IMPORTS_OK:
        print("❌ CRITICAL: Module imports failed!")
        print("Please check that terminal.py and unicode_support.py are available")
        return
    
    # Run all tests
    terminal_info = test_terminal_info()
    unicode_info = test_unicode_support()
    test_unicode_characters()
    test_environment_info()
    
    # Summary
    print_header("SUMMARY")
    
    # Critical checks
    width_ok = terminal_info.get('width') is not None
    tty_detected = terminal_info.get('is_tty', False)
    encoding_detected = terminal_info.get('encoding') not in [None, 'ascii']
    
    print_property("Terminal width detected", width_ok)
    print_property("TTY detected", tty_detected)
    print_property("Unicode encoding", encoding_detected)
    
    if width_ok and tty_detected:
        print("\n✅ Basic terminal detection is working!")
    else:
        print("\n⚠️  Some terminal detection issues found")
    
    unicode_features = sum([
        unicode_info.get('box_drawing', False),
        unicode_info.get('unicode_spinners', False), 
        unicode_info.get('progress_blocks', False)
    ])
    
    print_property(f"Unicode features supported", f"{unicode_features}/3")
    
    if unicode_features > 0:
        print("\n✅ Unicode support is working!")
    else:
        print("\n⚠️  No Unicode features detected (may be expected in some terminals)")
    
    print(f"\n🎯 Your terminal setup:")
    if tty_detected and unicode_features >= 2:
        print("   Excellent! Full Unicode support detected.")
        print("   Your formatting engine can use fancy boxes, spinners, and progress bars.")
    elif tty_detected and unicode_features >= 1:
        print("   Good! Partial Unicode support detected.")
        print("   Your formatting engine will work with some fancy features.")
    elif tty_detected:
        print("   Basic! ASCII-only mode detected.")
        print("   Your formatting engine will use ASCII fallbacks.")
    else:
        print("   Limited! Non-TTY environment detected.")
        print("   Your formatting engine will use minimal output.")


if __name__ == "__main__":
    # Allow force-testing mode
    if len(sys.argv) > 1 and sys.argv[1] == "--force-fallback":
        os.environ['FORCE_TERMINAL_FALLBACK'] = '1'
        print("🔧 Force fallback mode enabled")
    
    run_comprehensive_test()