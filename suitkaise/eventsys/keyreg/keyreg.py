# -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0 or the GNU General Public License v3.
#
# ~~ Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
#
# ~~ GNU General Public License, Version 3 (http://www.gnu.org/licenses/gpl-3.0.html)
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -------------------------------------------------------------------------------------

# suitkaise/eventsys/keyreg/keyreg.py

"""
The EventKeyRegistry and OptionalKeyRegistry, together making the 'keyreg', are
responsible for managing all data that gets added to a posting event. Data that
gets added should be registered key-value pairs, with the key being a name and 
the value being the valid data type. The key-value pairs are stored in a dictionary,
and allow event data to be validated both before and after event posting.

The EventKeyRegistry is a singleton class that manages all valid keys that can be
used in events, their expected data types, and optional validators that ensure
data integrity and uniformity across the system. It also provides methods for
registering, unregistering, and validating keys, as well as retrieving key metadata.

The OptionalKeyRegistry is a singleton class that manages optional keys, which
can be removed during event compression to reduce memory usage. It provides methods
for registering optional keys, changing their status to a required key, and checking
if a key is optional. It also provides methods for retrieving all registered optional
keys and checking if a key is optional.

"""


import threading
from typing import Dict, Type, Any, Optional, Callable, List, Set, Union, Tuple
from enum import Enum, auto
import uuid

import suitkaise.time.sktime as sktime
from suitkaise.eventsys.data.enums.enums import CompressionLevel

AnyType = Union[None, str, int, float, bool, Dict[str, Any], List[Any], Set[Any], Tuple[Any, ...], Enum]

