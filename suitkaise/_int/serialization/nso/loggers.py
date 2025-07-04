"""
Logger Objects Serialization Handler

This module provides serialization support for logging.Logger objects and
related logging components that cannot be pickled due to their complex
internal state, file handles, and formatter objects.

SUPPORTED OBJECTS:
==================

1. LOGGER OBJECTS:
   - logging.Logger instances (named and root loggers)
   - Child loggers with hierarchical names
   - Loggers with custom levels and effective levels

2. LOGGING HANDLERS:
   - StreamHandler (stdout, stderr)
   - FileHandler (file-based logging)
   - RotatingFileHandler (log rotation)
   - TimedRotatingFileHandler (time-based rotation)
   - SocketHandler (network logging)
   - Custom handler subclasses

3. LOGGING FORMATTERS:
   - logging.Formatter objects
   - Custom formatter subclasses
   - Format strings and date formats

4. LOGGING FILTERS:
   - logging.Filter objects
   - Custom filter functions and classes

SERIALIZATION STRATEGY:
======================

Logger serialization is challenging because loggers contain:
- File handles and streams (non-serializable)
- Handler objects with complex state
- Formatter objects with functions
- Filter objects that may contain lambdas
- Parent-child relationships in logger hierarchy

Our approach:
1. **Store logger configuration** (name, level, handlers, formatters)
2. **Recreate logger hierarchy** with proper parent-child relationships
3. **Restore handler configurations** with recreated file handles
4. **Preserve formatter settings** and custom format strings
5. **Handle filter objects** with graceful degradation
6. **Maintain logger state** (disabled, propagate flags)

LIMITATIONS:
============
- Custom handler classes may not be recreatable
- Filter functions/lambdas cannot be serialized
- Open file handles are closed and reopened
- Network connections in handlers are not preserved
- Custom logging classes may lose some functionality
- Handler locks and thread safety state is reset

"""

