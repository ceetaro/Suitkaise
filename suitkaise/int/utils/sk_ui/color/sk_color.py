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

# suitkaise/int/utils/sk_ui/color/sk_color.py

"""
Module responsible for streamlining color management.

This allows for you to define a color in many different ways, as well
as pick a contrasting, complementary, or similar color to the one you
defined. This is useful for creating color palettes, and for
creating color schemes that are easy to read and understand.

Also comes with a color picker that allows you to pick a color from
the screen, and a color wheel.

Comes with an SKColorRegistry that allows you to register custom colors
for use later on.


"""

import threading


class SKColorRegistry:
    """
    Singleton registry to manage all registered colors.

    This class allows you to register custom colors for use later on.
    
    If you register a color with the same name as a Suitkaise default,
    use 'Suitkaise.color' to access the original color (ex. 'Suitkaise.Pine Green').
    
    """
    _sk_color_registry = None
    _sk_color_registry_lock = threading.RLock()

    def __new__(cls):
        """Ensure that only one instance of SKColorRegistry is created."""
        with cls._sk_color_registry_lock:
            if cls._sk_color_registry is None:
                cls._sk_color_registry = super(SKColorRegistry, cls).__new__(cls)
                cls._sk_color_registry._init_registry()
        return cls._sk_color_registry
    
    
    def _init_registry(self):
        """Initialize the registry with default values."""
        self._colors = {}  # color name -> color object
        self._suitkaise_colors = {}  # color name -> color object


    def register_color(self, color_name, color):
        """Register a new color, using color_name for the name."""
        with self._sk_color_registry_lock:
            if color_name not in self._colors:
                self._colors[color_name] = color
            else:
                raise ValueError(f"Color '{color_name}' is already registered.")
        return self._colors[color_name]
    
    
    def deregister_color(self, color_name):
        """Deregister a color, using color_name for the name."""
        with self._sk_color_registry_lock:
            if color_name in self._colors:
                del self._colors[color_name]
            else:
                raise ValueError(f"Color '{color_name}' is not registered.")
            
    
    def register_suitkaise_color(self, color_name, color):
        """
        Register a new Suitkaise color, using color_name for the name.
        
        For internal use only.
        
        """
        with self._sk_color_registry_lock:
            color_name = "Suitkaise." + color_name
            if color_name not in self._suitkaise_colors:
                self._suitkaise_colors[color_name] = color
            else:
                raise ValueError(f"Color '{color_name}' is already registered.")
            
            
    def add(self, color_name, color):
        """
        Add a color to the registry.
        
        This will register the color if it is not already registered.
        
        """
        self.register_color(color_name, color)


    def get(self, color_name):
        """
        Get a color from the registry.
        
        This will return the color if it is registered, otherwise it will
        return None.
        
        """
        with self._sk_color_registry_lock:
            return self._colors.get(color_name)
        
        
    def remove(self, color_name):
        """
        Remove a color from the registry.
        
        This will remove the color if it is registered.
        
        """
        self.deregister_color(color_name)

            
    def is_registered(self, color_name):
        """
        Check if a color is registered.
        
        This will return True if the color is registered, otherwise it will
        return False.
        
        """
        with self._sk_color_registry_lock:
            return color_name in self._colors
        return False
            



class SKColor:
    """
    Class representing a color.

    This class allows you to define a color in many different ways,
    and converts it to a hex value color.

    Supported formats:
    - Hex: #RRGGBB, #RGB
    - RGB: (R, G, B)
    - common colors (manually added)
    - any format + lighter n%, darker n%
    - any format + complementary
    - any format + contrasting
    - any format + n% color

    examples:

    primary_color = SKColor('Pine Green') (#008C45)

    (# make a secondary color that is 10% lighter and 10% more red)

    secondary_color = primary_color.lighter(10).more("red", 10)

    (# make a tertiary color that contrasts and is 30% darker)

    tertiary_color = primary_color.contrasting().darker(30)

    (# make a fourth color, a really light blue)

    fourth_color = SKColor('Light Blue').lighter(20)

    (# save the colors for later)
    SKColorRegistry.add('theme1_primary', primary_color)
    SKColorRegistry.add('theme1_secondary', secondary_color)
    SKColorRegistry.add('theme1_tertiary', tertiary_color)
    SKColorRegistry.add('theme1_fourth', fourth_color)

    (# get the colors later)
    primary_color = SKColor('theme1_primary')
    
    """

    def __init__(self, color):
        """
        Initialize the SKColor object.

        Args:
            color: The color to initialize the object with. This can be a
                   hex string, RGB tuple, or a common color name.

        """
        self.color = self._validate_color(color)
        self.hex_color = self._to_hex(self.color)

    



