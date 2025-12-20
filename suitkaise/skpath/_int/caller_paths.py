# Get the actual suitkaise module base path for robust checking
_SUITKAISE_BASE_PATH = # TODO

def _get_non_sk_caller_file_path() -> Optional[Path]:
    """
    Get the path of the file that called this function, skipping all suitkaise module files.
    
    This function walks up the call stack until it finds a file that's not part of the
    suitkaise package, returning the first non-suitkaise file it encounters.
    
    Returns:
        Path to the first non-suitkaise calling file, or None if not found
    """
    frame = inspect.currentframe()
    try:
        # Start from the caller's frame
        if frame is None:
            return None
        caller_frame = frame.f_back
        
        # Keep going up the stack until we find a frame that's not from suitkaise
        while caller_frame is not None:
            caller_path = caller_frame.f_globals.get('__file__')
            
            if caller_path:
                try:
                    normalized_caller_path = Path(caller_path).resolve().absolute()
                except (OSError, ValueError):
                    # If we can't normalize this path, skip it
                    caller_frame = caller_frame.f_back
                    continue
                
                # Check if this file is part of the suitkaise package
                if not _is_suitkaise_module(normalized_caller_path):
                    return normalized_caller_path
            
            caller_frame = caller_frame.f_back
        
        # Fallback if we can't find a non-suitkaise file
        return None
    finally:
        del frame


def _is_suitkaise_module(file_path: Path) -> bool:
    """
    Robustly check if a file path belongs to the suitkaise library.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if the file is part of suitkaise library
    """
    try:
        # Resolve both paths to handle symlinks and relative paths
        file_resolved = file_path.resolve()
        suitkaise_resolved = _SUITKAISE_BASE_PATH.resolve()
        
        # Check if file is under suitkaise directory
        try:
            file_resolved.relative_to(suitkaise_resolved)
            return True
        except ValueError:
            # Not under suitkaise directory
            pass
        
        # Additional check: look at common installation patterns
        file_str = str(file_resolved)
        if any(part in file_str for part in ['/suitkaise/', '\\suitkaise\\', 'site-packages/suitkaise']):
            return True
            
        return False
        
    except (OSError, ValueError):
        # If we can't resolve paths, fall back to simple string check
        return 'suitkaise' in str(file_path)


def _get_caller_file_path(frames_to_skip: int = 2) -> Path:
    """
    Get the direct file path of the module that called this function.

    Mainly for testing suitkaise itself.
    
    Args:
        frames_to_skip: Number of frames to skip in the call stack
        
    Returns:
        Path to the calling file
    """
    frame = inspect.currentframe()
    try:
        # Skip the specified number of frames to get the caller's frame
        for _ in range(frames_to_skip):
            if frame is not None:
                frame = frame.f_back
        
        if frame is None:
            raise RuntimeError("No caller frame found")
        
        # Get the file path from the caller's frame
        caller_path = frame.f_globals.get('__file__')
        
        if not caller_path:
            raise RuntimeError("Caller frame does not have a file path")
        
        # Normalize and return the path
        return Path(caller_path).resolve().absolute()
    finally:
        del frame