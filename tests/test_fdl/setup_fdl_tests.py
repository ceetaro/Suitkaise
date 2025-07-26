# tests/test_fdl/setup_fdl_tests.py
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Path to FDL internal modules
FDL_INT_PATH = project_root / "suitkaise" / "fdl" / "_int"

# Core module paths
CORE_PATH = FDL_INT_PATH / "core"
COMMAND_REGISTRY_PATH = CORE_PATH / "command_registry.py"
FORMAT_STATE_PATH = CORE_PATH / "format_state.py"
MAIN_PROCESSOR_PATH = CORE_PATH / "main_processor.py"
OBJECT_REGISTRY_PATH = CORE_PATH / "object_registry.py"

# Elements module paths
ELEMENTS_PATH = FDL_INT_PATH / "elements"
BASE_ELEMENT_PATH = ELEMENTS_PATH / "base_element.py"
COMMAND_ELEMENT_PATH = ELEMENTS_PATH / "command_element.py"
OBJECT_ELEMENT_PATH = ELEMENTS_PATH / "object_element.py"
TEXT_ELEMENT_PATH = ELEMENTS_PATH / "text_element.py"
VARIABLE_ELEMENT_PATH = ELEMENTS_PATH / "variable_element.py"

# Processors module paths
PROCESSORS_PATH = FDL_INT_PATH / "processors"
COMMANDS_PATH = PROCESSORS_PATH / "commands"
OBJECTS_PATH = PROCESSORS_PATH / "objects"

# Setup module paths
SETUP_PATH = FDL_INT_PATH / "setup"
BOX_GENERATOR_PATH = SETUP_PATH / "box_generator.py"
COLOR_CONVERSION_PATH = SETUP_PATH / "color_conversion.py"
TERMINAL_PATH = SETUP_PATH / "terminal.py"
TEXT_JUSTIFICATION_PATH = SETUP_PATH / "text_justification.py"
TEXT_WRAPPING_PATH = SETUP_PATH / "text_wrapping.py"
UNICODE_PATH = SETUP_PATH / "unicode.py"

# Verify all paths exist
def verify_paths():
    """Verify that all expected FDL module paths exist."""
    paths_to_check = [
        ("FDL Internal", FDL_INT_PATH),
        ("Core", CORE_PATH),
        ("Elements", ELEMENTS_PATH),
        ("Processors", PROCESSORS_PATH),
        ("Setup", SETUP_PATH),
        ("Command Registry", COMMAND_REGISTRY_PATH),
        ("Format State", FORMAT_STATE_PATH),
        ("Main Processor", MAIN_PROCESSOR_PATH),
        ("Object Registry", OBJECT_REGISTRY_PATH),
        ("Base Element", BASE_ELEMENT_PATH),
        ("Command Element", COMMAND_ELEMENT_PATH),
        ("Object Element", OBJECT_ELEMENT_PATH),
        ("Text Element", TEXT_ELEMENT_PATH),
        ("Variable Element", VARIABLE_ELEMENT_PATH),
        ("Box Generator", BOX_GENERATOR_PATH),
        ("Color Conversion", COLOR_CONVERSION_PATH),
        ("Terminal", TERMINAL_PATH),
        ("Text Justification", TEXT_JUSTIFICATION_PATH),
        ("Text Wrapping", TEXT_WRAPPING_PATH),
        ("Unicode", UNICODE_PATH),
    ]
    
    missing_paths = []
    for name, path in paths_to_check:
        if not path.exists():
            missing_paths.append(f"{name}: {path}")
    
    if missing_paths:
        print("❌ Missing paths:")
        for path in missing_paths:
            print(f"  - {path}")
        return False
    else:
        print("✅ All FDL module paths verified!")
        return True

if __name__ == "__main__":
    verify_paths()