import logging
import sys
import os
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class LoggersHandler(_NSO_Handler):
    """Handler for logging.Logger objects and related logging components."""
    
    def __init__(self):
        """Initialize the loggers handler."""
        super().__init__()
        self._handler_name = "LoggersHandler"
        self._priority = 15  # High priority since loggers are very common
        
        # Standard logging levels
        self._logging_levels = {
            'CRITICAL': logging.CRITICAL,
            'FATAL': logging.FATAL,
            'ERROR': logging.ERROR,
            'WARNING': logging.WARNING,
            'WARN': logging.WARN,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
            'NOTSET': logging.NOTSET
        }
        
        # Reverse mapping for serialization
        self._level_names = {v: k for k, v in self._logging_levels.items()}
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given logging object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for logging.Logger objects
        - Check for logging handler objects
        - Check for logging formatter objects
        - Check for logging filter objects
        """
        try:
            # Direct logger check
            if isinstance(obj, logging.Logger):
                return True
            
            # Logging handler types
            if isinstance(obj, logging.Handler):
                return True
            
            # Logging formatter
            if isinstance(obj, logging.Formatter):
                return True
            
            # Logging filter
            if isinstance(obj, logging.Filter):
                return True
            
            # Check by type name and module for compatibility
            obj_type_name = type(obj).__name__
            obj_module = getattr(type(obj), '__module__', '')
            
            # Logger-related type names
            logging_types = {
                'Logger', 'RootLogger', 'PlaceHolder',
                'StreamHandler', 'FileHandler', 'RotatingFileHandler',
                'TimedRotatingFileHandler', 'SocketHandler', 'DatagramHandler',
                'SysLogHandler', 'NTEventLogHandler', 'SMTPHandler',
                'MemoryHandler', 'HTTPHandler', 'WatchedFileHandler',
                'Formatter', 'Filter'
            }
            
            if obj_type_name in logging_types and 'logging' in obj_module:
                return True
            
            # Check for custom logging objects by duck typing
            if hasattr(obj, 'handlers') and hasattr(obj, 'level') and hasattr(obj, 'name'):
                # Looks like a logger
                return True
            
            if hasattr(obj, 'emit') and hasattr(obj, 'format') and hasattr(obj, 'level'):
                # Looks like a logging handler
                return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a logging object to a dictionary representation.
        
        Args:
            obj: Logging object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the logging object
            
        SERIALIZATION PROCESS:
        1. Determine logging object type
        2. Extract configuration and state
        3. Handle nested objects (handlers, formatters, filters)
        4. Store hierarchy information for loggers
        5. Handle file paths and stream references
        """
        # Base serialization data
        data = {
            "logging_type": self._get_logging_type(obj),
            "object_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "serialization_strategy": None,
            "recreation_possible": False,
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        logging_type = data["logging_type"]
        
        if logging_type == "logger":
            data.update(self._serialize_logger(obj))
            data["serialization_strategy"] = "logger_recreation"
            
        elif logging_type == "handler":
            data.update(self._serialize_handler(obj))
            data["serialization_strategy"] = "handler_recreation"
            
        elif logging_type == "formatter":
            data.update(self._serialize_formatter(obj))
            data["serialization_strategy"] = "formatter_recreation"
            
        elif logging_type == "filter":
            data.update(self._serialize_filter(obj))
            data["serialization_strategy"] = "filter_recreation"
            
        else:
            # Unknown logging type
            data.update(self._serialize_unknown_logging_object(obj))
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a logging object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized logging data
            
        Returns:
            Recreated logging object
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Restore logging configuration
        4. Rebuild object relationships
        5. Handle errors gracefully with functional placeholders
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        logging_type = data.get("logging_type", "unknown")
        
        try:
            if strategy == "logger_recreation":
                return self._deserialize_logger(data)
            
            elif strategy == "handler_recreation":
                return self._deserialize_handler(data)
            
            elif strategy == "formatter_recreation":
                return self._deserialize_formatter(data)
            
            elif strategy == "filter_recreation":
                return self._deserialize_filter(data)
            
            elif strategy == "fallback_placeholder":
                return self._deserialize_unknown_logging_object(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a functional placeholder
            return self._create_logging_placeholder(logging_type, str(e))
    
    # ========================================================================
    # LOGGING TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_logging_type(self, obj: Any) -> str:
        """
        Determine the specific type of logging object.
        
        Args:
            obj: Logging object to analyze
            
        Returns:
            String identifying the logging object type
        """
        if isinstance(obj, logging.Logger):
            return "logger"
        
        elif isinstance(obj, logging.Handler):
            return "handler"
        
        elif isinstance(obj, logging.Formatter):
            return "formatter"
        
        elif isinstance(obj, logging.Filter):
            return "filter"
        
        else:
            # Check by attributes for custom classes
            if hasattr(obj, 'handlers') and hasattr(obj, 'level') and hasattr(obj, 'name'):
                return "logger"
            elif hasattr(obj, 'emit') and hasattr(obj, 'format'):
                return "handler"
            elif hasattr(obj, 'format') and hasattr(obj, '_fmt'):
                return "formatter"
            elif hasattr(obj, 'filter'):
                return "filter"
            else:
                return "unknown"
    
    # ========================================================================
    # LOGGER SERIALIZATION
    # ========================================================================
    
    def _serialize_logger(self, obj: logging.Logger) -> Dict[str, Any]:
        """
        Serialize logging.Logger objects.
        
        Store logger configuration, handlers, and hierarchy information.
        """
        result = {
            "logger_name": obj.name,
            "logger_level": obj.level,
            "logger_level_name": self._level_names.get(obj.level, str(obj.level)),
            "logger_disabled": obj.disabled,
            "logger_propagate": obj.propagate,
            "logger_handlers": [],
            "logger_filters": [],
            "parent_logger_name": None,
            "is_root_logger": obj is logging.getLogger()
        }
        
        try:
            # Get parent logger information
            if obj.parent and obj.parent.name:
                result["parent_logger_name"] = obj.parent.name
            
            # Serialize handlers
            for handler in obj.handlers:
                try:
                    handler_data = self._serialize_handler(handler)
                    handler_data["handler_class"] = f"{type(handler).__module__}.{type(handler).__name__}"
                    result["logger_handlers"].append(handler_data)
                except Exception as e:
                    # Skip handlers that can't be serialized
                    result["logger_handlers"].append({
                        "handler_error": str(e),
                        "handler_class": f"{type(handler).__module__}.{type(handler).__name__}",
                        "handler_type": "error_placeholder"
                    })
            
            # Serialize filters
            for filter_obj in obj.filters:
                try:
                    filter_data = self._serialize_filter(filter_obj)
                    result["logger_filters"].append(filter_data)
                except Exception as e:
                    # Skip filters that can't be serialized
                    result["logger_filters"].append({
                        "filter_error": str(e),
                        "filter_type": "error_placeholder"
                    })
            
        except Exception as e:
            result["note"] = f"Error serializing logger: {e}"
        
        result["recreation_possible"] = True  # Loggers can usually be recreated
        
        return result
    
    def _deserialize_logger(self, data: Dict[str, Any]) -> logging.Logger:
        """
        Deserialize logging.Logger objects.
        
        Recreate the logger with its configuration, handlers, and filters.
        """
        logger_name = data.get("logger_name", "")
        logger_level = data.get("logger_level", logging.INFO)
        logger_disabled = data.get("logger_disabled", False)
        logger_propagate = data.get("logger_propagate", True)
        logger_handlers = data.get("logger_handlers", [])
        logger_filters = data.get("logger_filters", [])
        is_root_logger = data.get("is_root_logger", False)
        
        try:
            # Get or create the logger
            if is_root_logger:
                logger = logging.getLogger()
            else:
                logger = logging.getLogger(logger_name)
            
            # Set logger properties
            logger.setLevel(logger_level)
            logger.disabled = logger_disabled
            logger.propagate = logger_propagate
            
            # Clear existing handlers to avoid duplicates
            logger.handlers.clear()
            
            # Recreate handlers
            for handler_data in logger_handlers:
                if handler_data.get("handler_type") == "error_placeholder":
                    continue  # Skip error placeholders
                
                try:
                    handler = self._deserialize_handler(handler_data)
                    logger.addHandler(handler)
                except Exception:
                    # Skip handlers that can't be recreated
                    continue
            
            # Clear existing filters
            logger.filters.clear()
            
            # Recreate filters
            for filter_data in logger_filters:
                if filter_data.get("filter_type") == "error_placeholder":
                    continue  # Skip error placeholders
                
                try:
                    filter_obj = self._deserialize_filter(filter_data)
                    logger.addFilter(filter_obj)
                except Exception:
                    # Skip filters that can't be recreated
                    continue
            
            return logger
            
        except Exception as e:
            # If logger recreation fails, create a basic logger
            logger = logging.getLogger(logger_name or "deserialized_logger")
            logger.setLevel(logger_level)
            return logger
    
    # ========================================================================
    # HANDLER SERIALIZATION
    # ========================================================================
    
    def _serialize_handler(self, obj: logging.Handler) -> Dict[str, Any]:
        """
        Serialize logging.Handler objects.
        
        Store handler configuration, formatter, and type-specific settings.
        """
        result = {
            "handler_type": type(obj).__name__,
            "handler_level": obj.level,
            "handler_level_name": self._level_names.get(obj.level, str(obj.level)),
            "handler_formatter": None,
            "handler_filters": [],
            "handler_specific_config": {}
        }
        
        try:
            # Serialize formatter
            if obj.formatter:
                try:
                    result["handler_formatter"] = self._serialize_formatter(obj.formatter)
                except Exception as e:
                    result["handler_formatter"] = {"formatter_error": str(e)}
            
            # Serialize filters
            for filter_obj in obj.filters:
                try:
                    filter_data = self._serialize_filter(filter_obj)
                    result["handler_filters"].append(filter_data)
                except Exception as e:
                    result["handler_filters"].append({"filter_error": str(e)})
            
            # Handler-specific configuration
            if isinstance(obj, logging.StreamHandler):
                result["handler_specific_config"] = self._serialize_stream_handler(obj)
            
            elif isinstance(obj, logging.FileHandler):
                result["handler_specific_config"] = self._serialize_file_handler(obj)
            
            elif hasattr(logging.handlers, 'RotatingFileHandler') and isinstance(obj, logging.handlers.RotatingFileHandler):
                result["handler_specific_config"] = self._serialize_rotating_file_handler(obj)
            
            elif hasattr(logging.handlers, 'TimedRotatingFileHandler') and isinstance(obj, logging.handlers.TimedRotatingFileHandler):
                result["handler_specific_config"] = self._serialize_timed_rotating_file_handler(obj)
            
            else:
                # Generic handler - try to extract common attributes
                result["handler_specific_config"] = self._serialize_generic_handler(obj)
            
        except Exception as e:
            result["note"] = f"Error serializing handler: {e}"
        
        result["recreation_possible"] = True
        
        return result
    
    def _serialize_stream_handler(self, obj: logging.StreamHandler) -> Dict[str, Any]:
        """Serialize StreamHandler specific configuration."""
        config = {}
        
        try:
            # Determine stream type
            if obj.stream is sys.stdout:
                config["stream_type"] = "stdout"
            elif obj.stream is sys.stderr:
                config["stream_type"] = "stderr"
            elif obj.stream is sys.stdin:
                config["stream_type"] = "stdin"
            else:
                config["stream_type"] = "custom"
                config["stream_name"] = getattr(obj.stream, 'name', str(obj.stream))
        
        except Exception as e:
            config["stream_error"] = str(e)
        
        return config
    
    def _serialize_file_handler(self, obj: logging.FileHandler) -> Dict[str, Any]:
        """Serialize FileHandler specific configuration."""
        config = {}
        
        try:
            config["filename"] = obj.baseFilename
            config["mode"] = getattr(obj, 'mode', 'a')
            config["encoding"] = getattr(obj, 'encoding', None)
            config["delay"] = getattr(obj, 'delay', False)
        
        except Exception as e:
            config["file_error"] = str(e)
        
        return config
    
    def _serialize_rotating_file_handler(self, obj) -> Dict[str, Any]:
        """Serialize RotatingFileHandler specific configuration."""
        config = self._serialize_file_handler(obj)
        
        try:
            config["max_bytes"] = getattr(obj, 'maxBytes', 0)
            config["backup_count"] = getattr(obj, 'backupCount', 0)
        
        except Exception as e:
            config["rotating_error"] = str(e)
        
        return config
    
    def _serialize_timed_rotating_file_handler(self, obj) -> Dict[str, Any]:
        """Serialize TimedRotatingFileHandler specific configuration."""
        config = self._serialize_file_handler(obj)
        
        try:
            config["when"] = getattr(obj, 'when', 'h')
            config["interval"] = getattr(obj, 'interval', 1)
            config["backup_count"] = getattr(obj, 'backupCount', 0)
            config["utc"] = getattr(obj, 'utc', False)
        
        except Exception as e:
            config["timed_rotating_error"] = str(e)
        
        return config
    
    def _serialize_generic_handler(self, obj: logging.Handler) -> Dict[str, Any]:
        """Serialize generic handler configuration."""
        config = {}
        
        try:
            # Extract common attributes that might be useful
            for attr_name in ['filename', 'mode', 'encoding', 'stream', 'address', 'facility']:
                if hasattr(obj, attr_name):
                    attr_value = getattr(obj, attr_name)
                    # Only store simple types
                    if isinstance(attr_value, (str, int, float, bool, type(None))):
                        config[attr_name] = attr_value
                    else:
                        config[attr_name] = str(attr_value)
        
        except Exception as e:
            config["generic_error"] = str(e)
        
        return config
    
    def _deserialize_handler(self, data: Dict[str, Any]) -> logging.Handler:
        """
        Deserialize logging.Handler objects.
        
        Recreate the handler with its specific configuration.
        """
        handler_type = data.get("handler_type", "StreamHandler")
        handler_level = data.get("handler_level", logging.INFO)
        handler_formatter = data.get("handler_formatter")
        handler_filters = data.get("handler_filters", [])
        handler_config = data.get("handler_specific_config", {})
        
        try:
            # Create handler based on type
            if handler_type == "StreamHandler":
                handler = self._create_stream_handler(handler_config)
            
            elif handler_type == "FileHandler":
                handler = self._create_file_handler(handler_config)
            
            elif handler_type == "RotatingFileHandler":
                handler = self._create_rotating_file_handler(handler_config)
            
            elif handler_type == "TimedRotatingFileHandler":
                handler = self._create_timed_rotating_file_handler(handler_config)
            
            else:
                # Default to StreamHandler for unknown types
                handler = logging.StreamHandler()
            
            # Set handler properties
            handler.setLevel(handler_level)
            
            # Restore formatter
            if handler_formatter and not handler_formatter.get("formatter_error"):
                try:
                    formatter = self._deserialize_formatter(handler_formatter)
                    handler.setFormatter(formatter)
                except Exception:
                    pass  # Skip formatter if recreation fails
            
            # Restore filters
            for filter_data in handler_filters:
                if not filter_data.get("filter_error"):
                    try:
                        filter_obj = self._deserialize_filter(filter_data)
                        handler.addFilter(filter_obj)
                    except Exception:
                        pass  # Skip filter if recreation fails
            
            return handler
            
        except Exception as e:
            # If handler recreation fails, create a basic StreamHandler
            handler = logging.StreamHandler()
            handler.setLevel(handler_level)
            return handler
    
    def _create_stream_handler(self, config: Dict[str, Any]) -> logging.StreamHandler:
        """Create StreamHandler from configuration."""
        stream_type = config.get("stream_type", "stderr")
        
        if stream_type == "stdout":
            return logging.StreamHandler(sys.stdout)
        elif stream_type == "stdin":
            return logging.StreamHandler(sys.stdin)
        else:  # stderr or custom
            return logging.StreamHandler(sys.stderr)
    
    def _create_file_handler(self, config: Dict[str, Any]) -> logging.FileHandler:
        """Create FileHandler from configuration."""
        filename = config.get("filename", "default.log")
        mode = config.get("mode", "a")
        encoding = config.get("encoding")
        delay = config.get("delay", False)
        
        kwargs = {"mode": mode, "delay": delay}
        if encoding:
            kwargs["encoding"] = encoding
        
        return logging.FileHandler(filename, **kwargs)
    
    def _create_rotating_file_handler(self, config: Dict[str, Any]):
        """Create RotatingFileHandler from configuration."""
        try:
            import logging.handlers
            
            filename = config.get("filename", "default.log")
            mode = config.get("mode", "a")
            max_bytes = config.get("max_bytes", 0)
            backup_count = config.get("backup_count", 0)
            encoding = config.get("encoding")
            
            kwargs = {"mode": mode, "maxBytes": max_bytes, "backupCount": backup_count}
            if encoding:
                kwargs["encoding"] = encoding
            
            return logging.handlers.RotatingFileHandler(filename, **kwargs)
            
        except ImportError:
            # Fall back to regular FileHandler
            return self._create_file_handler(config)
    
    def _create_timed_rotating_file_handler(self, config: Dict[str, Any]):
        """Create TimedRotatingFileHandler from configuration."""
        try:
            import logging.handlers
            
            filename = config.get("filename", "default.log")
            when = config.get("when", "h")
            interval = config.get("interval", 1)
            backup_count = config.get("backup_count", 0)
            encoding = config.get("encoding")
            utc = config.get("utc", False)
            
            kwargs = {"when": when, "interval": interval, "backupCount": backup_count, "utc": utc}
            if encoding:
                kwargs["encoding"] = encoding
            
            return logging.handlers.TimedRotatingFileHandler(filename, **kwargs)
            
        except ImportError:
            # Fall back to regular FileHandler
            return self._create_file_handler(config)
    
    # ========================================================================
    # FORMATTER SERIALIZATION
    # ========================================================================
    
    def _serialize_formatter(self, obj: logging.Formatter) -> Dict[str, Any]:
        """
        Serialize logging.Formatter objects.
        """
        result = {
            "format_string": getattr(obj, '_fmt', None),
            "date_format": getattr(obj, 'datefmt', None),
            "style": getattr(obj, '_style', '%'),  # Python 3.2+
            "formatter_class": f"{type(obj).__module__}.{type(obj).__name__}"
        }
        
        # Handle style attribute (might be an object in Python 3.2+)
        try:
            if hasattr(obj, '_style') and hasattr(obj._style, '_fmt'):
                result["style"] = getattr(obj._style, '_fmt', '%')
        except Exception:
            pass
        
        result["recreation_possible"] = True
        
        return result
    
    def _deserialize_formatter(self, data: Dict[str, Any]) -> logging.Formatter:
        """
        Deserialize logging.Formatter objects.
        """
        format_string = data.get("format_string")
        date_format = data.get("date_format")
        style = data.get("style", '%')
        
        try:
            # Create formatter with available parameters
            if sys.version_info >= (3, 2):
                # Python 3.2+ supports style parameter
                return logging.Formatter(fmt=format_string, datefmt=date_format, style=style)
            else:
                # Older Python versions
                return logging.Formatter(fmt=format_string, datefmt=date_format)
                
        except Exception:
            # If formatter creation fails, create a basic formatter
            return logging.Formatter()
    
    # ========================================================================
    # FILTER SERIALIZATION
    # ========================================================================
    
    def _serialize_filter(self, obj: logging.Filter) -> Dict[str, Any]:
        """
        Serialize logging.Filter objects.
        """
        result = {
            "filter_name": getattr(obj, 'name', ''),
            "filter_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "filter_callable": callable(obj) and not isinstance(obj, logging.Filter)
        }
        
        # If it's a function/callable filter, we can't serialize it
        if result["filter_callable"]:
            result["recreation_possible"] = False
            result["note"] = "Callable filters cannot be serialized"
        else:
            result["recreation_possible"] = True
        
        return result
    
    def _deserialize_filter(self, data: Dict[str, Any]) -> logging.Filter:
        """
        Deserialize logging.Filter objects.
        """
        filter_name = data.get("filter_name", '')
        filter_callable = data.get("filter_callable", False)
        recreation_possible = data.get("recreation_possible", True)
        
        if not recreation_possible or filter_callable:
            # Create a placeholder filter that allows all records
            class PlaceholderFilter(logging.Filter):
                def filter(self, record):
                    return True  # Allow all records
            
            return PlaceholderFilter(filter_name)
        
        try:
            return logging.Filter(filter_name)
        except Exception:
            # If filter creation fails, create a basic filter
            return logging.Filter()
    
    # ========================================================================
    # UNKNOWN LOGGING OBJECT SERIALIZATION
    # ========================================================================
    
    def _serialize_unknown_logging_object(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown logging object types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_type": type(obj).__name__,
            "object_module": getattr(type(obj), '__module__', 'unknown'),
            "note": f"Unknown logging object type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_logging_object(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown logging object types with placeholder.
        """
        object_type = data.get("object_type", "unknown")
        
        # Return a basic logger as fallback
        logger = logging.getLogger(f"unknown_logging_object_{object_type}")
        logger.setLevel(logging.INFO)
        return logger
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _create_logging_placeholder(self, logging_type: str, error_message: str) -> Any:
        """
        Create a placeholder logging object for objects that failed to deserialize.
        """
        if logging_type == "logger":
            logger = logging.getLogger(f"error_logger_{id(error_message)}")
            logger.setLevel(logging.ERROR)
            return logger
        
        elif logging_type == "handler":
            handler = logging.StreamHandler()
            handler.setLevel(logging.ERROR)
            return handler
        
        elif logging_type == "formatter":
            return logging.Formatter("ERROR: Formatter deserialization failed")
        
        elif logging_type == "filter":
            class ErrorFilter(logging.Filter):
                def filter(self, record):
                    return True  # Allow all records
            return ErrorFilter()
        
        else:
            # Default to logger
            logger = logging.getLogger("unknown_error_logger")
            logger.setLevel(logging.ERROR)
            return logger


# Create a singleton instance for auto-registration
loggers_handler = LoggersHandler()