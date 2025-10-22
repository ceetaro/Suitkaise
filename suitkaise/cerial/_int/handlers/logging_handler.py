"""
Handler for logging.Logger objects.

Loggers are configured with handlers, formatters, levels, and filters.
We serialize the configuration and recreate the logger with the same setup.
"""

import logging
from typing import Any, Dict
from .base_class import Handler


class LoggingSerializationError(Exception):
    """Raised when logging object serialization fails."""
    pass


class LoggerHandler(Handler):
    """
    Serializes logging.Logger objects by capturing their configuration.
    
    Strategy:
    - Extract logger name, level, handlers, filters, propagate setting
    - Recursively serialize handler objects (StreamHandler, FileHandler, etc.)
    - On reconstruction, get logger by name and reapply configuration
    
    Note: Logger instances are singletons per name - logging.getLogger(name)
    always returns the same instance. We leverage this.
    """
    
    type_name = "logger"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a Logger."""
        return isinstance(obj, logging.Logger)
    
    def extract_state(self, obj: logging.Logger) -> Dict[str, Any]:
        """
        Extract logger configuration.
        
        What we capture:
        - name: Logger name (e.g., "__main__", "myapp.module")
        - level: Logging level (DEBUG=10, INFO=20, etc.)
        - handlers: List of handler objects (central serializer will recurse)
        - filters: List of filter objects
        - propagate: Whether to propagate to parent loggers
        - disabled: Whether logger is disabled
        """
        return {
            "name": obj.name,
            "level": obj.level,
            "handlers": list(obj.handlers),  # Will be recursively serialized
            "filters": list(obj.filters),    # Will be recursively serialized
            "propagate": obj.propagate,
            "disabled": obj.disabled,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> logging.Logger:
        """
        Reconstruct logger from configuration.
        
        Process:
        1. Get logger by name (creates or returns existing singleton)
        2. Clear existing handlers (in case logger already existed)
        3. Set level and other properties
        4. Add handlers back (already deserialized by central serializer)
        """
        # Get logger instance (singleton per name)
        logger = logging.getLogger(state["name"])
        
        # Clear existing handlers to start fresh
        logger.handlers = []
        
        # Restore configuration
        logger.setLevel(state["level"])
        logger.propagate = state["propagate"]
        logger.disabled = state["disabled"]
        
        # Add handlers (already reconstructed objects)
        for handler in state["handlers"]:
            logger.addHandler(handler)
        
        # Add filters (already reconstructed objects)
        for filter_obj in state["filters"]:
            logger.addFilter(filter_obj)
        
        return logger


class StreamHandlerHandler(Handler):
    """
    Serializes logging.StreamHandler objects.
    
    StreamHandlers write logs to a stream (usually sys.stdout or sys.stderr).
    We capture the formatter and level, but not the stream itself (it's 
    usually a system stream that exists in the target process).
    """
    
    type_name = "stream_handler"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a StreamHandler (but not subclasses like FileHandler)."""
        return type(obj) == logging.StreamHandler
    
    def extract_state(self, obj: logging.StreamHandler) -> Dict[str, Any]:
        """
        Extract StreamHandler configuration.
        
        What we capture:
        - level: Handler's logging level
        - formatter: Formatter object (will be recursively serialized)
        - stream: We don't serialize the stream itself - use default on reconstruct
        """
        return {
            "level": obj.level,
            "formatter": obj.formatter,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> logging.StreamHandler:
        """
        Reconstruct StreamHandler.
        
        Note: We use default stream (sys.stderr) since we can't serialize
        the stream itself. Most use cases just use the default anyway.
        """
        handler = logging.StreamHandler()  # Uses sys.stderr by default
        handler.setLevel(state["level"])
        
        if state["formatter"]:
            handler.setFormatter(state["formatter"])
        
        return handler


class FileHandlerHandler(Handler):
    """
    Serializes logging.FileHandler objects.
    
    FileHandlers write logs to a file. We capture the filename and mode.
    """
    
    type_name = "file_handler"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a FileHandler."""
        return isinstance(obj, logging.FileHandler)
    
    def extract_state(self, obj: logging.FileHandler) -> Dict[str, Any]:
        """
        Extract FileHandler configuration.
        
        What we capture:
        - baseFilename: Path to log file
        - mode: File open mode ('a' for append, 'w' for write)
        - encoding: File encoding
        - level: Handler's logging level
        - formatter: Formatter object
        """
        return {
            "filename": obj.baseFilename,
            "mode": obj.mode,
            "encoding": obj.encoding,
            "level": obj.level,
            "formatter": obj.formatter,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> logging.FileHandler:
        """
        Reconstruct FileHandler.
        
        Opens the log file with the same path and mode.
        """
        handler = logging.FileHandler(
            state["filename"],
            mode=state["mode"],
            encoding=state["encoding"]
        )
        handler.setLevel(state["level"])
        
        if state["formatter"]:
            handler.setFormatter(state["formatter"])
        
        return handler


class FormatterHandler(Handler):
    """
    Serializes logging.Formatter objects.
    
    Formatters define the structure of log messages.
    """
    
    type_name = "formatter"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a Formatter."""
        return isinstance(obj, logging.Formatter)
    
    def extract_state(self, obj: logging.Formatter) -> Dict[str, Any]:
        """
        Extract Formatter configuration.
        
        What we capture:
        - _fmt: Format string (e.g., '%(asctime)s - %(name)s - %(levelname)s')
        - datefmt: Date format string
        - _style: Format style ('%', '{', or '$')
        """
        return {
            "fmt": obj._fmt,
            "datefmt": obj.datefmt,
            "style": obj._style._fmt if hasattr(obj._style, '_fmt') else '%',
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> logging.Formatter:
        """
        Reconstruct Formatter with same format strings.
        """
        return logging.Formatter(
            fmt=state["fmt"],
            datefmt=state["datefmt"],
            style=state["style"]
        )

