# tests/conftest.py

"""
Pytest configuration for Suitkaise tests.

This file contains shared fixtures and configuration for all tests.
"""

import sys
import os
from pathlib import Path
import pytest

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment."""
    # Ensure we're using the local suitkaise package
    import suitkaise
    print(f"Testing with suitkaise from: {suitkaise.__file__ if hasattr(suitkaise, '__file__') else 'built-in'}")

@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def project_root():
    """Provide the project root path."""
    return str(Path(__file__).parent.parent)

# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    # Register custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")

def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add markers automatically based on test names/locations
    for item in items:
        # Mark stress tests as slow
        if "stress" in item.name.lower() or "concurrent" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        
        # Mark as unit tests by default
        if not any(marker.name in ["integration", "slow"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)