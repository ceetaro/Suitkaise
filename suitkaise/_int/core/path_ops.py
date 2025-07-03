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
from pathlib import Path
from typing import Dict, List, Set, Optional, Union, Tuple

# Get the actual suitkaise module base path for robust checking
_SUITKAISE_BASE_PATH = Path(__file__).resolve().parent.parent


def _get_caller_file_path(frames_to_skip: int = 2) -> Path:
    """
    Get the direct file path of the module that called this function.

    Mainly for testing suitkaise itself.
    
    Args:
        frames_to_skip: Number of frames to skip in the call stack
        
    Returns:
        Path to the calling file
    """
    frame = inspect.currentframe()
    try:
        # Skip the specified number of frames to get the caller's frame
        for _ in range(frames_to_skip):
            if frame is not None:
                frame = frame.f_back
        
        if frame is None:
            raise RuntimeError("No caller frame found")
        
        # Get the file path from the caller's frame
        caller_path = frame.f_globals.get('__file__')
        
        if not caller_path:
            raise RuntimeError("Caller frame does not have a file path")
        
        # Normalize and return the path
        return Path(caller_path).resolve().absolute()
    finally:
        del frame


def _get_non_sk_caller_file_path() -> Optional[Path]:
    """
    Get the path of the file that called this function, skipping all suitkaise module files.
    
    This function walks up the call stack until it finds a file that's not part of the
    suitkaise package, returning the first non-suitkaise file it encounters.
    
    Returns:
        Path to the first non-suitkaise calling file, or None if not found
    """
    frame = inspect.currentframe()
    try:
        # Start from the caller's frame
        caller_frame = frame.f_back
        
        # Keep going up the stack until we find a frame that's not from suitkaise
        while caller_frame is not None:
            caller_path = caller_frame.f_globals.get('__file__')
            
            if caller_path:
                try:
                    normalized_caller_path = Path(caller_path).resolve().absolute()
                except (OSError, ValueError):
                    # If we can't normalize this path, skip it
                    caller_frame = caller_frame.f_back
                    continue
                
                # Check if this file is part of the suitkaise package
                if not _is_suitkaise_module(normalized_caller_path):
                    return normalized_caller_path
            
            caller_frame = caller_frame.f_back
        
        # Fallback if we can't find a non-suitkaise file
        return None
    finally:
        del frame


def _is_suitkaise_module(file_path: Path) -> bool:
    """
    Robustly check if a file path belongs to the suitkaise library.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if the file is part of suitkaise library
    """
    try:
        # Resolve both paths to handle symlinks and relative paths
        file_resolved = file_path.resolve()
        suitkaise_resolved = _SUITKAISE_BASE_PATH.resolve()
        
        # Check if file is under suitkaise directory
        try:
            file_resolved.relative_to(suitkaise_resolved)
            return True
        except ValueError:
            # Not under suitkaise directory
            pass
        
        # Additional check: look at common installation patterns
        file_str = str(file_resolved)
        if any(part in file_str for part in ['/suitkaise/', '\\suitkaise\\', 'site-packages/suitkaise']):
            return True
            
        return False
        
    except (OSError, ValueError):
        # If we can't resolve paths, fall back to simple string check
        return 'suitkaise' in str(file_path)


