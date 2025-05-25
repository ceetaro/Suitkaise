# add license here

# suitkaise/skroot/skroot.py

"""
This module provides functionality to create and manage objects in global storage
that point to directories.

How it works:
- Initialize the SKRoot in TOP level global storage with SKRoot.create_root().
- Create an SKBranch, that points to a certain directory.
- Create SKLeaf objects connected to an SKBranch, which point to files or subdirectories
  of the SKBranch's directory.

you can check for root-branch-leaf structures by using get_branch(), get_leaf(), or get_tree()
- The SKRoot object is a global singleton that manages all branches and leaves in top level global storage.
- build tree and branch relationships by checking global storage at paths where SKRoot, SKBranch, and SKLeaf 
  objects were stored.


- Useful for:
- managing permissions for certain parts of the project
- checking what parts of the project are being used and errors that occur in them
- getting resource statistics for specific parts of the project during actual use
- policing data exchange between global storages.

"""