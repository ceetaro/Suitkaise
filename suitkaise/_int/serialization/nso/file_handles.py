"""
File Handles and I/O Objects Serialization Handler

This module provides serialization support for file handles and I/O objects
that cannot be pickled due to their connection to external resources or
system-level state.

SUPPORTED OBJECTS:
==================

1. FILE OBJECTS:
   - TextIOWrapper (open('file.txt', 'r'))
   - BufferedReader/Writer (open('file.bin', 'rb'))
   - Raw file objects
   - File-like objects with read/write methods

2. IN-MEMORY I/O:
   - StringIO objects (text in memory)
   - BytesIO objects (binary data in memory)
   - Other in-memory file-like objects

3. TEMPORARY FILES:
   - TemporaryFile objects
   - NamedTemporaryFile objects
   - SpooledTemporaryFile objects

4. STANDARD STREAMS:
   - sys.stdin, sys.stdout, sys.stderr
   - Other system streams

5. SPECIAL I/O OBJECTS:
   - Compressed file objects (gzip, bz2, lzma)
   - Network file-like objects
   - Custom I/O implementations

SERIALIZATION STRATEGY:
======================

File handle serialization requires different approaches based on the type:

1. **Regular Files**: Store path, mode, position, and metadata
2. **In-Memory Files**: Store the complete content and position
3. **Temporary Files**: Store content (cannot preserve file path)
4. **Standard Streams**: Store reference and recreate connection
5. **Network Files**: Store metadata but cannot recreate connection
6. **Special Files**: Extract what metadata is available

Our approach:
- **Preserve file position** when possible
- **Store file content** for small in-memory files
- **Store file metadata** (path, mode, encoding) for regular files
- **Handle special cases** with appropriate warnings
- **Provide best-effort recreation** with clear limitations

LIMITATIONS:
============
- Network connections cannot be recreated
- Temporary files lose their original file paths
- Very large files are not content-stored (only metadata)
- Some file objects may be in invalid states after recreation
- File locks and exclusive access are not preserved
- External file modifications between serialize/deserialize are not detected

"""