# Project indicators configuration
PROJECT_INDICATORS = {
    "common_ospaths": {
        "macOS": {
            "Applications",
            "Library", 
            "System/.",
            "Users/.",
            "Documents"
        },
        "windows": {
            "Program Files",
            "Program Files (x86)",
            "Users/.",
            "Documents"
        },
        "linux": {
            "usr",
            "var", 
            "etc",
            "home/.",
            "opt"
        }
    },
    "file_groups": {
        "license": {
            "LICENSE",
            "LICENSE.*",
            "LICENCE", 
            "LICENCE.*",
            "license",
            "license.*",
            "licence",
            "licence.*",
        },
        "readme": {
            "README",
            "README.*",
            "readme",
            "readme.*"
        },
        "requirements": {
            "requirements",
            "requirements.*",
            "requirements-*"
        },
        "env": {
            ".env",
            ".env.*"
        },
        "examples": {
            "example",
            "examples", 
            "example.*",
            "examples.*"
        }
    },
    "dir_groups": {
        "test": {
            "test",
            "tests",
            "test.*",
            "tests.*"
        },
        "doc": {
            "doc",
            "docs",
            "documents",
            "documentation*"
        },
        "data": {
            "data",
            "dataset",
            "datasets",
            "data.*",
            "dataset.*", 
            "datasets.*"
        },
        "app": {
            "app",
            "apps",
            "application",
            "applications",
            "app.*",
            "apps.*",
            "application.*",
            "applications.*"
        },
        "env": {
            "env",
            "venv",
            "venv*",
            "env*",
            ".env",
            ".env.*"
        },
        "git": {
            ".git",
            ".git*",
            ".github",
            ".gitlab"
        },
        "source": {
            "src",
            "source",
            "src.*",
            "source.*"
        },
        "cache": {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache"
        },
        "examples": {
            "example",
            "examples",
            "example.*", 
            "examples.*"
        }
    },
    "common_proj_root_files": {
        "necessary": {
            "@file_groups.license",
            "@file_groups.readme", 
            "@file_groups.requirements"
        },
        "indicators": {
            "setup.py",
            "setup.cfg",
            "pyproject.toml",
            "tox.ini",
            "@file_groups.env",
            ".gitignore",
            ".dockerignore",
            "__init__.py"
        },
        "weak_indicators": {
            "Makefile",
            "docker-compose.*",
            "Dockerfile",
            "@file_groups.examples",
            "pyrightconfig.json"
        }
    },
    "common_proj_root_dirs": {
        "strong_indicators": {
            "@dir_groups.app",
            "@dir_groups.data",
            "@dir_groups.doc", 
            "@dir_groups.test"
        },
        "indicators": {
            "@dir_groups.git",
            "@dir_groups.source",
            "@dir_groups.cache",
            "@dir_groups.examples",
            "@dir_groups.env",
            ".idea",
            "dist",
            "build",
            ".vscode",
            "*.egg-info"
        }
    }
}


class _IndicatorExpander:
    """
    Expands group references and patterns in project indicators.
    
    Handles:
    - @file_groups.license -> expands to actual patterns
    - *.txt -> wildcard pattern matching
    - Pattern normalization and validation
    """
    
    def __init__(self, indicators: Dict = None):
        """
        Initialize the indicator expander.
        
        Args:
            indicators: Project indicators dictionary (defaults to PROJECT_INDICATORS)
        """
        self.indicators = indicators or PROJECT_INDICATORS
    
    def expand_reference(self, reference: str) -> Set[str]:
        """
        Expand a group reference like @file_groups.license into actual patterns.
        
        Args:
            reference: Reference string (e.g., "@file_groups.license")
            
        Returns:
            Set of patterns that the reference expands to
        """
        if not reference.startswith('@'):
            # Not a reference, return as-is
            return {reference}
        
        # Parse the reference: @file_groups.license -> ["file_groups", "license"]
        ref_parts = reference[1:].split('.')
        
        if len(ref_parts) != 2:
            # Invalid reference format, return as-is
            return {reference}
        
        group_type, group_name = ref_parts
        
        # Look up the group in indicators
        if group_type in self.indicators and group_name in self.indicators[group_type]:
            return set(self.indicators[group_type][group_name])
        
        # Reference not found, return as-is
        return {reference}
    
    def expand_pattern_set(self, pattern_set: Set[str]) -> Set[str]:
        """
        Expand all references in a set of patterns.
        
        Args:
            pattern_set: Set of patterns that may contain references
            
        Returns:
            Set of expanded patterns with all references resolved
        """
        expanded = set()
        
        for pattern in pattern_set:
            expanded.update(self.expand_reference(pattern))
        
        return expanded
    
    def match_pattern(self, filename: str, pattern: str) -> bool:
        """
        Check if a filename matches a pattern (supports wildcards).
        
        Args:
            filename: Name of file to check
            pattern: Pattern to match against (may contain * and ?)
            
        Returns:
            True if filename matches pattern
        """
        # Case-insensitive matching
        return fnmatch.fnmatch(filename.lower(), pattern.lower())
    
    def find_matches(self, filenames: Set[str], patterns: Set[str]) -> Set[str]:
        """
        Find which filenames match any of the given patterns.
        
        Args:
            filenames: Set of filenames to check
            patterns: Set of patterns to match against
            
        Returns:
            Set of filenames that matched at least one pattern
        """
        # Expand all references in patterns first
        expanded_patterns = self.expand_pattern_set(patterns)
        
        matches = set()
        for filename in filenames:
            for pattern in expanded_patterns:
                if self.match_pattern(filename, pattern):
                    matches.add(filename)
                    break  # Found a match, move to next filename
        
        return matches


