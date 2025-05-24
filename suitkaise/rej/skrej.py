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

