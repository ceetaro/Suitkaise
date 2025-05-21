# add license here

# suitkaise/skglobals/skglobals.py

"""
Module for creating and managing global variables and registries.

- create leveled global variables using SKRoots/Leaves
- create cross process global storage and variables using multiprocessing.Manager
- global storage automatically created for each SKRoot/Leaf that needs to share data
- globals can auto-sync with each other if needed

"""


class SKGlobal:
    pass

class GlobalStorage:
    pass