class _ProjectRootDetector:
    """
    Sophisticated project root detection using configurable indicators.
    
    Uses a two-phase approach:
    1. Check for necessary files (required to be considered a project root)
    2. Score based on other indicators to determine confidence
    """

    def __init__(self, indicators: Dict = None, confidence_threshold: float = 0.5):
        """
        Initialize the project root detector.
        
        Args:
            indicators: Project indicators configuration
            confidence_threshold: Minimum confidence score for non-necessary indicators
        """
        self.indicators = indicators or PROJECT_INDICATORS
        self.expander = _IndicatorExpander(self.indicators)
        self.confidence_threshold = confidence_threshold
        self._forced_root = None  # Override for project root
        
        # Scoring weights for different indicator types (after necessary check passes)
        self.weights = {
            'indicators': 0.3,       # Strong indicators (setup.py, .gitignore, etc.)
            'weak_indicators': 0.1,  # Weak indicators (Makefile, etc.)
            'strong_indicators': 0.4, # Strong directory indicators
            'dir_indicators': 0.2    # Regular directory indicators
        }

    def force_project_root(self, path: Union[str, Path]) -> None:
        """
        Force the project root to a specific path.
        
        Args:
            path: Path to use as project root
        """
        forced_path = Path(path).resolve()
        if not forced_path.exists():
            raise FileNotFoundError(f"Forced project root path does not exist: {forced_path}")
        if not forced_path.is_dir():
            raise NotADirectoryError(f"Forced project root is not a directory: {forced_path}")
        
        self._forced_root = forced_path
    
    def clear_forced_root(self) -> None:
        """Clear any forced project root, returning to auto-detection."""
        self._forced_root = None
    
    def get_forced_root(self) -> Optional[Path]:
        """Get the currently forced project root, if any."""
        return self._forced_root

    def _check_necessary_files(self, files: Set[str]) -> Tuple[bool, Set[str]]:
        """
        Check if directory contains necessary files for a project root.
        
        Args:
            files: Set of filenames in the directory
            
        Returns:
            Tuple of (has_necessary_files, missing_categories)
        """
        file_config = self.indicators['common_proj_root_files']
        necessary_patterns = file_config.get('necessary', set())
        
        missing_categories = set()
        
        for pattern in necessary_patterns:
            matches = self.expander.find_matches(files, {pattern})
            if not matches:
                # Extract category name from @file_groups.license -> license
                if pattern.startswith('@file_groups.'):
                    category = pattern.split('.')[-1]
                    missing_categories.add(category)
                else:
                    missing_categories.add(pattern)
        
        has_all_necessary = len(missing_categories) == 0
        return has_all_necessary, missing_categories
    
    def _scan_directory(self, path: Path) -> Tuple[float, Dict]:
        """
        Scan a directory and calculate its project root confidence score.
        
        Args:
            path: Directory path to scan
            
        Returns:
            Tuple of (confidence_score, scan_details)
        """
        if not path.is_dir():
            return 0.0, {'error': 'Not a directory'}
        
        try:
            # Get directory contents
            items = list(path.iterdir())
            files = {item.name for item in items if item.is_file()}
            directories = {item.name for item in items if item.is_dir()}
            
            details = {
                'files': files,
                'directories': directories,
                'matches': {},
                'scores': {},
                'necessary_files_present': False,
                'missing_necessary': set()
            }
            
            # Phase 1: Check necessary files
            has_necessary, missing = self._check_necessary_files(files)
            details['necessary_files_present'] = has_necessary
            details['missing_necessary'] = missing
            
            if not has_necessary:
                # Cannot be a project root without necessary files
                details['total_score'] = 0.0
                details['rejection_reason'] = f"Missing necessary files: {missing}"
                return 0.0, details
            
            # Phase 2: Score based on other indicators
            score = 0.0
            file_config = self.indicators['common_proj_root_files']
            
            # Score file indicators (excluding necessary)
            for category, patterns in file_config.items():
                if category == 'necessary':
                    continue  # Already checked
                
                matches = self.expander.find_matches(files, patterns)
                category_score = len(matches) * self.weights.get(category, 0.1)
                
                details['matches'][f'file_{category}'] = matches
                details['scores'][f'file_{category}'] = category_score
                score += category_score
            
            # Score directory indicators  
            dir_config = self.indicators['common_proj_root_dirs']
            for category, patterns in dir_config.items():
                matches = self.expander.find_matches(directories, patterns)
                weight_key = 'dir_indicators' if category == 'indicators' else 'strong_indicators'
                category_score = len(matches) * self.weights.get(weight_key, 0.1)
                
                details['matches'][f'dir_{category}'] = matches
                details['scores'][f'dir_{category}'] = category_score
                score += category_score
            
            details['total_score'] = min(score, 1.0)  # Cap at 1.0
            return details['total_score'], details
            
        except (PermissionError, OSError) as e:
            return 0.0, {'error': f'Cannot read directory: {e}'}

    def find_project_root(self, start_path: Optional[Union[str, Path]] = None,
                         expected_name: Optional[str] = None) -> Optional[Path]:
        """
        Find the project root by walking up the directory tree.
        
        Args:
            start_path: Starting path (defaults to auto-detected caller)
            expected_name: Expected project name (must match if provided)
            
        Returns:
            Path to project root if found with sufficient confidence
        """
        # Check for forced root first
        if self._forced_root is not None:
            # Validate expected name if provided
            if expected_name is None or self._forced_root.name.lower() == expected_name.lower():
                return self._forced_root
            else:
                return None  # Forced root doesn't match expected name
        
        # Auto-detection mode
        if start_path is None:
            caller_file = _get_non_sk_caller_file_path()
            if caller_file:
                start_path = caller_file.parent
            else:
                start_path = Path.cwd()
        else:
            start_path = Path(start_path).resolve()
        
        best_candidate = None
        best_score = 0.0
        best_details = {}
        
        current = start_path
        
        # Walk up directory tree
        while True:
            score, details = self._scan_directory(current)
            
            # Check expected name if provided
            name_matches = (expected_name is None or 
                          current.name.lower() == expected_name.lower())
            
            if score > best_score and name_matches:
                best_candidate = current
                best_score = score
                best_details = details
            
            # Early exit for very confident matches
            if score >= 0.9 and name_matches:
                break
            
            # Move to parent
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent
        
        # Return only if confidence threshold is met
        if best_score >= self.confidence_threshold:
            return best_candidate
        
        return None


