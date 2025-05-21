# add license here

# suitkaise/skroot/skroot.py

"""
Module for creating and managing SKRoots and SKLeaves.

- SKRoot is an object that represents a root.
- SKLeaf is a root like object that is not actually the project root.

Say you want to have mulitple instances of a singleton registry at differnt levels
in your project, with the main path being myproject/level1/level2/level3.

An SKRoot would get created for myproject. that doesn't mean it is created in myproject,
but rather when created, points to myproject.

If you want a different registry at level1, level2, or level3, but want them to sync
with the root SKRoot, you can create a SKLeaf for each of those levels. The SKLeaf acts
exactly the same as a pointer to the directory it was made for, but with the added bonus
of being able to sync with the SKRoot.

If the SKRoot and an SKLeaf have the same object type in storage, the root will be able 
to send changes or sync to the leaf if we want, and vice versa.

"""

class RootProperties:
    """
    Common properties for SKRoot and SKLeaf.
    
    """

class SKRoot(RootProperties):
    pass

class SKLeaf(RootProperties):
    pass
