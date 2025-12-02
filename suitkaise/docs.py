"""
Download suitkaise documentation to your Downloads folder.

Usage:
    from suitkaise import docs
    docs.download()
"""

import shutil
from pathlib import Path


MODULES = ["cerial", "circuit", "sktime", "skpath"]


def download():
    """
    Download info.md and concept.md for each module to ~/Downloads/suitkaise-docs/
    """
    project_root = Path(__file__).parent.parent
    docs_dir = project_root / "docs"
    downloads_dir = Path.home() / "Downloads" / "suitkaise-docs"
    
    # Clean up existing export folder if it exists
    if downloads_dir.exists():
        shutil.rmtree(downloads_dir)
    
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    exported = []
    
    for module_name in MODULES:
        module_dir = docs_dir / module_name
        
        if not module_dir.exists():
            continue
        
        info_file = module_dir / "info.md"
        concept_file = module_dir / "concept.md"
        
        if info_file.exists() and concept_file.exists():
            module_export_dir = downloads_dir / module_name
            module_export_dir.mkdir(exist_ok=True)
            
            shutil.copy2(info_file, module_export_dir / "info.md")
            shutil.copy2(concept_file, module_export_dir / "concept.md")
            
            exported.append(module_name)
    
    print(f"\n📁 Downloaded to: {downloads_dir}\n")
    
    for name in exported:
        print(f"  • {name}/")
        print(f"      info.md")
        print(f"      concept.md")
    
    print()

