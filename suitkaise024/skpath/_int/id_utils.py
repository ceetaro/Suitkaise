"""
SKPath ID Utilities

Encoding and decoding utilities for path IDs.
- ID (property): Base64url encoded path (reversible)
- Hash: MD5 hash for __hash__ (not reversible, fixed length)
"""

import base64
import hashlib
import threading

# Thread-safe lock for any shared state
_id_lock = threading.RLock()


def normalize_separators(path_str: str) -> str:
    """
    Normalize path separators to forward slashes for cross-platform compatibility.
    
    Args:
        path_str: Path string with any separator style
        
    Returns:
        Path string with all separators as forward slashes
    """
    return path_str.replace("\\", "/")


def to_os_separators(path_str: str) -> str:
    """
    Convert normalized path separators back to OS-native separators.
    
    Args:
        path_str: Path string with forward slashes
        
    Returns:
        Path string with OS-native separators
    """
    import os
    if os.sep == "\\":
        return path_str.replace("/", "\\")
    return path_str


def encode_path_id(path_str: str) -> str:
    """
    Encode a path string to a reversible base64url ID.
    
    Uses base64url encoding (URL-safe, no padding) for the normalized path.
    The path is normalized to forward slashes before encoding.
    
    Args:
        path_str: Path string to encode
        
    Returns:
        Base64url encoded string (reversible)
    """
    normalized = normalize_separators(path_str)
    encoded = base64.urlsafe_b64encode(normalized.encode("utf-8"))
    # Remove padding for cleaner IDs
    return encoded.decode("utf-8").rstrip("=")


def decode_path_id(encoded_id: str) -> str | None:
    """
    Decode a base64url encoded path ID back to a path string.
    
    Args:
        encoded_id: Base64url encoded ID string
        
    Returns:
        Decoded path string with forward slashes, or None if decoding fails
    """
    try:
        # Add back padding if needed
        padding = 4 - (len(encoded_id) % 4)
        if padding != 4:
            encoded_id += "=" * padding
        
        decoded = base64.urlsafe_b64decode(encoded_id.encode("utf-8"))
        return decoded.decode("utf-8")
    except Exception:
        return None


def is_valid_encoded_id(s: str) -> bool:
    """
    Check if a string looks like a valid base64url encoded ID.
    
    This is a heuristic check - it doesn't guarantee the decoded result
    is a valid path, just that the string could be a valid encoding.
    
    Args:
        s: String to check
        
    Returns:
        True if string appears to be base64url encoded
    """
    # Base64url uses A-Z, a-z, 0-9, -, _
    # Must not contain path separators or common path characters
    if not s:
        return False
    
    # If it contains path separators, it's likely a path, not an ID
    if "/" in s or "\\" in s:
        return False
    
    # If it contains spaces or common file extensions, likely a path
    if " " in s or s.startswith("."):
        return False
    
    # Check if all characters are valid base64url characters
    valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
    return all(c in valid_chars for c in s)


def hash_path_md5(path_str: str) -> int:
    """
    Generate an integer hash from a path string using MD5.
    
    Used for __hash__ to enable SKPath in sets and as dict keys.
    The path is normalized to forward slashes before hashing.
    
    Args:
        path_str: Path string to hash
        
    Returns:
        Integer hash value
    """
    normalized = normalize_separators(path_str)
    md5_hash = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    # Convert first 16 hex chars to int (64 bits, fits in Python int)
    return int(md5_hash[:16], 16)
