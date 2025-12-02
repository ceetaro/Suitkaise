"""
User-facing API for the fileconv module.

This module provides the public interface for file conversion operations,
wrapping the internal file_conversion.py with a clean, user-friendly API.
"""

from __future__ import annotations
from pathlib import Path
from typing import Union, List, Optional

from ._int.file_conversion import (
    Format, 
    convert_files, 
    ConversionError, 
    UnsupportedFormatError,
    get_supported_input_formats,
    get_supported_output_formats,
    check_dependencies
)


def convert(
    input_files: Union[Path, List[Path]], 
    formats: Union[Format, List[Format]],
    output_location: Union[str, Path],
    output_name: Optional[str] = None,
    *,
    zip: bool = False,
    max_workers: Optional[int] = None,
    **kwargs
) -> Path:
    """
    Convert files to the specified format(s).
    
    This is the main user-facing function for file conversion. It supports:
    - Single file to single format
    - Multiple files to single format  
    - Single file to multiple formats
    - Multiple files to multiple formats
    
    Args:
        input_files: Single file or list of files to convert
        formats: Output format(s) - can be single Format or list of Formats  
        output_location: Directory where converted files should be placed
        output_name: Custom name for output file/folder (optional)
        zip: Whether to create a zip archive for multiple outputs (keyword-only)
        max_workers: Maximum number of threads for parallel processing (keyword-only)
        **kwargs: Additional conversion options passed to converters
        
    Returns:
        Path to the converted file, folder, or zip archive
        
    Raises:
        ConversionError: If conversion fails
        UnsupportedFormatError: If file format is not supported  
        FileNotFoundError: If input files don't exist
        ValueError: If required parameters are missing
        
    Examples:
        # Convert single file (required positional args)
        result = convert(Path("document.md"), Format.HTML, Path("/output"))
        
        # Convert with custom output name
        result = convert(
            Path("document.md"), 
            Format.HTML,
            Path("/output"),
            "my_document"
        )
        
        # Convert multiple files with keyword options
        result = convert(
            [Path("doc1.md"), Path("doc2.txt")],
            Format.DOCX,
            Path("/output"),
            "batch_docs",
            zip=True
        )
        
        # Convert files to multiple formats with parallel processing
        result = convert(
            Path("document.md"),
            [Format.HTML, Format.PDF, Format.DOCX],
            Path("/output"),
            "multi_format_doc",
            max_workers=4
        )
    """
    return convert_files(
        input_files=input_files,
        formats=formats,
        output_location=output_location,
        output_name=output_name,
        zip_output=zip,
        max_workers=max_workers,
        **kwargs
    )


# Re-export important classes and functions for convenience
__all__ = [
    "Format",
    "convert", 
    "ConversionError",
    "UnsupportedFormatError",
    "get_supported_input_formats",
    "get_supported_output_formats",
    "check_dependencies"
]
