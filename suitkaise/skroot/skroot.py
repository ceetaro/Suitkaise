# add license here

# suitkaise/skroot/skroot.py

"""
SKRoot - Smart object storage that follows your project structure

This conceptually allows you to store objects in your project structure at different 
directories, and allows these objects to be shared with subdirectories. Maps your
directory structure into a container where you can store objects that your whole directory can access,
including its subdirectories.

Simple Example:
```python
    # Your project structure automatically becomes a container
    root = SKRoot.create_root()
    
    # Turn specific folders into active containers
    root.activate_branch("src/api")
    root.activate_branch("src/database")
    
    # Store a database connection in the main folder
    api_folder = root.get_branch("src/api")
    api_folder.store("db_connection", DatabaseConnection())
    
    # Subfolders can access it automatically
    auth_folder = root.get_branch("src/api/auth")
    db = auth_folder.resolve("db_connection")  # Gets it from parent folder
```
"""
import os 
from typing import Any, Dict, Optional, List, Callable
from pathlib import Path
from enum import Enum
import threading

from suitkaise.skglobals import SKGlobal, GlobalLevel, get_project_root
import suitkaise.skpath.skpath as skpath
import suitkaise.sktime.sktime as sktime

class SKRootError(Exception):
    """Something went wrong with SKRoot."""
    pass

class SKRootNotInitializedError(SKRootError):
    """You need to call create_root() before using SKRoot."""
    pass

class SKBranchError(SKRootError):
    """Something went wrong with an SKBranch (directory container)."""
    pass

class SKBranchNotFoundError(SKBranchError):
    """The requested SKBranch was not found."""
    pass

class SKBranchNotActiveError(SKBranchError):
    """The requested SKBranch is not active -- call activate_branch() first."""
    pass

class SKBranch:
    """
    A container that can store and share objects "in" a certain directory.

    An SKBranch is a smart folder that:
    - Stores objects that you can access globally
      - ex. database connections, configuration settings, etc, that you might
        want to access across multiple files in a directory.
    - shares objects with sub-branches (subdirectories) if you want it to.
    - gets objects from parent branches (parent directories) if you want it to.
    - adheres to rules you set regarding object sharing/retrieval.
    
    Branches start inactive, and activate (become ready to store and share objects)
    when you call `activate_branch()` with the directory's path you want to activate.

    """

    class Ruleset:
        """
        All the rules for how branches share objects with each other.

        This keeps all rule types organized and makes it easy to add custom rules
        later.
        
        """
        class RuleTypes(Enum):
            """
            Types of rules that can be applied to branches.

            Each rule type has its own section in the Ruleset class.
            Only one rule from each section can be active at a time.

            """
            FROM_PARENT = "from_parent"
            TO_CHILDREN = "to_children"
            WHERE_TO_CHECK = "where_to_check"

        class FromParent(Enum):
            """
            Rules for how branches get objects from parent branches.

            Only one rule from this section can be active at a time.

            """
            # can only receive these objects from parent branches
            CAN_ONLY_RECEIVE = "can_only_receive"
            # cannot receive these objects from parent branches
            CANT_RECEIVE = "cant_receive"

        class ToChildren(Enum):
            """
            Rules for how branches share objects with child branches.

            Only one rule from this section can be active at a time.

            """
            # can only share these objects with child branches
            CAN_ONLY_SHARE = "can_only_share"
            # cannot share these objects with child branches
            CANT_SHARE = "cant_share"

        class WhereToCheck(Enum):
            """
            Rules for where to check first when looking for something.

            """
            # check parent first
            PARENT_FIRST = "parent_first"
            # check locally
            LOCAL_FIRST = "local_first"

        class Custom:
            """
            Custom rules that can be added by the user.
            
            This will be implemented once SKFunction is created.

            """
            pass

        


            
    