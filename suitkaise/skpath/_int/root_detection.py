
from .skpath import SKPath


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
    
    def __init__(self, indicators: Optional[Dict] = None):
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

    def __init__(self, indicators: Optional[Dict] = None, confidence_threshold: float = 0.5):
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
        self._lock = threading.RLock()  # Thread-safe access to forced root
        
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
        
        with self._lock:
            self._forced_root = forced_path
    
    def clear_forced_root(self) -> None:
        """Clear any forced project root, returning to auto-detection."""
        with self._lock:
            self._forced_root = None
    
    def get_forced_root(self) -> Optional[Path]:
        """Get the currently forced project root, if any."""
        with self._lock:
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
        with self._lock:
            forced_root = self._forced_root
        
        if forced_root is not None:
            # Validate expected name if provided
            if expected_name is None or forced_root.name.lower() == expected_name.lower():
                return forced_root
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


class _ProjectRootCache(TypedDict):
    root: Optional[Path]
    cache_key: Optional[str]


class _IgnorePatternsCache(TypedDict):
    patterns: Optional[Set[str]]
    cache_key: Optional[str]
    timestamp: float

    # Global detector instance for convenience functions
_global_detector = _ProjectRootDetector()

# Global cache for project root detection
_project_root_cache: _ProjectRootCache = {
    'root': None,
    'cache_key': None,
}

# Store previous auto-detected cache to restore after clearing a forced root
_previous_auto_root: Optional[Path] = None
_previous_auto_cache_key: Optional[str] = None

# Global cache for ignore file patterns
_ignore_patterns_cache: _IgnorePatternsCache = {
    'patterns': None,
    'cache_key': None,
    'timestamp': 0.0,
}

# Thread-safe lock for both caches
_cache_lock = threading.RLock()

