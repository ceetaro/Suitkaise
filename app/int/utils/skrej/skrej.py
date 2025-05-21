# add license here

# suitkaise/int/utils/skrej/skrej.py

"""
Module for creating the global, internal and external registry pattern that
Suitkaise uses.

- SKRegistries (creates one registry at each level)
- SKRej (base class for 3 below)
- GlobalRej (registry that goes at top level (outside of int/ext))
- IntRej (registry for internal suitkaise use)
- ExtRej (registry for external user imported code to use)

"""