import io
import sys
import os
import tempfile
import gzip
import bz2
import lzma
from pathlib import Path
from typing import Any, Dict, Optional, Union, BinaryIO, TextIO

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class FileHandlesHandler(_NSO_Handler):
    """Handler for file handles and I/O objects."""
    
    def __init__(self):
        """Initialize the file handles handler."""
        super().__init__()
        self._handler_name = "FileHandlesHandler"
        self._priority = 45  # Moderate priority
        
        # Size limit for storing file content (1MB)
        self._content_size_limit = 1024 * 1024
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given file handle object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for file-like objects with read/write methods
        - Check for specific I/O types (TextIOWrapper, etc.)
        - Check for in-memory I/O objects (StringIO, BytesIO)
        - Check for temporary file objects
        - Check for standard streams
        - Check for compressed file objects
        """
        try:
            # Standard I/O types
            if isinstance(obj, (io.TextIOWrapper, io.BufferedReader, io.BufferedWriter, 
                              io.BufferedRandom, io.RawIOBase, io.IOBase)):
                return True
            
            # In-memory I/O
            if isinstance(obj, (io.StringIO, io.BytesIO)):
                return True
            
            # Temporary files
            if hasattr(tempfile, 'TemporaryFile') and isinstance(obj, type(tempfile.TemporaryFile())):
                return True
            if isinstance(obj, tempfile._TemporaryFileWrapper):
                return True
            if hasattr(tempfile, 'NamedTemporaryFile'):
                try:
                    # NamedTemporaryFile creates different types on different platforms
                    temp_file = tempfile.NamedTemporaryFile()
                    temp_file.close()
                    if type(obj) == type(temp_file):
                        return True
                except Exception:
                    pass
            
            # Standard streams
            if obj in (sys.stdin, sys.stdout, sys.stderr):
                return True
            
            # Compressed files
            if hasattr(gzip, 'GzipFile') and isinstance(obj, gzip.GzipFile):
                return True
            if hasattr(bz2, 'BZ2File') and isinstance(obj, bz2.BZ2File):
                return True
            if hasattr(lzma, 'LZMAFile') and isinstance(obj, lzma.LZMAFile):
                return True
            
            # Generic file-like object detection
            # Must have both read-like and file-like characteristics
            has_read = hasattr(obj, 'read')
            has_write = hasattr(obj, 'write')
            has_close = hasattr(obj, 'close')
            has_seek = hasattr(obj, 'seek')
            has_tell = hasattr(obj, 'tell')
            
            # File-like objects should have several of these methods
            file_like_methods = sum([has_read, has_write, has_close, has_seek, has_tell])
            
            if file_like_methods >= 3:  # At least 3 file-like methods
                # But exclude common non-file objects that happen to have these methods
                obj_type_name = type(obj).__name__
                excluded_types = {
                    'dict', 'list', 'tuple', 'set', 'frozenset', 'str', 'bytes',
                    'int', 'float', 'bool', 'NoneType'
                }
                if obj_type_name not in excluded_types:
                    return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a file handle object to a dictionary representation.
        
        Args:
            obj: File handle object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the object
            
        SERIALIZATION PROCESS:
        1. Determine file object type and characteristics
        2. Extract metadata (name, mode, position, encoding)
        3. Store content for small in-memory files
        4. Store file path and metadata for regular files
        5. Handle special cases (temp files, streams, compressed files)
        """
        # Base serialization data
        data = {
            "file_type": self._get_file_type(obj),
            "file_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "serialization_strategy": None,  # Will be determined below
            "recreation_possible": False,
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        file_type = data["file_type"]
        
        if file_type == "regular_file":
            data.update(self._serialize_regular_file(obj))
            data["serialization_strategy"] = "file_path_reopen"
            
        elif file_type == "string_io":
            data.update(self._serialize_string_io(obj))
            data["serialization_strategy"] = "content_recreation"
            
        elif file_type == "bytes_io":
            data.update(self._serialize_bytes_io(obj))
            data["serialization_strategy"] = "content_recreation"
            
        elif file_type == "temporary_file":
            data.update(self._serialize_temporary_file(obj))
            data["serialization_strategy"] = "content_recreation"
            
        elif file_type == "standard_stream":
            data.update(self._serialize_standard_stream(obj))
            data["serialization_strategy"] = "standard_stream_reference"
            
        elif file_type == "compressed_file":
            data.update(self._serialize_compressed_file(obj))
            data["serialization_strategy"] = "compressed_file_reopen"
            
        elif file_type == "network_file":
            data.update(self._serialize_network_file(obj))
            data["serialization_strategy"] = "network_placeholder"
            
        else:
            # Unknown file type
            data.update(self._serialize_unknown_file(obj))
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a file handle object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized file data
            
        Returns:
            Recreated file object (with limitations noted in documentation)
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Restore file with metadata and content
        4. Handle errors gracefully with placeholders
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        file_type = data.get("file_type", "unknown")
        
        try:
            if strategy == "file_path_reopen":
                return self._deserialize_regular_file(data)
            
            elif strategy == "content_recreation":
                if file_type == "string_io":
                    return self._deserialize_string_io(data)
                elif file_type == "bytes_io":
                    return self._deserialize_bytes_io(data)
                elif file_type == "temporary_file":
                    return self._deserialize_temporary_file(data)
                else:
                    raise ValueError(f"Unknown content recreation type: {file_type}")
            
            elif strategy == "standard_stream_reference":
                return self._deserialize_standard_stream(data)
            
            elif strategy == "compressed_file_reopen":
                return self._deserialize_compressed_file(data)
            
            elif strategy == "network_placeholder":
                return self._deserialize_network_file(data)
            
            elif strategy == "fallback_placeholder":
                return self._deserialize_unknown_file(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a placeholder
            return self._create_error_placeholder(file_type, str(e))
    
    # ========================================================================
    # FILE TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_file_type(self, obj: Any) -> str:
        """
        Determine the specific type of file object.
        
        Args:
            obj: File object to analyze
            
        Returns:
            String identifying the file type
        """
        # Standard streams
        if obj in (sys.stdin, sys.stdout, sys.stderr):
            return "standard_stream"
        
        # In-memory I/O
        if isinstance(obj, io.StringIO):
            return "string_io"
        if isinstance(obj, io.BytesIO):
            return "bytes_io"
        
        # Temporary files
        if isinstance(obj, tempfile._TemporaryFileWrapper):
            return "temporary_file"
        if hasattr(tempfile, 'TemporaryFile'):
            try:
                temp_file = tempfile.TemporaryFile()
                if type(obj) == type(temp_file):
                    temp_file.close()
                    return "temporary_file"
                temp_file.close()
            except Exception:
                pass
        
        # Compressed files
        if hasattr(gzip, 'GzipFile') and isinstance(obj, gzip.GzipFile):
            return "compressed_file"
        if hasattr(bz2, 'BZ2File') and isinstance(obj, bz2.BZ2File):
            return "compressed_file"
        if hasattr(lzma, 'LZMAFile') and isinstance(obj, lzma.LZMAFile):
            return "compressed_file"
        
        # Check if it has a name attribute (regular files usually do)
        if hasattr(obj, 'name') and hasattr(obj, 'mode'):
            name = getattr(obj, 'name', None)
            if isinstance(name, (str, Path)) and name not in ('<stdin>', '<stdout>', '<stderr>'):
                # Check if it might be a network file
                if isinstance(name, str) and ('://' in name or name.startswith('<') or name.startswith('[')):
                    return "network_file"
                else:
                    return "regular_file"
        
        # Network or special files
        if hasattr(obj, 'read') and hasattr(obj, 'name'):
            name = getattr(obj, 'name', '')
            if isinstance(name, str) and ('://' in name or 'socket' in name.lower()):
                return "network_file"
        
        # Default to unknown
        return "unknown_file"
    
    # ========================================================================
    # REGULAR FILE SERIALIZATION
    # ========================================================================
    
    def _serialize_regular_file(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize regular file objects.
        
        Store file path, mode, position, and other metadata for recreation.
        """
        result = {
            "file_path": None,
            "file_mode": None,
            "file_position": None,
            "file_encoding": None,
            "file_newline": None,
            "file_buffering": None,
            "file_errors": None,
            "file_exists": False,
            "store_content": False,
            "file_content": None
        }
        
        try:
            # Get file metadata
            result["file_path"] = getattr(obj, 'name', None)
            result["file_mode"] = getattr(obj, 'mode', 'r')
            result["file_encoding"] = getattr(obj, 'encoding', None)
            result["file_newline"] = getattr(obj, 'newlines', None)
            result["file_errors"] = getattr(obj, 'errors', None)
            
            # Get current position
            try:
                result["file_position"] = obj.tell()
            except (OSError, io.UnsupportedOperation):
                result["file_position"] = None
            
            # Check if file exists
            if result["file_path"] and isinstance(result["file_path"], (str, Path)):
                try:
                    result["file_exists"] = os.path.exists(result["file_path"])
                except Exception:
                    result["file_exists"] = False
            
            # For small files, consider storing content as backup
            if result["file_exists"] and result["file_path"]:
                try:
                    file_size = os.path.getsize(result["file_path"])
                    if file_size <= self._content_size_limit:
                        # Store content as backup
                        original_position = result["file_position"]
                        obj.seek(0)
                        
                        if 'b' in result["file_mode"]:
                            content = obj.read()
                            if isinstance(content, bytes):
                                result["file_content"] = content
                                result["store_content"] = True
                        else:
                            content = obj.read()
                            if isinstance(content, str):
                                result["file_content"] = content
                                result["store_content"] = True
                        
                        # Restore original position
                        if original_position is not None:
                            obj.seek(original_position)
                            
                except Exception as e:
                    result["note"] = f"Could not store file content: {e}"
            
        except Exception as e:
            result["note"] = f"Error serializing regular file: {e}"
        
        result["recreation_possible"] = bool(result["file_path"] and 
                                           (result["file_exists"] or result["store_content"]))
        
        return result
    
    def _deserialize_regular_file(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize regular file objects by reopening the file.
        """
        file_path = data.get("file_path")
        file_mode = data.get("file_mode", "r")
        file_position = data.get("file_position")
        file_encoding = data.get("file_encoding")
        file_errors = data.get("file_errors")
        store_content = data.get("store_content", False)
        file_content = data.get("file_content")
        
        if not file_path:
            raise ValueError("No file path available for regular file recreation")
        
        try:
            # Check if original file still exists
            if os.path.exists(file_path):
                # Open the original file
                open_kwargs = {}
                if file_encoding:
                    open_kwargs['encoding'] = file_encoding
                if file_errors:
                    open_kwargs['errors'] = file_errors
                
                file_obj = open(file_path, file_mode, **open_kwargs)
                
                # Restore position if available
                if file_position is not None:
                    try:
                        file_obj.seek(file_position)
                    except (OSError, io.UnsupportedOperation):
                        pass  # Position restoration failed, but file is open
                
                return file_obj
                
            elif store_content and file_content is not None:
                # Original file doesn't exist, but we have content - create temporary file
                if 'b' in file_mode:
                    # Binary mode
                    temp_file = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
                    temp_file.write(file_content)
                else:
                    # Text mode
                    open_kwargs = {}
                    if file_encoding:
                        open_kwargs['encoding'] = file_encoding
                    if file_errors:
                        open_kwargs['errors'] = file_errors
                    
                    temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, **open_kwargs)
                    temp_file.write(file_content)
                
                # Restore position
                if file_position is not None:
                    try:
                        temp_file.seek(file_position)
                    except (OSError, io.UnsupportedOperation):
                        pass
                
                return temp_file
                
            else:
                raise FileNotFoundError(f"File {file_path} no longer exists and no content backup available")
                
        except Exception as e:
            raise ValueError(f"Could not recreate regular file {file_path}: {e}")
    
    # ========================================================================
    # STRING I/O SERIALIZATION
    # ========================================================================
    
    def _serialize_string_io(self, obj: io.StringIO) -> Dict[str, Any]:
        """
        Serialize StringIO objects by storing their content and position.
        """
        result = {
            "string_content": None,
            "string_position": None,
            "initial_value": None
        }
        
        try:
            # Get current position
            result["string_position"] = obj.tell()
            
            # Get full content
            original_position = result["string_position"]
            obj.seek(0)
            result["string_content"] = obj.read()
            obj.seek(original_position)  # Restore position
            
        except Exception as e:
            result["note"] = f"Error serializing StringIO: {e}"
        
        result["recreation_possible"] = result["string_content"] is not None
        
        return result
    
    def _deserialize_string_io(self, data: Dict[str, Any]) -> io.StringIO:
        """
        Deserialize StringIO objects by recreating with stored content.
        """
        string_content = data.get("string_content", "")
        string_position = data.get("string_position", 0)
        
        # Create new StringIO with content
        string_io = io.StringIO(string_content)
        
        # Restore position
        if string_position is not None:
            try:
                string_io.seek(string_position)
            except (OSError, io.UnsupportedOperation):
                pass
        
        return string_io
    
    # ========================================================================
    # BYTES I/O SERIALIZATION
    # ========================================================================
    
    def _serialize_bytes_io(self, obj: io.BytesIO) -> Dict[str, Any]:
        """
        Serialize BytesIO objects by storing their content and position.
        """
        result = {
            "bytes_content": None,
            "bytes_position": None
        }
        
        try:
            # Get current position
            result["bytes_position"] = obj.tell()
            
            # Get full content
            original_position = result["bytes_position"]
            obj.seek(0)
            result["bytes_content"] = obj.read()
            obj.seek(original_position)  # Restore position
            
        except Exception as e:
            result["note"] = f"Error serializing BytesIO: {e}"
        
        result["recreation_possible"] = result["bytes_content"] is not None
        
        return result
    
    def _deserialize_bytes_io(self, data: Dict[str, Any]) -> io.BytesIO:
        """
        Deserialize BytesIO objects by recreating with stored content.
        """
        bytes_content = data.get("bytes_content", b"")
        bytes_position = data.get("bytes_position", 0)
        
        # Create new BytesIO with content
        bytes_io = io.BytesIO(bytes_content)
        
        # Restore position
        if bytes_position is not None:
            try:
                bytes_io.seek(bytes_position)
            except (OSError, io.UnsupportedOperation):
                pass
        
        return bytes_io
    
    # ========================================================================
    # TEMPORARY FILE SERIALIZATION
    # ========================================================================
    
    def _serialize_temporary_file(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize temporary file objects by storing their content.
        """
        result = {
            "temp_content": None,
            "temp_position": None,
            "temp_mode": None,
            "temp_encoding": None,
            "temp_name": None
        }
        
        try:
            # Get metadata
            result["temp_mode"] = getattr(obj, 'mode', 'w+b')
            result["temp_encoding"] = getattr(obj, 'encoding', None)
            result["temp_name"] = getattr(obj, 'name', None)
            
            # Get current position
            try:
                result["temp_position"] = obj.tell()
            except (OSError, io.UnsupportedOperation):
                result["temp_position"] = None
            
            # Store content
            if result["temp_position"] is not None:
                original_position = result["temp_position"]
                obj.seek(0)
                
                if 'b' in result["temp_mode"]:
                    result["temp_content"] = obj.read()
                else:
                    result["temp_content"] = obj.read()
                
                obj.seek(original_position)  # Restore position
            
        except Exception as e:
            result["note"] = f"Error serializing temporary file: {e}"
        
        result["recreation_possible"] = result["temp_content"] is not None
        
        return result
    
    def _deserialize_temporary_file(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize temporary file objects by creating new temp file with content.
        """
        temp_content = data.get("temp_content")
        temp_position = data.get("temp_position", 0)
        temp_mode = data.get("temp_mode", "w+b")
        temp_encoding = data.get("temp_encoding")
        
        if temp_content is None:
            temp_content = b"" if 'b' in temp_mode else ""
        
        try:
            # Create new temporary file
            if 'b' in temp_mode:
                temp_file = tempfile.NamedTemporaryFile(mode=temp_mode, delete=False)
                temp_file.write(temp_content)
            else:
                kwargs = {}
                if temp_encoding:
                    kwargs['encoding'] = temp_encoding
                temp_file = tempfile.NamedTemporaryFile(mode=temp_mode, delete=False, **kwargs)
                temp_file.write(temp_content)
            
            # Restore position
            if temp_position is not None:
                try:
                    temp_file.seek(temp_position)
                except (OSError, io.UnsupportedOperation):
                    pass
            
            return temp_file
            
        except Exception as e:
            raise ValueError(f"Could not recreate temporary file: {e}")
    
    # ========================================================================
    # STANDARD STREAM SERIALIZATION
    # ========================================================================
    
    def _serialize_standard_stream(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize standard stream objects (stdin, stdout, stderr).
        """
        result = {
            "stream_name": None,
            "stream_encoding": None,
            "stream_errors": None
        }
        
        if obj is sys.stdin:
            result["stream_name"] = "stdin"
        elif obj is sys.stdout:
            result["stream_name"] = "stdout"
        elif obj is sys.stderr:
            result["stream_name"] = "stderr"
        else:
            result["stream_name"] = str(obj)
        
        result["stream_encoding"] = getattr(obj, 'encoding', None)
        result["stream_errors"] = getattr(obj, 'errors', None)
        result["recreation_possible"] = result["stream_name"] in ("stdin", "stdout", "stderr")
        
        return result
    
    def _deserialize_standard_stream(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize standard stream objects by returning the current streams.
        """
        stream_name = data.get("stream_name")
        
        if stream_name == "stdin":
            return sys.stdin
        elif stream_name == "stdout":
            return sys.stdout
        elif stream_name == "stderr":
            return sys.stderr
        else:
            # Unknown stream - return stdout as fallback
            return sys.stdout
    
    # ========================================================================
    # COMPRESSED FILE SERIALIZATION
    # ========================================================================
    
    def _serialize_compressed_file(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize compressed file objects (gzip, bz2, lzma).
        """
        result = {
            "compression_type": None,
            "file_name": None,
            "file_mode": None,
            "file_position": None
        }
        
        # Determine compression type
        if hasattr(gzip, 'GzipFile') and isinstance(obj, gzip.GzipFile):
            result["compression_type"] = "gzip"
        elif hasattr(bz2, 'BZ2File') and isinstance(obj, bz2.BZ2File):
            result["compression_type"] = "bz2"
        elif hasattr(lzma, 'LZMAFile') and isinstance(obj, lzma.LZMAFile):
            result["compression_type"] = "lzma"
        
        # Get metadata
        result["file_name"] = getattr(obj, 'name', None)
        result["file_mode"] = getattr(obj, 'mode', 'rb')
        
        try:
            result["file_position"] = obj.tell()
        except (OSError, io.UnsupportedOperation):
            result["file_position"] = None
        
        result["recreation_possible"] = bool(result["file_name"] and 
                                           result["compression_type"] and
                                           os.path.exists(result["file_name"]) if result["file_name"] else False)
        
        return result
    
    def _deserialize_compressed_file(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize compressed file objects by reopening them.
        """
        compression_type = data.get("compression_type")
        file_name = data.get("file_name")
        file_mode = data.get("file_mode", "rb")
        file_position = data.get("file_position")
        
        if not compression_type or not file_name:
            raise ValueError("Missing compression type or file name")
        
        try:
            # Open compressed file
            if compression_type == "gzip":
                compressed_file = gzip.open(file_name, file_mode)
            elif compression_type == "bz2":
                compressed_file = bz2.open(file_name, file_mode)
            elif compression_type == "lzma":
                compressed_file = lzma.open(file_name, file_mode)
            else:
                raise ValueError(f"Unknown compression type: {compression_type}")
            
            # Restore position
            if file_position is not None:
                try:
                    compressed_file.seek(file_position)
                except (OSError, io.UnsupportedOperation):
                    pass
            
            return compressed_file
            
        except Exception as e:
            raise ValueError(f"Could not recreate compressed file: {e}")
    
    # ========================================================================
    # NETWORK FILE SERIALIZATION
    # ========================================================================
    
    def _serialize_network_file(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize network file objects (limited capability).
        """
        result = {
            "network_name": getattr(obj, 'name', None),
            "network_mode": getattr(obj, 'mode', None),
            "object_repr": repr(obj)[:200]
        }
        
        result["recreation_possible"] = False
        result["limitation"] = "Network file objects cannot be recreated"
        
        return result
    
    def _deserialize_network_file(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize network file objects (placeholder only).
        """
        network_name = data.get("network_name", "unknown")
        
        # Return a placeholder that explains the limitation
        class NetworkFilePlaceholder:
            def __init__(self, name):
                self.name = name
                self.closed = True
            
            def read(self, *args):
                raise RuntimeError(f"Network file '{self.name}' cannot be recreated after serialization")
            
            def write(self, *args):
                raise RuntimeError(f"Network file '{self.name}' cannot be recreated after serialization")
            
            def close(self):
                pass
            
            def __repr__(self):
                return f"<NetworkFilePlaceholder name='{self.name}'>"
        
        return NetworkFilePlaceholder(network_name)
    
    # ========================================================================
    # UNKNOWN FILE SERIALIZATION
    # ========================================================================
    
    def _serialize_unknown_file(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown file types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_type": type(obj).__name__,
            "object_module": getattr(type(obj), '__module__', 'unknown'),
            "has_read": hasattr(obj, 'read'),
            "has_write": hasattr(obj, 'write'),
            "has_close": hasattr(obj, 'close'),
            "has_name": hasattr(obj, 'name'),
            "name": getattr(obj, 'name', None),
            "note": f"Unknown file type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_file(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown file types with placeholder.
        """
        object_type = data.get("object_type", "unknown")
        object_name = data.get("name", "unknown")
        
        class UnknownFilePlaceholder:
            def __init__(self, file_type, name):
                self.file_type = file_type
                self.name = name
                self.closed = True
            
            def read(self, *args):
                raise RuntimeError(f"Unknown file type '{self.file_type}' cannot be recreated")
            
            def write(self, *args):
                raise RuntimeError(f"Unknown file type '{self.file_type}' cannot be recreated")
            
            def close(self):
                pass
            
            def __repr__(self):
                return f"<UnknownFilePlaceholder type='{self.file_type}' name='{self.name}'>"
        
        return UnknownFilePlaceholder(object_type, object_name)
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _create_error_placeholder(self, file_type: str, error_message: str) -> Any:
        """
        Create a placeholder file object for objects that failed to deserialize.
        """
        class ErrorFilePlaceholder:
            def __init__(self, file_type, error):
                self.file_type = file_type
                self.error = error
                self.closed = True
            
            def read(self, *args):
                raise RuntimeError(f"File object ({self.file_type}) deserialization failed: {self.error}")
            
            def write(self, *args):
                raise RuntimeError(f"File object ({self.file_type}) deserialization failed: {self.error}")
            
            def close(self):
                pass
            
            def __repr__(self):
                return f"<ErrorFilePlaceholder type='{self.file_type}' error='{self.error}'>"
        
        return ErrorFilePlaceholder(file_type, error_message)


# Create a singleton instance for auto-registration
file_handles_handler = FileHandlesHandler()