# Global detector instance for convenience functions
_global_detector = _ProjectRootDetector()


def _get_project_root(start_path: Optional[Union[str, Path]] = None,
                     expected_name: Optional[str] = None) -> Optional[Path]:
    """
    Find the project root directory starting from the caller's file location.
    
    Args:
        start_path: Override starting path (defaults to caller's file location)
        expected_name: Expected project name (returns None if name doesn't match)
        
    Returns:
        Path object pointing to project root, or None if not found
    """
    if start_path is None:
        caller_file = _get_non_sk_caller_file_path()
        if caller_file:
            start_path = caller_file.parent
        else:
            start_path = Path.cwd()
    
    return _global_detector.find_project_root(start_path, expected_name)


def _force_project_root(path: Union[str, Path]) -> None:
    """
    Force the project root to a specific path globally.
    
    Args:
        path: Path to use as project root
    """
    _global_detector.force_project_root(path)


def _clear_forced_project_root() -> None:
    """Clear any forced project root, returning to auto-detection."""
    _global_detector.clear_forced_root()


def _get_forced_project_root() -> Optional[Path]:
    """Get the currently forced project root, if any."""
    return _global_detector.get_forced_root()


def _get_cwd() -> Path:
    """
    Get the current working directory.
    
    Returns:
        Path object for current directory
    """
    return Path.cwd()


