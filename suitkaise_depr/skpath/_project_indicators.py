# add license here

# suitkaise/skpath/_project_indicators.py

project_indicators = {
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
                "file_groups{'license'}",
                "file_groups{'readme'}",
                "file_groups{'requirements'}"
            },
            "indicators": {
                "setup.py",
                "setup.cfg",
                "pyproject.toml",
                "tox.ini",
                "file_groups{'env'}",
                ".gitignore",
                ".dockerignore",
                "__init__.py"
            },
            "weak_indicators": {
                "Makefile",
                "docker-compose.*",
                "Dockerfile",
                "file_groups{'examples'}",
                "pyrightconfig.json"
            }
        },

        "common_proj_root_dirs": {
            "strong_indicators": {
                "dir_groups{'app'}",
                "dir_groups{'data'}",
                "dir_groups{'doc'}",
                "dir_groups{'test'}"
            },
            "indicators": {
                "dir_groups{'git'}",
                "dir_groups{'source'}",
                "dir_groups{'cache'}",
                "dir_groups{'examples'}",
                "dir_groups{'env'}",
                ".idea",
                "dist",
                "build",
                ".vscode",
                "*.egg-info"
            }  
        }
    }

