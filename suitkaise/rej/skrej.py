# add license here

# suitkaise/rej/rej.py
from typing import (
    Any, Dict, Optional, Type, Union, 
    List, Callable, TypeVar, Generic, Set
    )
from enum import Enum, auto

T = TypeVar('T')

class OnDuplicate(Enum):
    """
    4 options for handling duplicate registrations:
    - create new with _number after name
      - if name_number exists, increment
    - overwrite existing
    - ignore new registration
    - raise error
    
    """
    CREATE_NEW = auto()
    OVERWRITE = auto()
    IGNORE = auto()
    RAISE_ERROR = auto()

class Rej(Generic[T]):
    """
    Basic registry class with core functionality.

    - Register items
    - Retrieve items
    - Remove items
    - Check if items exist
    - List registered item names

    Generic class for type safety.
    
    """

    def __init__(self, 
                 duplicates: bool = False,
                 on_duplicate: OnDuplicate = OnDuplicate.IGNORE) -> None:
        """
        Initialize an empty registry.
        
        Args:
            duplicates: Allow duplicate names.
            on_duplicate: Action to take on duplicate registrations.
                Use the enum OnDuplicate to specify the action:
                - CREATE_NEW: Create a new item with a number suffix.
                - OVERWRITE: Overwrite the existing item.
                - IGNORE: Ignore the new registration.
                - RAISE_ERROR: Raise an error on duplicate registration.
        
        """
        self._duplicates = duplicates
        self._on_duplicate = on_duplicate
        self._registry: Dict[str, T] = {}

    def register(self, name: str, item: T) -> None:
        """
        Register an item with the given name.

        Args:
            name: The name of the item
            item: The item to register

        Raises:
            ValueError: If the item is already registered and duplicates are not allowed.
        
        """
        if name not in self._registry:
            self._registry[name] = item
        elif name in self._registry:
            if self._duplicates:
                if self._on_duplicate == OnDuplicate.CREATE_NEW:
                    base_name = name
                    i = 1
                    while f"{base_name}_{i}" in self._registry:
                        i += 1
                    new_name = f"{base_name}_{i}"                   
                    self._registry[new_name] = item
                elif self._on_duplicate == OnDuplicate.OVERWRITE:
                    self._registry[name] = item
                elif self._on_duplicate == OnDuplicate.IGNORE:
                    print(f"Item '{name}' already registered. This item will be ignored.")
                elif self._on_duplicate == OnDuplicate.RAISE_ERROR:
                    raise ValueError(f"Item '{name}' already registered. Cannot register again.")
        else:
            raise ValueError(f"Item '{name}' already registered. Cannot register again.")
    
        print(f"Item '{name}' registered successfully.")

    def get(self, name: str) -> Optional[T]:
        """
        Retrieve an item by its name.

        Args:
            name: The name of the item to retrieve.

        Returns:
            The registered item or None if not found.

        """
        return self._registry.get(name, None)
    
    def remove(self, name: str) -> None:
        """
        Remove an item from the registry.

        Args:
            name: The name of the item to remove.

        Raises:
            KeyError: If the item is not found in the registry.

        """
        if name not in self._registry:
            raise KeyError(f"Item '{name}' not found in registry.")
        self._registry.pop(name)

    def contains(self, name: str) -> bool:
        """
        Check if an item is registered.

        Args:
            name: The name of the item to check.

        Returns:
            True if the item is registered, False otherwise.

        """
        return name in self._registry
    
    def get_all(self) -> Dict[str, T]:
        """
        Get all registered items.

        Returns:
            A dictionary of all registered items.

        """
        return self._registry.copy()
    
    def get_names(self) -> List[str]:
        """
        Get all registered item names.

        Returns:
            A list of names of all registered items.

        """
        return list(self._registry.keys())
    
    def clear(self) -> None:
        """Remove all items from the registry."""
        self._registry.clear()
        print("All items removed from registry.")

    def __len__(self) -> int:
        """Get the number of registered items."""
        return len(self._registry)
    
    def __contains__(self, name: str) -> bool:
        """Check if an item is registered."""
        return name in self._registry
    
    def __iter__(self):
        """Iterate over the registered items."""
        return iter(self._registry.items())


class SingletonRej(Rej):
    """
    Singleton registry class.
    
    This class is a singleton, meaning only one instance of it can exist.
    
    """
    _instance: Optional['SingletonRej'] = None

    def __new__(cls, *args, **kwargs) -> 'SingletonRej':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'SingletonRej':
        """
        Get the singleton instance of the registry.

        Returns:
            The singleton instance of the registry.

        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    

class SKRej(Rej):
    """
    Registry class with additional functionality.

    - add an SKRoot to the registry
      - if a file accesses this registry type, than it will use the instance 
        closest to the file's location, unless otherwise specified
    - does not allow duplicate instances in the same root
    
    """
    _max_instances: int = 1
    _max_instances_reached: bool = False
    _valid_roots: Set[SKRoot | SKLeaf] = set()
    _instances: Dict[str, 'SKRej'] = {}

    def __new__(cls, name: str, level: SKRoot | SKLeaf) -> 'SKRej':
        if name not in cls._instances and root is not None:
            cls._instances[name] = super().__new__(cls)
            cls._instances[name]._level = level
        return cls._instances[name]
    