def _get_current_dir() -> Path:
    """
    Get the directory of the current calling file.
    
    Returns:
        Path object for the calling file's directory
    """
    caller_file = _get_non_sk_caller_file_path()
    if caller_file:
        return caller_file.parent
    return Path.cwd()


def _equal_paths(path1: Union[str, Path], path2: Union[str, Path]) -> bool:
    """
    Check if two paths are equal, handling different path types.
    
    Args:
        path1: First path to compare
        path2: Second path to compare
        
    Returns:
        True if paths point to the same location
    """
    # Convert both to absolute paths for comparison
    abs1 = Path(path1).resolve()
    abs2 = Path(path2).resolve()
    
    return abs1 == abs2


def _path_id(path: Union[str, Path], short: bool = False) -> str:
    """
    Generate a reproducible ID for a path.
    
    Args:
        path: Path to generate ID for
        short: If True, return a shortened version of the ID
        
    Returns:
        Reproducible string ID for the path
    """
    abs_path = str(Path(path).resolve())
    
    # Create hash
    hash_obj = hashlib.md5(abs_path.encode())
    hash_str = hash_obj.hexdigest()
    
    # Create readable ID from path components
    path_parts = Path(abs_path).parts
    if short:
        # Use only filename and short hash
        filename = Path(abs_path).stem.replace('.', '_')
        short_hash = hash_str[:4]
        return f"{filename}_{short_hash}"
    else:
        # Use path components and longer hash
        safe_parts = [part.replace('.', '_').replace('-', '_') for part in path_parts[-3:]]
        readable = '_'.join(safe_parts)
        return f"{readable}_{hash_str[:8]}"


def _path_id_short(path: Union[str, Path]) -> str:
    """
    Generate a short reproducible ID for a path.
    
    Args:
        path: Path to generate ID for
        
    Returns:
        Short reproducible string ID for the path
    """
    return _path_id(path, short=True)


def _parse_gitignore_file(gitignore_path: Path) -> Set[str]:
    """
    Parse a .gitignore or .dockerignore file and extract ignore patterns.
    
    Args:
        gitignore_path: Path to the ignore file
        
    Returns:
        Set of ignore patterns from the file
    """
    patterns = set()
    
    if not gitignore_path.exists():
        return patterns
    
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Remove leading slash for consistency
                if line.startswith('/'):
                    line = line[1:]
                
                # Convert gitignore patterns to fnmatch patterns
                # Simple conversion - more sophisticated parsing could be added
                patterns.add(line)
                
    except (OSError, UnicodeDecodeError):
        # If we can't read the file, return empty set
        pass
    
    return patterns


