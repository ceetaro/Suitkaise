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

# suitkaise/int/utils/sk_ui/themes.py

"""
Module for managing themes that SK UI components can use.

"""

import threading
from typing import Callable, List, Optional, Dict, Type

class SKThemeRegistry:
    """
    Singleton registry to manage all registered themes.
    
    """
    _sk_theme_registry = None
    _sk_theme_registry_lock = threading.RLock()

    def __new__(cls):
        """Ensure that only one instance of SKThemeRegistry is created."""
        with cls._sk_theme_registry_lock:
            if cls._sk_theme_registry is None:
                cls._sk_theme_registry = super(SKThemeRegistry, cls).__new__(cls)
                cls._sk_theme_registry._init_registry()
        return cls._sk_theme_registry
    
    def _init_registry(self):
        """Initialize the registry with default values."""
        self._themes = {} # theme name -> theme object
        self._active_theme = None
        self.theme_change_callbacks = [] # list of callbacks to call when theme changes

    def register_theme(self, theme):
        """Register a new theme, using theme.name for the name."""
        with self._sk_theme_registry_lock:
            if theme.name not in self._themes:
                self._themes[theme.name] = theme
                if self._active_theme is None:
                    self.set_active_theme(theme.name)

    def set_active_theme(self, theme_name):
        """Set the active theme and notify listeners."""
        if theme_name not in self._themes:
            raise ValueError(f"Theme '{theme_name}' is not registered.")
        with self._sk_theme_registry_lock:
            self._active_theme = self._themes[theme_name]
            self.notify_theme_change()

    def get_active_theme(self):
        """Get the currently active theme."""
        return self._active_theme
        
    def get_theme(self, theme_name):
        """Get a specific theme by name."""
        return self._themes.get(theme_name)
    
    def list_themes(self):
        """List all registered themes."""
        return list(self._themes.keys())
    

    # NOTE: if callbacks need to change theme with different args as well,
    #       convert to using FunctionInstances
    def register_change_callback(self, callback: Callable):
        """
        Register a callback to be called when the theme changes.
        
        Make sure the callback accepts theme as first argument.

        """
        if callback not in self.theme_change_callbacks:
            self.theme_change_callbacks.append(callback)

    def unregister_change_callback(self, callback: Callable):
        """Unregister a callback."""
        if callback in self.theme_change_callbacks:
            self.theme_change_callbacks.remove(callback)

    def _notify_theme_change(self):
        """Notify all registered callbacks of a theme change."""
        for callback in self.theme_change_callbacks:
            try:
                callback(self._active_theme)
            except Exception as e:
                print(f"Error notifying theme change: {e}")



class SKTheme:
    """
    Base class for creating themes.

    This class can be instantiated directly, but it will be a defualt
    grayscale theme.

    What do themes do?
    - themes style prefabs, or custom sk ui components/widgets
    - they can change:
        - colors
        - fonts
        - icons
        - frame styles
        - add custom borders
        - add custom backgrounds
        - components themselves!!! (sort of)

    ex.

    # create a slider to toggle between sorting from oldest or newest
    self.sort_from_slider = SKSlider(self)

    And, depending on the theme, slider could be SKSlider1, SKSlider2, etc.
    The slider object itself wouldn't actually change, but its style would get
    converted to the slider style being used in the theme.
    
    """

    def __init__(self, name="Default Theme", desc="", author="Suitkaise"):
        """
        Initialize the theme with a name, description, and author.

        Args:
            name (str): The name of the theme.
            desc (str): A description of the theme.
            author (str): The author of the theme.
        
        """
        self.name = name
        self.desc = desc
        self.author = author

        # base colors
