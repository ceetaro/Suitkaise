"""
Set a skill level to use the suitkaise library at.

Beginner: very simplified API and functions, advanced features are hidden and
default to safe values.

Intermediate: more advanced API, some features are hidden, but most are available.

Advanced: full API, all features are available. There is a suitkaise specific 
learning curve that goes beyond standard Python knowledge, so please refer to 
tutorials and documentation for advanced usage.

If no skill level is set, the default is Advanced.

Example usage:
import suitkaise.lvl as lvl

# module level
lvl.beginner.set() # stores this in an SKGlobal object

Behind the scenes (using SKGlobal as an example):

# all args for creating an SKGlobal object
def create_skglobal(name, level, path, value, auto_sync, auto_create, remove_in):
    level = get_lvl() -> returns Beginner because we set it above

# what Beginner needs to add: just name and value
def create_skglobal(name, value)
- it will assume level is GlobalLevel.TOP, auto_sync is True, 
  path is caller module path, etc.

# what Intermediate needs to add: name, value, path, level

# what Advanced needs to add: all args (they still default to safe values)

The difference is the level of manual intervention and fine control you have over the
library. 

"""
from enum import Enum, auto

class SkillLevel(Enum):
    BEGINNER = auto()
    INTERMEDIATE = auto()
    ADVANCED = auto()
    
Beginner = SkillLevel.BEGINNER
Intermediate = SkillLevel.INTERMEDIATE
Advanced = SkillLevel.ADVANCED

def set(level: SkillLevel):
    """
    Set the skill level for using the suitkaise library.
    
    Store this as a global under this module's name in current SKBranch.

    """