def _get_all_project_paths(except_paths: Optional[Union[str, List[str]]] = None,
                          as_str: bool = False,
                          dont_ignore: bool = False,
                          force_root: Optional[Union[str, Path]] = None) -> List[Union[Path, str]]:
    """
    Get all paths in the current project.
    
    Args:
        except_paths: Paths to exclude from results
        as_str: Return string paths instead of Path objects
        dont_ignore: Include paths that would normally be ignored
        force_root: Force a specific project root
        
    Returns:
        List of paths in the project
    """
    if force_root:
        project_root = Path(force_root).resolve()
    else:
        project_root = _get_project_root()
    
    if project_root is None:
        return []
    
    # Convert except_paths to set for faster lookup
    if except_paths is None:
        except_set = set()
    elif isinstance(except_paths, str):
        except_set = {except_paths}
    else:
        except_set = set(except_paths)
    
    # Default ignore patterns
    ignore_patterns = {
        '__pycache__', '.git', '.pytest_cache', '.mypy_cache',
        'node_modules', '.venv', 'venv', 'env', '.env',
        'dist', 'build', '*.egg-info'
    } if not dont_ignore else set()
    
    # Add patterns from .gitignore and .dockerignore files
    if not dont_ignore:
        gitignore_path = project_root / '.gitignore'
        dockerignore_path = project_root / '.dockerignore'
        
        ignore_patterns.update(_parse_gitignore_file(gitignore_path))
        ignore_patterns.update(_parse_gitignore_file(dockerignore_path))
    
    all_paths = []
    
    def should_ignore(path: Path) -> bool:
        """Check if path should be ignored."""
        path_name = path.name
        
        # Check except_paths
        if path_name in except_set:
            return True
        
        # Check ignore patterns
        if not dont_ignore:
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(path_name.lower(), pattern.lower()):
                    return True
        
        return False
    
    # Walk the project directory
    try:
        for root, dirs, files in os.walk(project_root):
            root_path = Path(root)
            
            # Filter directories in-place to avoid walking ignored dirs
            dirs[:] = [d for d in dirs if not should_ignore(root_path / d)]
            
            # Add files
            for file in files:
                file_path = root_path / file
                if not should_ignore(file_path):
                    if as_str:
                        all_paths.append(str(file_path))
                    else:
                        all_paths.append(file_path)
    
    except (PermissionError, OSError):
        # If we can't walk the directory, return empty list
        pass
    
    return all_paths


def _get_project_structure(force_root: Optional[Union[str, Path]] = None) -> Dict:
    """
    Get a nested dictionary representing the project structure.
    
    Args:
        force_root: Custom root directory (defaults to detected project root)
        
    Returns:
        Nested dictionary representing directory structure
    """
    if force_root is None:
        root = _get_project_root()
    else:
        root = Path(force_root)
    
    if root is None or not root.exists():
        return {}
    
    def build_structure(path: Path) -> Dict:
        """Recursively build structure dictionary."""
        structure = {}
        
        try:
            for item in path.iterdir():
                if item.is_dir():
                    # Skip common ignore patterns
                    if item.name.startswith('.') or item.name in {'__pycache__', 'node_modules'}:
                        continue
                    structure[item.name] = build_structure(item)
                else:
                    structure[item.name] = 'file'
        except PermissionError:
            pass
        
        return structure
    
    return build_structure(root)


def _get_formatted_project_tree(force_root: Optional[Union[str, Path]] = None,
                                max_depth: int = 3,
                                show_files: bool = True) -> str:
    """
    Get a formatted string representation of the project structure.

    Uses tree-like characters (│, ├─, └─) to create a visual hierarchy.
    
    Args:
        force_root: Custom root directory (defaults to detected project root)
        max_depth: Maximum depth to display (prevents huge output)
        show_files: Whether to show files or just directories
        
    Returns:
        Formatted string representing directory structure
    """
    if force_root is None:
        root = _get_project_root()
    else:
        root = Path(force_root)
    
    if root is None or not root.exists():
        return "No project root found"
    
    def format_tree(path: Path, prefix: str = "", depth: int = 0) -> List[str]:
        """Recursively format the tree structure."""
        if depth > max_depth:
            return []
        
        lines = []
        
        try:
            # Get directory contents, separated into dirs and files
            items = list(path.iterdir())
            dirs = [item for item in items if item.is_dir() and not item.name.startswith('.')]
            files = [item for item in items if item.is_file() and not item.name.startswith('.')] if show_files else []
            
            # Sort for consistent output
            dirs.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())
            
            all_items = dirs + files
            
            for i, item in enumerate(all_items):
                is_last = i == len(all_items) - 1
                
                # Choose the appropriate tree characters
                current_prefix = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")
                
                # Add the current item
                if item.is_dir():
                    lines.append(f"{prefix}{current_prefix}{item.name}/")
                    # Recursively add subdirectory contents
                    lines.extend(format_tree(item, next_prefix, depth + 1))
                else:
                    lines.append(f"{prefix}{current_prefix}{item.name}")
                    
        except PermissionError:
            lines.append(f"{prefix}[Permission Denied]")
        
        return lines
    
    # Start the tree with the root directory name
    tree_lines = [f"{root.name}/"]
    tree_lines.extend(format_tree(root))
    
    return "\n".join(tree_lines)