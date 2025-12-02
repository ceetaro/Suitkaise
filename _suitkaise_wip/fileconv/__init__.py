"""
fileconv - A utility for converting text files between different formats.

fileconv allows you to convert text files to different formats, with a consistent 
output result for the given output type. It uses a special object, `TextFile`, 
that acts as an intermediate step between the input file and the output file.

Supported inputs: markdown, txt, yaml, docx
Supported outputs: markdown, txt, yaml, docx, html, pdf

Usage:
    from suitkaise import fileconv
    
    # Convert single file to single format
    result = fileconv.convert(
        input_files=Path("document.md"), 
        formats=fileconv.Format.HTML,
        output_name="converted_doc",
        output_location=Path("/path/to/output")
    )
    
    # Convert multiple files to multiple formats
    result = fileconv.convert(
        input_files=[Path("doc1.md"), Path("doc2.txt")],
        formats=[fileconv.Format.HTML, fileconv.Format.PDF],
        output_name="batch_conversion",
        zip=True
    )
"""

# Import everything from the public API
from .api import (
    Format,
    convert,
    ConversionError,
    UnsupportedFormatError,
    get_supported_input_formats,
    get_supported_output_formats,
    check_dependencies
)

__all__ = [
    "Format",
    "convert", 
    "ConversionError",
    "UnsupportedFormatError",
    "get_supported_input_formats",
    "get_supported_output_formats",
    "check_dependencies"
]