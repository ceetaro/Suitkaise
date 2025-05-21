# add license here

# suitkaise/rej/rej.py
from typing import Any, Dict, Optional, Type, Union
from abc import ABC, abstractmethod

class Rej(ABC):
    """
    Basic shell for registry classes, that comes with basic methods.
    
    """


class SingletonRej(Rej):
    """
    Singleton registry class.
    
    This class is a singleton, meaning only one instance of it can exist.
    
    """
    _instance: Optional['SingletonRej'] = None

    def __new__(cls) -> 'SingletonRej':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

