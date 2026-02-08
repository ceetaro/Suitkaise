"""
Download suitkaise documentation to your project.

Usage:
    ```python
    from suitkaise import docs

    # download to project root (default)
    docs.download()

    # download to a specific path within your project
    docs.download("path/within/project")

    # download outside project root (requires Permission)
    with docs.Permission():
        docs.download("/some/external/path")
    ```
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .paths import Skpath, get_project_root


# ── internal state ──────────────────────────────────────────────────────────

_permission_granted: bool = False

_DOCS_DIR_NAME = "suitkaise-docs"


# ── Permission context manager ──────────────────────────────────────────────

class Permission:
    """
    Context manager that temporarily allows ``docs.download()`` to write
    outside the project root.

    ```python
    from suitkaise import docs

    with docs.Permission():
        docs.download("/Users/joe/Documents")
    ```
    """

    def __enter__(self) -> "Permission":
        global _permission_granted
        _permission_granted = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        global _permission_granted
        _permission_granted = False


# ── helpers ─────────────────────────────────────────────────────────────────

def _get_bundled_docs_dir() -> Path:
    """Return the path to the bundled suitkaise-docs directory shipped with
    the package."""
    return Path(__file__).resolve().parent / _DOCS_DIR_NAME


def _is_within_project_root(destination: Path, project_root: Path) -> bool:
    """Check if *destination* is inside (or equal to) *project_root*."""
    try:
        destination.resolve().relative_to(project_root.resolve())
        return True
    except ValueError:
        return False


# ── public API ──────────────────────────────────────────────────────────────

def download(path: str | Path | None = None) -> Path:
    """
    Copy the bundled ``suitkaise-docs`` folder to *path*.

    Parameters
    ----------
    path : str | Path | None
        Destination directory where the docs folder will be placed.
        The resulting directory will be ``<path>/suitkaise-docs/``.

        * ``None`` (default) — uses the project root detected by
          ``suitkaise.paths``.
        * A relative or absolute path — normalized through ``Skpath``.

    Returns
    -------
    Path
        The absolute path to the created ``suitkaise-docs`` directory.

    Raises
    ------
    FileNotFoundError
        If the bundled docs directory is missing from the package.
    PermissionError
        If *path* is outside the project root and ``Permission()`` is
        not active.
    """
    source = _get_bundled_docs_dir()
    if not source.is_dir():
        raise FileNotFoundError(
            f"Bundled docs directory not found at {source}. "
            "Your suitkaise installation may be corrupted."
        )

    # resolve destination
    project_root = get_project_root()

    if path is None:
        dest_parent = Path(project_root.ap)
    else:
        normalized = Skpath(str(path))
        dest_parent = Path(normalized.ap)

    # security check: refuse to write outside project root without Permission
    if not _permission_granted and not _is_within_project_root(dest_parent, Path(project_root.ap)):
        raise PermissionError(
            f"Destination '{dest_parent}' is outside the project root "
            f"'{project_root.ap}'. Use `with docs.Permission():` to allow "
            "writing outside the project root."
        )

    dest = dest_parent / _DOCS_DIR_NAME

    # if it already exists, remove it so we get a clean copy
    if dest.exists():
        shutil.rmtree(dest)

    shutil.copytree(source, dest)

    print(f"suitkaise docs downloaded to: {dest}")
    return dest
