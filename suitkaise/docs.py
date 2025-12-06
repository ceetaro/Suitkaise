"""
Download suitkaise documentation to your Downloads folder.

Usage:
    from suitkaise import docs

    docs.download("/a/specific/file/path")
    docs.download() # downloads to detected project root

    with Permission():
        docs.download() # can send to Downloads folder

    # if no Permission and no proj root detected, it will raise an error
"""

import os
import shutil
from contextvars import ContextVar
from suitkaise import skpath


MODULES = ["cerial", "circuit", "sktime", "skpath", "processing"]

_downloads_permission: ContextVar[bool] = ContextVar("_downloads_permission", default=False)


class Permission:
    """Context manager that grants permission to use ~/Downloads as destination."""
    
    def __enter__(self):
        self._token = _downloads_permission.set(True)
        return self
    
    def __exit__(self, *_):
        _downloads_permission.reset(self._token)


def _get_destination() -> skpath.SKPath:
    """Determine destination: project root, or Downloads if permitted."""
    try:
        project_root = skpath.get_project_root()
        if project_root is not None:
            return project_root / "suitkaise-docs"
    except Exception:
        pass
    
    if _downloads_permission.get():
        home = skpath.SKPath(os.path.expanduser("~"))
        return home / "Downloads" / "suitkaise-docs"
    
    raise RuntimeError(
        "No project root detected and no Permission granted.\n"
        "Either call from within a project, provide an explicit path,\n"
        "or use: with docs.Permission(): docs.download()"
    )


def download(destination: skpath.AnyPath | None = None):
    """
    Download info.md and concept.md for each module.
    
    Args:
        destination: Explicit path. If None, uses detected project root
                     or ~/Downloads (if inside Permission context).

    To send to Downloads folder:
    ```python
    with Permission():
        docs.download()
    ```
    """
    if destination is not None:
        dest_dir = skpath.SKPath(destination) / "suitkaise-docs"
    else:
        dest_dir = _get_destination()
    
    # Find the docs directory relative to this file
    docs_dir = skpath.SKPath(__file__).parent.parent / "docs"
    
    # Clean up existing export folder if it exists
    if dest_dir.exists:
        shutil.rmtree(dest_dir)
    
    os.makedirs(dest_dir, exist_ok=True)
    
    exported = []
    
    for module_name in MODULES:
        module_dir = docs_dir / module_name
        
        if not module_dir.exists:
            continue
        
        info_file = module_dir / "info.md"
        concept_file = module_dir / "concept.md"
        
        if info_file.exists and concept_file.exists:
            module_export_dir = dest_dir / module_name
            os.makedirs(module_export_dir, exist_ok=True)
            
            shutil.copy2(info_file, module_export_dir / "info.md")
            shutil.copy2(concept_file, module_export_dir / "concept.md")
            
            exported.append(module_name)
    
    print(f"\n📁 Downloaded to: {dest_dir}\n")
    
    for name in exported:
        print(f"  • {name}/")
        print(f"      info.md")
        print(f"      concept.md")
    
    print()

