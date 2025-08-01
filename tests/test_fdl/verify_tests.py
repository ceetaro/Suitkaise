#!/usr/bin/env python3
"""
Simple verification script to check test structure without pytest.
"""

import sys
import os

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def verify_progress_bar_tests():
    """Verify progress bar test structure."""
    print("🔍 Verifying Progress Bar Tests...")
    
    try:
        # Import the test classes
        from test_progress_bar import (
            TestProgressBarInitialization,
            TestProgressBarProperties,
            TestProgressBarCoreOperations,
            TestProgressBarFormatting,
            TestProgressBarOutput,
            TestProgressBarUtilityMethods,
            TestProgressBarMemoryManagement,
            TestProgressBarContextManager,
            TestProgressBarStringRepresentation,
            TestProgressBarThreadSafety,
            TestProgressBarEdgeCases,
            TestProgressBarConvenienceFunction,
            TestProgressBarVisualDemonstration
        )
        
        print("  ✅ All progress bar test classes imported successfully")
        
        # Test basic instantiation
        test_init = TestProgressBarInitialization()
        print("  ✅ Progress bar test classes can be instantiated")
        
        # Check if we have the main classes
        from suitkaise.fdl._int.classes.progress_bar import _ProgressBar
        print("  ✅ Progress bar class can be imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Progress bar test verification failed: {e}")
        return False

def verify_table_tests():
    """Verify table test structure."""
    print("🔍 Verifying Table Tests...")
    
    try:
        # Import the test classes
        from test_table import (
            TestTableInitialization,
            TestTableHeaderManagement,
            TestTableDataManagement,
            TestTableCellAccess,
            TestTableFormatting,
            TestTableUtilityMethods,
            TestTableMemoryManagement,
            TestTableDisplayMethods,
            TestTableEdgeCases,
            TestTableVisualDemonstration
        )
        
        print("  ✅ All table test classes imported successfully")
        
        # Test basic instantiation
        test_init = TestTableInitialization()
        print("  ✅ Table test classes can be instantiated")
        
        # Check if we have the main classes
        from suitkaise.fdl._int.classes.table import _Table
        print("  ✅ Table class can be imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Table test verification failed: {e}")
        return False

def verify_basic_functionality():
    """Verify basic functionality works."""
    print("🔍 Verifying Basic Functionality...")
    
    try:
        # Test progress bar creation
        from suitkaise.fdl._int.classes.progress_bar import _ProgressBar
        from unittest.mock import patch
        
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            progress = _ProgressBar(total=100)
            assert progress.total == 100.0
            print("  ✅ Progress bar basic functionality works")
        
        # Test table creation
        from suitkaise.fdl._int.classes.table import _Table
        table = _Table()
        table.add_header("Test")
        assert table.column_count == 1
        print("  ✅ Table basic functionality works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Basic functionality verification failed: {e}")
        return False

def main():
    """Main verification function."""
    print("🚀 FDL Test Verification")
    print("=" * 50)
    
    all_passed = True
    
    all_passed &= verify_progress_bar_tests()
    all_passed &= verify_table_tests()
    all_passed &= verify_basic_functionality()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL VERIFICATIONS PASSED!")
        print("The test structure is correct and basic functionality works.")
    else:
        print("❌ SOME VERIFICATIONS FAILED!")
        print("Check the errors above for details.")
    print("=" * 50)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)