class EventKeyRegistry:
    """
    Singleton registry for event keys.

    Manages all valid keys that can be uesd in events, their expected data types,
    and optional validators that ensure data integrity and uniformity across the system.

    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventKeyRegistry, cls).__new__(cls)
                cls._instance._keys = {}
                cls._instance._initialized = False
            return cls._instance
        
    def __init__(self):
        with self._lock:
            if not self._initialized:
                self._keys = {}
                self._initialized = True

    def register(self, 
                 key: str,
                 key_user: Optional[str],
                 value_type: Union[Type, Tuple[Type, ...], List[Type], AnyType],
                 validator: Optional[Callable[[Any], bool]] = None,
                 is_optional: bool = False,
                 should_compress: bool = False,
                 replace_with_function: Optional[Callable[[Any], Any]] = None,
                 description: Optional[str] = None,) -> None:
        """
        Register a key with the EventKeyRegistry and optionally the OptionalKeyRegistry.

        Args:
            key: Key name to register 

            key_user: The user of the key. For example, MyEvent.

            value_type: The expected type of the value.
                - AnyType is a type hint for any valid standard Python data type, plus 
                Enum.

            validator: Optional function to validate the value, 
            if the value is not a standard type.

            is_optional (bool): If True, the key is optional.
                - if True, key will also get registered in the OptionalKeyRegistry.

            should_compress: If True, the key will be compressed during event compression.
                - if True, the key will likely get compressed when event histories
                  need to be compressed to save memory.
                - mark this as False if the key would not function properly if compressed,
                  or it not necessary to compress it.
                  NOTE: ints, floats, and bools automatically have this as False.

            replace_with_function: If True, the key can be replaced with a 
            function that can regenerate the value if the key is needed again.
                - if True, during event compression, the key will be replaced with 
                  a function that can regenerate the value if the key is needed again.
                - example: regenerating an ast.Module tree instead of keeping the 
                  entire tree in memory.

            description: Optional description for the key.
        
        """
        with self._lock:
            # validate inputs
            if not isinstance(key, str):
                raise ValueError("Key must be a string.")
            
            # convert single types to list for streamlined handling
            if not isinstance(value_type, list):
                value_type = [value_type]

            # create key
            if key_user and isinstance(key_user, str):
                key = f"{key_user}.{key}"
            else:
                key = key

            if not key:
                raise ValueError("Key cannot be empty.")
            if key in self._keys:
                raise KeyError(f"Key '{key}' is already registered.")
            
            # store key metadata
            self._keys[key] = {
                'key': key,
                'key_user': key_user,
                'value_type': value_type,
                'validator': validator,
                'is_optional': is_optional,
                'description': description,
                'id': uuid.uuid4(),
                'idshort': str(uuid.uuid4())[:8],
                'created': sktime.now(),
                'should_compress': should_compress,
                'is_compressed': CompressionLevel.NONE,
                'replace_with_function': replace_with_function,
            }

            if is_optional:
                OptionalKeyRegistry().register_as_optional(self._keys[key])

            print(f"Registered key: {key}")
            print(f"  - User: {key_user}")
            print(f"  - Value Type: {value_type}")
            print(f"  - Optional: {is_optional}")
            print(f"  - Description: {description}")
            print(f"  - Validator: {validator.__name__ if validator else 'None'}")
            print(f"  - UUID: {uuid.uuid4()}")
            print(f"  - ID Short: {str(uuid.uuid4())[:8]}")
            print(f"  - Created: {sktime.to_custom_time_format(self._keys[key]['created'])}")
            if should_compress:
                print(f"  - Should Compress: {should_compress}")
                print(f"  - Replace with function: "
                    f"{replace_with_function.__name__ if replace_with_function else 'None'}")
            print("\n")


    def unregister(self, key: str) -> bool:
        """
        Unregister a key from the registry.

        Args:
            key: Key name to unregister.

        Returns:
            bool: True if the key was unregistered, False if it was not found.

        """
        with self._lock:
            if key in self._keys:
                del self._keys[key]
                print(f"Unregistered key: {key}")
                return True
            else:
                print(f"Key '{key}' not found in registry.")
                return False
            

    def is_registered(self, key: str) -> bool:
        """
        Check if a key is registered in the registry.

        Args:
            key: Key name to check.

        Returns:
            bool: True if the key is registered, False otherwise.
        
        """
        return key in self._keys
    
    def change_optional_status(self, key: str, is_optional: bool) -> None:
        """
        Change the optional status of a key.

        Args:
            key: Key name to change.
            is_optional: New optional status for the key.
        
        """
        with self._lock:
            if key in self._keys:
                self._keys[key]['is_optional'] = is_optional
                print(f"Changed optional status of key '{key}' to {is_optional}.")
            else:
                print(f"Key '{key}' not found in registry.")

    def validate_event_data(self, key: str, value: Any) -> bool:
        """
        Validate a key-value pair.

        If the key has a validator, use it to validate the value.
        Otherwise, assume key's value is a standard data type, or Enum.

        Args:
            key: Key name to validate.
            value: Value to validate.


        """
        # check if registered
        if not self.is_registered(key):
            print(f"Warning: Key '{key}' is not registered.")
            return False
        
        # get the key metadata
        key_metadata = self._keys[key]
        value_types = key_metadata['value_type']
        validator = key_metadata['validator']

        # check the value type
        type_valid = False
        for expected_type in value_types:
            if isinstance(value, expected_type):
                type_valid = True
                break

        if validator is not None:
            try:
                if not validator(value):
                    print(f"Validation with validator {validator.__name__} "
                          f"failed for key '{key}' with value '{value}'.")
                    return False
            except Exception as e:
                print(f"Error using validator {validator.__name__} "
                      f"to validate key '{key}' with value '{value}': {e}")
                return False

        if not type_valid:
            print(f"Warning: Value '{value}' for key '{key}' is not of expected type(s) "
                  f"{[t.__name__ for t in value_types]}.")
            return False
        
        return True
    
    def get_key_info(self, key: str) -> Dict[str, Any]:
        """
        Get the metadata for a registered key.

        Args:
            key: Key name to get metadata for.

        Returns:
            Dict[str, Any]: Metadata for the key, or None if not found.
        
        """
        return self._keys.get(key, None)
    
    def get_all_key_names(self) -> List[str]:
        """
        Get all registered key names.

        Returns:
            List[str]: List of all registered key names.
        
        """
        return list(self._keys.keys())
    
    def print_all_keys(self, with_metadata: bool = False) -> None:
        """
        Print all registered key names, and their metadata if requested.

        Args:
            with_metadata: If True, print metadata for each key.
        
        """
        if not with_metadata:
            keynames = self.get_all_key_names()
            print("Registered keys:")
            for key in keynames:
                print(f"  - {key}")

        else:
            for key in self._keys:
                key_metadata = self.get_key_info(key)
                print(f"Key: {key}")
                print(f"  - User: {key_metadata['key_user']}")
                print(f"  - Value Type: {key_metadata['value_type']}")
                print(f"  - Optional: {key_metadata['is_optional']}")
                print(f"  - Description: {key_metadata['description']}")
                print(f"  - Validator: {key_metadata['validator'].__name__ if key_metadata['validator'] else 'None'}")
                print(f"  - UUID: {key_metadata['id']}")
                print(f"  - ID Short: {key_metadata['idshort']}")
                print(f"  - Created: {sktime.to_custom_time_format(key_metadata['created'])}")
                print("\n")

            print("Total keys registered:", len(self._keys))


    def get_all_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered keys and their metadata.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of all registered keys and their metadata.
        
        """
        return self._keys.copy()
        
    
    def get_keys_with_user(self, key_user: str) -> List[Dict[str, Any]]:
        """
        Get all keys registered by a specific user, and their metadata.

        Args:
            key_user: The user of the keys.

        Returns:
            List[str]: List of keys registered by the user.
        
        """
        return [key for key in self._keys if self._keys[key]['key_user'] == key_user]
    
    
    def get_keys_with_type(self, value_type: Type) -> List[Dict[str, Any]]:
        """
        Get all keys registered with a specific value type.

        Args:
            value_type: The value type to search for.

        Returns:
            List[str]: List of keys with the specified value type.
        
        """
        return [key for key in self._keys if value_type in self._keys[key]['value_type']]
    


