"""
Simple Progress Bar Test - No pytest required
"""

import sys
import os
from unittest.mock import Mock, patch

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_basic_progress_bar():
    """Test basic progress bar functionality."""
    print("Testing basic progress bar functionality...")
    
    from suitkaise.fdl._int.classes.progress_bar import _ProgressBar, ProgressBarError
    
    # Test initialization
    with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
        mock_terminal.return_value.width = 80
        
        progress = _ProgressBar(total=100)
        assert progress.total == 100.0
        assert progress.current == 0.0
        assert progress.percentage == 0
        print("  ✅ Progress bar initialization works")
        
        # Test updates
        with patch.object(progress, '_render_and_display'):
            progress.update(25, "Test step")
            assert progress.current == 25.0
            assert progress.percentage == 25
            print("  ✅ Progress bar updates work")
        
        # Test properties
        assert not progress.is_complete
        progress._current = 100.0
        assert progress.is_complete
        print("  ✅ Progress bar properties work")
        
        # Test error conditions
        try:
            _ProgressBar(total=0)
            assert False, "Should have raised error"
        except ProgressBarError:
            print("  ✅ Progress bar error handling works")

def test_basic_table():
    """Test basic table functionality."""
    print("Testing basic table functionality...")
    
    from suitkaise.fdl._int.classes.table import _Table
    
    # Test initialization
    table = _Table()
    assert table.row_count == 0
    assert table.column_count == 0
    print("  ✅ Table initialization works")
    
    # Test headers
    table.add_header("Name")
    table.add_header("Age")
    assert table.column_count == 2
    print("  ✅ Table header management works")
    
    # Test data
    table.add_row_data(["Alice", "25"])
    assert table.row_count == 1
    assert table.get_cell("Name", 1) == "Alice"
    print("  ✅ Table data management works")
    
    # Test cell operations
    table.set_cell("Age", 1, "26")
    assert table.get_cell("Age", 1) == "26"
    print("  ✅ Table cell operations work")

def main():
    """Run all simple tests."""
    print("🚀 FDL Simple Tests")
    print("=" * 40)
    
    try:
        test_basic_progress_bar()
        test_basic_table()
        
        print("\n" + "=" * 40)
        print("✅ ALL SIMPLE TESTS PASSED!")
        print("Basic functionality is working correctly.")
        print("=" * 40)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 40)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)