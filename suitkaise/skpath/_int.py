"""
Complete Path Operations System for Suitkaise.

This module provides internal path handling functionality that powers the SKPath module.
It includes sophisticated project root detection, path utilities, and project structure
analysis with automatic user caller detection while ignoring internal suitkaise calls.

Key Features:
- Magical project root detection from user caller's file location
- Sophisticated indicator-based project detection with necessary files requirement
- Force override system for uninitialized projects
- Complete path utilities with user caller detection
- Project structure analysis with .gitignore integration
- Robust suitkaise module detection

The "magic" comes from automatically detecting which user file called our functions,
ignoring any internal suitkaise library calls in the process.
"""

import os
import sys
import fnmatch
import inspect
import hashlib
import importlib
import threading
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Union, Tuple, Any, TypedDict

# ============================================================================
# Internal Exception Classes
# ============================================================================