class OptionalKeyRegistry:
    """
    Singleton registry for optional keys.

    This registry stores keys from the EventKeyRegistry that are marked as optional.
    Optional keys can be removed during event compression to reduce memory usage.

    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OptionalKeyRegistry, cls).__new__(cls)
                cls._instance._optional_keys = set()
                cls._instance._initialized = False
            return cls._instance
        
    def __init__(self):
        with self._lock:
            if not self._initialized:
                self._optional_keys = set()
                self._initialized = True

    def register_as_optional(self, key: Dict[str, Any]) -> None:
        """
        Register an optional key.

        Args:
            key: The key to register.
        
        """
        with self._lock:
            if key['key'] not in self._optional_keys and key['is_optional'] is True:
                self._optional_keys.add(key)
                print(f"Registered optional key: {key['key']}")
            elif key['key'] in EventKeyRegistry().get_all_key_names() and key['key'] not in self._optional_keys:
                self._optional_keys.add(key)
                EventKeyRegistry().change_optional_status(key['key'], True)
                print(f"Reregistered existing key as optional key: {key['key']}")
            else:
                print(f"Optional key '{key['key']}' is already registered.")


    def change_to_required_key(self, key: Dict[str, Any]) -> bool:
        """
        Unregister an optional key and change its status in the EventKeyRegistry.

        Args:
            key: The key to unregister.

        Returns:
            bool: True if the key was unregistered, False if it was not found.
        
        """
        with self._lock:
            if key in self._optional_keys:
                self._optional_keys.remove(key)
                EventKeyRegistry().change_optional_status(key['key'], False)
                print(f"Unregistered optional key: {key['key']}")
                return True
            else:
                print(f"Optional key '{key['key']}' not found in registry.")
                return False
            

    def is_optional(self, key: str) -> bool:
        """
        Check if a key is optional.

        Args:
            key: Key name to check.

        Returns:
            bool: True if the key is optional, False otherwise.
        
        """
        return key in self._optional_keys
    
    
    def get_all_optional_keys(self) -> List[Dict[str, Any]]:
        """
        Get all registered optional keys.

        Returns:
            List[str]: List of all registered optional keys.
        
        """
        return self._optional_keys.copy()
    

def initialize_key_registries() -> None:
    """
    Initialize the key registries.

    This function is called at the start of the program to set up the key registry.
    It creates an instance of the EventKeyRegistry and OptionalKeyRegistry.
    
    """
    with EventKeyRegistry._lock:
        EventKeyRegistry()
    with OptionalKeyRegistry._lock:
        OptionalKeyRegistry()


def register(key: str,
                 key_user: Optional[str],
                 value_type: Union[Type, Tuple[Type, ...], List[Type], AnyType],
                 validator: Optional[Callable[[Any], bool]] = None,
                 is_optional: bool = False,
                 description: Optional[str] = None) -> None:
    """
    Register a key with the EventKeyRegistry and optionally the OptionalKeyRegistry.

    Args:
        key: Key name to register.

        key_user: The user of the key. For example, MyEvent.

        value_type (Union[Type, Tuple[Type, ...], List[Type], AnyType]): The expected type of the value.
            - AnyType is a type hint for any valid standard Python data type, plus Enum.

        validator (Optional[Callable[[Any], bool]]): Optional function to validate the value,
            if the value is not a standard type.

        is_optional (bool): If True, the key is optional.
            - if True, key will also get registered in the OptionalKeyRegistry.

        description (Optional[str]): Optional description for the key.
    
    """
    event_key_registry = EventKeyRegistry()
    event_key_registry.register(key, key_user, value_type, validator, is_optional, description)

    if is_optional:
        optional_key_registry = OptionalKeyRegistry()
        optional_key_registry.register_as_optional(event_key_registry.get_key_info(key))


def validate(key: str, value: Any) -> bool:
    """
    Validate a key-value pair.

    If the key has a validator, use it to validate the value.
    Otherwise, assume key's value is a standard data type, or Enum.

    Args:
        key: Key name to validate.
        value: Value to validate.

    Returns:
        bool: True if the key-value pair is valid, False otherwise.
    
    """
    event_key_registry = EventKeyRegistry()
    return event_key_registry.validate_event_data(key, value)


def get_key_info(key: str) -> Dict[str, Any]:
    """
    Get the metadata for a registered key.

    Args:
        key: Key name to get metadata for.

    Returns:
        Dict[str, Any]: Metadata for the key, or None if not found.
    
    """
    event_key_registry = EventKeyRegistry()
    return event_key_registry.get_key_info(key)

def get_all_key_names() -> List[str]:
    """
    Get all registered key names.

    Returns:
        List[str]: List of all registered key names.
    
    """
    event_key_registry = EventKeyRegistry()
    return event_key_registry.get_all_key_names()

def print_all_keys(with_metadata: bool = False) -> None:
    """
    Print all registered key names, and their metadata if requested.

    Args:
        with_metadata: If True, print metadata for each key.
    
    """
    event_key_registry = EventKeyRegistry()
    event_key_registry.print_all_keys(with_metadata)

def get_all_keys() -> Dict[str, Dict[str, Any]]:
    """
    Get all registered keys and their metadata.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of all registered keys and their metadata.
    
    """
    event_key_registry = EventKeyRegistry()
    return event_key_registry.get_all_keys()

def get_keys_with_user(key_user: str) -> List[Dict[str, Any]]:
    """
    Get all keys registered by a specific user, and their metadata.

    Args:
        key_user: The user of the keys.

    Returns:
        List[str]: List of keys registered by the user.
    
    """
    event_key_registry = EventKeyRegistry()
    return event_key_registry.get_keys_with_user(key_user)

def get_keys_with_type(value_type: Type) -> List[Dict[str, Any]]:
    """
    Get all keys registered with a specific value type.

    Args:
        value_type: The value type to search for.

    Returns:
        List[str]: List of keys with the specified value type.
    
    """
    event_key_registry = EventKeyRegistry()
    return event_key_registry.get_keys_with_type(value_type)


def change_optional_status(key: str, is_optional: bool) -> None:
    """
    Change the optional status of a key.

    Args:
        key: Key name to change.
        is_optional: New optional status for the key.
    
    """
    event_key_registry = EventKeyRegistry()
    event_key_registry.change_optional_status(key, is_optional)


def is_registered(key: str) -> bool:
    """
    Check if a key is registered in the registry.

    Args:
        key: Key name to check.

    Returns:
        bool: True if the key is registered, False otherwise.
    
    """
    event_key_registry = EventKeyRegistry()
    return event_key_registry.is_registered(key)


def unregister(key: str) -> bool:
    """
    Unregister a key from the registry.

    Args:
        key: Key name to unregister.

    Returns:
        bool: True if the key was unregistered, False if it was not found.
    
    """
    event_key_registry = EventKeyRegistry()
    return event_key_registry.unregister(key)


def change_to_required_key(key: str) -> bool:
    """
    Unregister an optional key and change its status in the EventKeyRegistry.

    Args:
        key: The key to unregister.

    Returns:
        bool: True if the key was unregistered, False if it was not found.
    
    """
    optional_key_registry = OptionalKeyRegistry()
    return optional_key_registry.change_to_required_key(key)


def is_optional(key: str) -> bool:
    """
    Check if a key is optional.

    Args:
        key: Key name to check.

    Returns:
        bool: True if the key is optional, False otherwise.
    
    """
    optional_key_registry = OptionalKeyRegistry()
    return optional_key_registry.is_optional(key)


def get_all_optional_keys() -> List[Dict[str, Any]]:
    """
    Get all registered optional keys.

    Returns:
        List[str]: List of all registered optional keys.
    
    """
    optional_key_registry = OptionalKeyRegistry()
    return optional_key_registry.get_all_optional_keys()

def should_compress_key(key: str) -> bool:
    """
    Check if a key should be compressed.

    Args:
        key: Key name to check.

    Returns:
        bool: True if the key should be compressed, False otherwise.
    
    """
    event_key_registry = EventKeyRegistry()
    key_info = event_key_registry.get_key_info(key)
    if key_info:
        return key_info['should_compress']
    return False

def get_keys_to_compress(level: CompressionLevel = CompressionLevel.LOW) -> List[str]:
    """
    Get all keys that:
    - have should_compress set to True
    - have is_compressed set to a lower level than the requested level

    Args:
        level: Compression level to check against.

    Returns:
        List[str]: List of keys that should be compressed.
    
    """
    event_key_registry = EventKeyRegistry()
    keys_to_compress = []
    for key, metadata in event_key_registry.get_all_keys().items():
        if metadata['should_compress'] and metadata['is_compressed'] < level:
            keys_to_compress.append(key)
    return keys_to_compress

def key_is_compressed(key: str) -> Tuple[bool, CompressionLevel]:
    """
    Check if a key is compressed.

    Args:
        key: Key name to check.

    Returns:
        Tuple[bool, CompressionLevel]: Tuple containing a boolean 
            indicating if the key is compressed, and the compression level
            it has been compressed to.
    
    """
    event_key_registry = EventKeyRegistry()
    key_info = event_key_registry.get_key_info(key)
    if key_info:
        if key_info['is_compressed'] != CompressionLevel.NONE:
            return True, get_compression_level(key)
        else:
            return False, CompressionLevel.NONE
        
    print(f"Key '{key}' not found in registry.")
    return False, CompressionLevel.NONE

def get_compression_level(key: str) -> CompressionLevel:
    """
    Get the compression level of a key.

    Args:
        key: Key name to check.

    Returns:
        CompressionLevel: The compression level of the key.
    
    """
    event_key_registry = EventKeyRegistry()
    key_info = event_key_registry.get_key_info(key)
    if key_info:
        return key_info['is_compressed']
    
    print(f"Key '{key}' not found in registry.")
    return CompressionLevel.NONE

def upgrade_compression_level(keys: List[str], level: CompressionLevel) -> None:
    """
    Set a new compression level for a list of keys.

    Args:
        keys: List of keys to set the compression level for.
        level: New compression level to set.
    
    """
    event_key_registry = EventKeyRegistry()
    with event_key_registry._lock:
        for key in keys:
            if key in event_key_registry.get_all_key_names():
                if level > event_key_registry.get_key_info(key)['is_compressed']:
                    event_key_registry.get_key_info(key)['is_compressed'] = level
                else:
                    print(f"Key '{key}' is already at a higher compression level.")
            else:
                print(f"Key '{key}' not found in registry.")

        print(f"Set compression level for keys: {keys} to {level}.")

def reset_compression_level(keys: List[str]) -> None:
    """
    Reset the compression level for a list of keys to NONE.

    Call this after decompressing data.

    Args:
        keys: List of keys to reset the compression level for.
    
    """
    event_key_registry = EventKeyRegistry()
    with event_key_registry._lock:
        for key in keys:
            if key in event_key_registry.get_all_key_names():
                event_key_registry.get_key_info(key)['is_compressed'] = CompressionLevel.NONE
            else:
                print(f"Key '{key}' not found in registry.")

        print(f"Reset compression level for keys: {keys} to NONE.")


def is_valid_function_replacement(self) -> bool:
    """
    Check if given data can successfully be used to create a 
    FunctionReplacement object.

    Returns:
        bool: True if valid, False otherwise.
    
    """
    pass


def get_replacement_function():
    """
    Get the replacement function for a key.

    Args:
        key: Key name to get the replacement function for.

    Returns:
        Optional[Callable[[Any], Any]]: The replacement function for the key, 
        or None if not found.
    
    """
    pass

def add_replacement_function() -> None:
    """
    Add a replacement function for a key.

    Also add a string representation of the function, that will
    be used to get required args and kwargs for the function.

    When using repr to populate args and kwargs, do this:

    module.function(arg1=val1, arg2=val2, ...)

    instead of:
    
    module.function(arg1, arg2, ...)

    Args:
        key: Key name to add the replacement function for.
        function: The replacement function to add.
        repr: Required string representation of the function.
    
    """
    pass