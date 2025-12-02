# FileConv Dependencies

This document lists all the dependencies required for the fileconv module to function properly.

## Required Dependencies

The fileconv module requires different dependencies depending on which file formats you want to support:

### Core Dependencies (Always Required)
- **Python 3.8+** - Base Python version requirement

### Format-Specific Dependencies

#### YAML Support (.yaml, .yml files)
- **PyYAML** - For parsing and generating YAML files
  ```bash
  pip install PyYAML
  ```

#### DOCX Support (.docx files)
- **python-docx** - For reading and writing Microsoft Word documents
- **Pillow** - For image handling in DOCX files
  ```bash
  pip install python-docx pillow
  ```

#### PDF Support (.pdf files)
- **reportlab** - For generating PDF documents
  ```bash
  pip install reportlab
  ```

#### Formats with No External Dependencies
The following formats use only Python's standard library:
- **Markdown** (.md, .markdown)
- **Plain Text** (.txt, .text)
- **HTML** (.html)

## Installation Commands

### Install All Dependencies
To support all file formats, install all dependencies at once:
```bash
pip install PyYAML python-docx pillow reportlab
```

### Minimal Installation
If you only need basic text, markdown, and HTML support:
```bash
# No additional dependencies needed - uses only standard library
```

### Selective Installation
Install only what you need:

**For YAML support only:**
```bash
pip install PyYAML
```

**For DOCX support only:**
```bash
pip install python-docx pillow
```

**For PDF support only:**
```bash
pip install reportlab
```

## Dependency Details

| Format | Input Support | Output Support | Dependencies | Notes |
|--------|---------------|----------------|--------------|-------|
| Markdown | ✅ | ✅ | None | Uses standard library |
| TXT | ✅ | ✅ | None | Uses standard library |
| HTML | ❌ | ✅ | None | Uses standard library |
| YAML | ✅ | ✅ | PyYAML | Required for YAML parsing |
| DOCX | ✅ | ✅ | python-docx, pillow | Pillow needed for image support |
| PDF | ❌ | ✅ | reportlab | Has fallback to text if not installed |

## Graceful Degradation

The fileconv module is designed to work gracefully when optional dependencies are missing:

- **Missing PyYAML**: YAML files will be treated as plain text with error messages
- **Missing python-docx**: DOCX parsing will return error messages  
- **Missing reportlab**: PDF generation will fall back to text files with .pdf extension

## Checking Dependencies

You can check which dependencies are available using the module's built-in function:

```python
from fileconv import check_dependencies, Format

# Check dependencies for a specific format
deps = check_dependencies(Format.PDF)
print(f"PDF dependencies: {deps}")

# Check all supported formats
from fileconv import get_supported_output_formats
for fmt in get_supported_output_formats():
    deps = check_dependencies(fmt)
    print(f"{fmt.value}: {deps}")
```

## Requirements.txt

For easy installation, you can create a `requirements.txt` file:

```txt
# Core dependencies for all fileconv features
PyYAML>=6.0
python-docx>=0.8.11
pillow>=9.0.0
reportlab>=3.6.0
```

Then install with:
```bash
pip install -r requirements.txt
```
