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

# suitkaise/int/utils/dprint/dprint_settings.py

"""
Module containing class that manages global Dprint settings.

This class is responsible for initializing, managing, and updating settings for 
Dprints under a certain namespace.

"""

import os
import threading
import logging
import uuid
from typing import Optional, Any, Dict, List, Union, Tuple


import suitkaise.int.utils.domain.skdomain as skdomain
import suitkaise.int.utils.path.get_paths as paths
import suitkaise.int.utils.time.sktime as sktime


class DprintSettingsError(Exception):
    """Custom exception for DprintSettings."""
    pass

class DprintSettingsRegistry:
    """
    Singleton that manages all DprintSettings instances and their settings,
    and provides default settings for them to add onto.

    """
    _dprint_settings_registry = None
    _dprint_settings_registry_lock = threading.RLock()

    def __new__(cls):
        """
        Ensure that only one instance of DprintSettingsRegistry is created.

        """
        with cls._dprint_settings_registry_lock:
            if cls._dprint_settings_registry is None:
                cls._dprint_settings_registry = super().__new__(cls)
            return cls._dprint_settings_registry

    def __init__(self):
        if getattr(self, "_initialized", True):
            return
        
        # instance specific lock
        self._dprint_settings_registry_lock = threading.RLock()
        
        print_to_console = True
        valid_print_levels = [1, 2, 3, 4, 5]
        valid_tags = self._register_default_tags() # list of dicts
        tags_to_include = valid_tags.copy() # copy of valid_tags
        for tag in valid_tags:
            tags_to_include.append(tag["name"])
        
        should_log = False
        valid_log_levels = ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]
        auto_add_newlines = True
        use_shortened_previews = True
        auto_add_timestamp = True
        timestamp_format = sktime.CustomTime.YMD_HMS6
        auto_add_time_since_start = True
        time_diff_format = sktime.CustomTimeDiff.HMS6
        auto_add_file_name = True

        # default settings for all DprintSettings instances
        self._default_settings = {
            skdomain.SKDomain.INTERNAL: {
                "print_to_console": print_to_console,
                "valid_print_levels": valid_print_levels,
                "valid_tags": valid_tags,
                "tags_to_include": tags_to_include,
                "should_log": should_log,
                "valid_log_levels": valid_log_levels,
                "auto_add_newlines": auto_add_newlines,
                "use_shortened_previews": use_shortened_previews,
                "auto_add_timestamp": auto_add_timestamp,
                "timestamp_format": timestamp_format,
                "auto_add_time_since_start": auto_add_time_since_start,
                "time_diff_format": time_diff_format,
                "auto_add_file_name": auto_add_file_name
            },
            skdomain.SKDomain.EXTERNAL: {
                "print_to_console": print_to_console,
                "valid_print_levels": valid_print_levels,
                "valid_tags": valid_tags,
                "tags_to_include": tags_to_include,
                "should_log": should_log,
                "valid_log_levels": valid_log_levels,
                "auto_add_newlines": auto_add_newlines,
                "use_shortened_previews": use_shortened_previews,
                "auto_add_timestamp": auto_add_timestamp,
                "timestamp_format": timestamp_format,
                "auto_add_time_since_start": auto_add_time_since_start,
                "time_diff_format": time_diff_format,
                "auto_add_file_name": auto_add_file_name
            }
        }
        
        self._initialized = True

    @classmethod
    def get_instance(cls) -> 'DprintSettingsRegistry':
        """
        Get the singleton instance of DprintSettingsRegistry.

        """
        with cls._dprint_settings_registry_lock:
            if cls._dprint_settings_registry is None:
                cls._dprint_settings_registry = cls()
            return cls._dprint_settings_registry


    def _register_default_tags(self) -> List[Dict[str, str]]:
        """
        Register default tags for DprintSettings.
        
        """
        # default tags
        warning = {
            "name": "warning",
            "description": "Warning message",
            "color": "#FFA500" # orange
        }
        error = {
            "name": "error",
            "description": "Error message",
            "color": "#FF0000" # red
        }
        info = {
            "name": "info",
            "description": "Info message",
            "color": "#0000FF" # blue
        }
        debug = {
            "name": "debug",
            "description": "Debug message",
            "color": "#00FF00" # green
        }
        critical = {
            "name": "critical",
            "description": "Critical error message",
            "color": "#8B0000" # dark red
        }
        added = {
            "name": "added",
            "description": "Message when something is added",
            "color": "#00FF00" # green
        }
        removed = {
            "name": "removed",
            "description": "Message when something is removed",
            "color": "#FF0000" # red
        }
        changed = {
            "name": "changed",
            "description": "Message when something is changed",
            "color": "#FFA500" # orange
        }
        nothing_changed = {
            "name": "nothing_changed",
            "description": "Message when nothing is changed",
            "color": "#0000FF" # blue
        }
        early_return = {
            "name": "early_return",
            "description": "Message when early return is triggered",
            "color": "#FF00FF" # magenta
        }
        clearing = {
            "name": "clearing",
            "description": "Message when clearing something",
            "color": "#D3D3D3" # light gray
        }
        compressing = {
            "name": "compressing",
            "description": "Message when compressing/decompressing something",
            "color": "#D3D3D3" # light gray
        }
        not_registered = {
            "name": "not_registered",
            "description": "Message when something is not registered",
            "color": "#FF00FF" # magenta
        }
        not_found = {
            "name": "not_found",
            "description": "Message when something is not found/provided",
            "color": "#FF00FF" # magenta
        }
        invalid = {
            "name": "invalid",
            "description": "Message when something is invalid",
            "color": "#FF00FF" # magenta
        }
        initialized = {
            "name": "initialized",
            "description": "Message when something is initialized",
            "color": "#006400" # dark green
        }

        return [
            warning,
            error,
            info,
            debug,
            critical,
            added,
            removed,
            changed,
            nothing_changed,
            early_return,
            clearing,
            compressing,
            not_registered,
            not_found,
            invalid,
            initialized
        ]




class DprintSettings:
    """
    Class that manages global Dprint settings.

    """
    _settings_instances = []
    _max_instances = 2 # 1 for internal code, 1 for external code
    _dprint_settings_creation_lock = threading.RLock()
    
    def __new__(cls):
        """
        Ensure that a maximum of 4 instances of DprintSettings are created.

        If there is an instance at a higher level directory than the current
        one trying to create an instance, return that instance instead.

        If not, and there are less than 4 instances, create a new one.
        
        """
        with cls._dprint_settings_creation_lock:
            num_instances = len(cls._settings_instances)
            domain = skdomain.get_domain()
            module_path = paths.get_dir_path()

            # check if there is an instance at a higher level directory
            if cls._settings_instances:
                current_path = module_path
                for instance in cls._settings_instances:
                    if instance._module_path == current_path:
                        return instance
                    # get rid of the last part of the path
                    current_path = os.path.dirname(current_path)
                    if not current_path:
                        break
            # check if there is an opening for a new instance in the current domain
            if len(cls._settings_instances) >= cls._max_instances:
                raise DprintSettingsError(
                    f"Maximum number of DprintSettings instances reached. "
                    f"Max instances: {cls._max_settings_instances}"
                )
            for instance in cls._settings_instances:
                if instance._domain == domain and domain == skdomain.SKDomain.INTERNAL:
                    raise DprintSettingsError(
                        "'suitkaise/int' can only have one DprintSettings instance. "
                        "Please use the existing instance instead."
                    )
                elif instance._domain == domain and domain == skdomain.SKDomain.EXTERNAL:
                    raise DprintSettingsError(
                        "only one DprintSettings instance can be created in the external domain. "
                        "(your imported project)"
                    )
                
            # if we aren't at the max and don't have a conflicting instance in the same domain
            # create a new instance
            instance = super().__new__(cls)
            instance._id = uuid.uuid4()
            logger_name = f"{domain.name}DprintSettings"
            instance._logger = logging.getLogger(logger_name)
            instance._module_path = module_path
            instance._domain = domain
            instance._initialized = False
            cls._settings_instances.append(instance)
        return instance
    
    
    def __init__(self):
        if getattr(self, "_initialized", True):
            return
        
        # instance specific lock
        self._dprint_settings_lock = threading.RLock()
        
        # otherwise, initialize the instance
        # get the default settings from the registry
        self._registry = DprintSettingsRegistry.get_instance()
        default_settings = self._registry.get_default_settings(self._domain)
        if default_settings is None:
            raise DprintSettingsError(
                f"No default settings found for domain {self._domain}"
            )

        # overall settings
        self._print_to_console = default_settings.get("print_to_console", True)
        self._valid_print_levels = default_settings.get("valid_print_levels", [])
        self._current_print_level = self._get_median_print_level()


        # tags that Dprints can use to be filtered further
        self._valid_tags = default_settings.get("valid_tags", [])
        self._tags_to_include = default_settings.get("tags_to_include", [])


        self._all_dirs, self._all_files = self._get_all_dirs_and_files(
            self._module_path, subdirs=True)
        
        self._files_to_include = self._all_files.copy()

        self._should_log = default_settings.get("should_log", False)
        self._valid_log_levels = default_settings.get("valid_log_levels", [])

        # automatically add newlines to printed statements
        self._auto_add_newlines = default_settings.get("auto_add_newlines", True)

        # shorten statements in UI display to fit to one line
        # ex. "this is a long statement that will be shortened" -> "this is a long..."
        self._use_shortened_previews = default_settings.get("use_shortened_previews", True)

        # automatically add time
        self._auto_add_timestamp = default_settings.get("auto_add_timestamp", True)
        self._timestamp_format = default_settings.get("timestamp_format", sktime.CustomTime.YMD_HMS6)
        self._auto_add_time_since_start = default_settings.get("auto_add_time_since_start", True)
        self._time_diff_format = default_settings.get("time_diff_format", sktime.CustomTimeDiff.HMS6)

        # automatically add the file name to the printed statement
        self._auto_add_file_name = default_settings.get("auto_add_file_name", True)

        # set the initialized flag to True
        self._initialized = True

    
    @classmethod
    def get_instance(cls) -> 'DprintSettings':
        """
        Get the most appropriate instance of DprintSettings.

        Find the closest level instance of DprintSettings to the current module,
        ensuring that it is in the same domain.

        """
        with cls._dprint_settings_creation_lock:
            domain = skdomain.get_domain()
            module_path = paths.get_file_path_of_caller()

            # check if there is an instance at a higher level directory
            for instance in cls._settings_instances:
                if instance._module_path == module_path:
                    if instance._domain == domain:
                        return instance
                # get rid of the last part of the path
                module_path = os.path.dirname(module_path)
                if not module_path:
                    break

            # if no instance was found, raise an error
            raise DprintSettingsError(
                f"No DprintSettings instance found for domain {domain} at path {module_path}"
            )


    def get_lock(self) -> threading.RLock:
        """
        Get the lock for this DprintSettings instance.

        """
        return self._dprint_settings_lock


    def _get_median_print_level(self) -> int:
        """
        Get the median print level from the valid print levels.

        """
        if not self._valid_print_levels:
            raise DprintSettingsError(
                "No valid print levels found. Please set valid print levels."
            )
        
        # return the median print level
        return sorted(self._valid_print_levels)[len(self._valid_print_levels) // 2]
    
    def _get_lowest_level(self) -> int:
        """
        Get the lowest print level from the valid print levels.

        """
        if not self._valid_print_levels:
            raise DprintSettingsError(
                "No valid print levels found. Please set valid print levels."
            )
        
        # return the lowest print level
        return min(self._valid_print_levels)
    
    def _get_all_dirs_and_files(self,
                                dir_path) -> Tuple[List[str], List[str]]:
        """
        Get all directories and files at or below this
        DprintSettings instance's module path.

        Args:
            dir_path (str): The path to the directory to search.

        Returns:
            Tuple[List[str], List[str]]: A tuple containing a list of directories
            and a list of files.
        
        """
        from suitkaise.int.utils.path.get_paths import get_dirs_and_files_from_path

        # get the directories and files from the module path
        dirs, files = get_dirs_and_files_from_path(dir_path, subdirs=True)

        return dirs, files

    def set_print_to_console(self, value: bool) -> None:
        """
        Set whether to print to console.

        Args:
            value (bool): True to print to console, False otherwise.
        
        """
        with self._dprint_settings_lock:
            self._print_to_console = value


    def add_print_level(self, level: int) -> None:
        """
        Add a print level to the valid print levels.

        Args:
            level (int): The print level to add.
        
        """
        if level not in self._valid_print_levels:
            with self._dprint_settings_lock:
                self._valid_print_levels.append(level)
                self._valid_print_levels.sort()


    def remove_print_level(self, level: int) -> None:
        """
        Remove a print level from the valid print levels.

        Args:
            level (int): The print level to remove.
        
        """
        with self._dprint_settings_lock:
            if level in self._valid_print_levels:
                self._valid_print_levels.remove(level)
                self._valid_print_levels.sort()


    def set_default_print_level(self, level: int) -> None:
        """
        Set the default print level.

        Args:
            level (int): The print level to set as default.
        
        """
        with self._dprint_settings_lock:
            if level in self._valid_print_levels:
                self._current_print_level = level
            else:
                raise DprintSettingsError(
                    f"Invalid print level {level}. Valid levels are {self._valid_print_levels}"
                )

    def register_new_tag(self, 
                         tag_name: str,
                         tag_description: str,
                         tag_color: str) -> None:
        """
        Register a new tag for this DprintSettings instance.

        Args:
            tag_name (str): The name of the tag.
            tag_description (str): The description of the tag.
            tag_color (str): The color of the tag.

        """
        if tag_name in self._valid_tags:
            raise DprintSettingsError(
                f"Tag {tag_name} already exists. Please use a different name."
            )
        
        if not tag_name:
            raise DprintSettingsError(
                "Tag name cannot be empty."
            )
        if not tag_description:
            tag_description = "not provided"
            print(f"Warning: Description for tag {tag_name} not provided.")

        if not tag_color:
            # default to light gray
            tag_color = "#D3D3D3"
        
        tag_name = {
            "name": tag_name,
            "description": tag_description,
            "color": tag_color
        }
        with self._dprint_settings_lock:
            self._valid_tags.append(tag_name)
            self._tags_to_include.append(tag_name["name"])

        print(f"Tag {tag_name['name']} registered successfully.")

    def deregister_tag(self, tag_name: str) -> None:
        """
        Remove a tag from this DprintSettings instance.

        Args:
            tag_name (str): The name of the tag to remove.
        
        """
        if tag_name not in self._valid_tags:
            raise DprintSettingsError(
                f"Cannot deregister tag {tag_name} because it does not exist."
            )
        
        with self._dprint_settings_lock:
            self._valid_tags.remove(tag_name)
            if tag_name in self._tags_to_include:
                self._tags_to_include.remove(tag_name)

        print(f"Tag {tag_name} deregistered successfully.")
        

    def exclude_tag(self, tag_name: str) -> None:
        """
        Stop printing Dprints with a specific tag.

        Args:
            tag_name (str): The name of the tag to stop printing.
        
        """
        if tag_name not in self._tags_to_include:
            raise DprintSettingsError(
                f"Tag {tag_name} is not being printed. Cannot stop printing."
            )
        
        with self._dprint_settings_lock:
            self._tags_to_include.remove(tag_name)

    def include_tag(self, tag_name: str) -> None:
        """
        Start printing Dprints with a specific tag.

        Args:
            tag_name (str): The name of the tag to start printing.
        
        """
        if tag_name in self._tags_to_include:
            raise DprintSettingsError(
                f"Tag {tag_name} is already being printed."
            )
        
        with self._dprint_settings_lock:
            self._tags_to_include.append(tag_name)

    
    def exclude_dir(self, dir_path: str,
                    subdirs: bool = False) -> None:
        """
        Stop printing Dprints from a specific directory's files,
        and optionally any subdirectories' files.

        Args:
            dir_path (str): The path of the directory to stop printing.
        
        """
        # normalize the path
        dir_path = os.path.normpath(dir_path)

        if dir_path not in self._all_dirs:
            raise DprintSettingsError(
                f"Directory {dir_path} is not in the list of directories."
            )
        
        dirs, files = self._get_all_dirs_and_files(dir_path, subdirs=subdirs)
        with self._dprint_settings_lock:
            for file in files:
                if file in self._files_to_include:
                    self._files_to_include.remove(file)

        print(f"Directory {dir_path} excluded successfully.")
        

    def exclude_file(self, file_path: str) -> None:
        """
        Stop printing Dprints from a specific file.

        Args:
            file_path (str): The name of the file to stop printing.
        
        """
        # normalize the path
        file_path = os.path.normpath(file_path)

        if file_path not in self._all_files:
            raise DprintSettingsError(
                f"File {file_path} is not in the list of files."
            )
        
        with self._dprint_settings_lock:
            if file_path in self._files_to_include:
                self._files_to_include.remove(file_path)

        print(f"File {file_path} excluded successfully.")


    def include_dir(self, dir_path: str,
                    subdirs: bool = False) -> None:
        """
        Start printing Dprints from a specific directory, its files,
        and any subdirectories and their files.

        Args:
            dir_path (str): The path of the directory to start printing.
        
        """
        # normalize the path
        dir_path = os.path.normpath(dir_path)

        if dir_path not in self._all_dirs:
            raise DprintSettingsError(
                f"Directory {dir_path} is not in the list of directories."
            )
        
        dirs, files = self._get_all_dirs_and_files(dir_path, subdirs=subdirs)
        with self._dprint_settings_lock:
            for file in files:
                if file not in self._files_to_include:
                    self._files_to_include.append(file)

        print(f"Directory {dir_path} included successfully.")


    def include_file(self, file_path: str) -> None:
        """
        Start printing Dprints from a specific file again.

        Args:
            file_path (str): The name of the file to start printing.
        
        """
        # normalize the path
        file_path = os.path.normpath(file_path)

        if file_path not in self._all_files:
            raise DprintSettingsError(
                f"File {file_path} is not in the list of files."
            )
        
        with self._dprint_settings_lock:
            if file_path not in self._files_to_include:
                self._files_to_include.append(file_path)

        print(f"File {file_path} included successfully.")

    
    def set_should_log(self, value: bool) -> None:
        """
        Set whether to log Dprints.

        Args:
            value (bool): True to log Dprints, False otherwise.
        
        """
        with self._dprint_settings_lock:
            self._should_log = value


    def set_auto_add_newlines(self, value: bool) -> None:
        """
        Set whether to automatically add newlines to printed statements.

        Args:
            value (bool): True to automatically add newlines, False otherwise.
        
        """
        with self._dprint_settings_lock:
            self._auto_add_newlines = value


    def set_use_shortened_previews(self, value: bool) -> None:
        """
        Set whether to use shortened previews for printed statements.

        Args:
            value (bool): True to use shortened previews, False otherwise.
        
        """
        with self._dprint_settings_lock:
            self._use_shortened_previews = value

    def set_auto_add_timestamp(self, value: bool, 
                               format: sktime.CustomTime = sktime.CustomTime.YMD_HMS6
                               ) -> None:
        """
        Set whether to automatically add a timestamp to printed statements,
        and the format of the timestamp.

        For a full list of formats, see the sktime.CustomTime enum.

        Args:
            value (bool): True to automatically add a timestamp, False otherwise.
            format (sktime.CustomTime): The format of the timestamp.

        """
        with self._dprint_settings_lock:
            self._auto_add_timestamp = value
            if isinstance(format, sktime.CustomTime):
                self._timestamp_format = format
            else:
                self._timestamp_format = sktime.CustomTime.YMD_HMS6

        
    def set_auto_add_time_since_start(self, value: bool,
                                      format: sktime.CustomTimeDiff = sktime.CustomTimeDiff.HMS6
                                      ) -> None:
        """
        Set whether to automatically add the time since the program started
        to printed statements, and the format of the time difference.

        For a full list of formats, see the sktime.CustomTimeDiff enum.

        Args:
            value (bool): True to automatically add the time since the program started,
                False otherwise.
            format (sktime.CustomTimeDiff): The format of the time difference.

        """
        with self._dprint_settings_lock:
            self._auto_add_time_since_start = value
            if isinstance(format, sktime.CustomTimeDiff):
                self._time_diff_format = format
            else:
                self._time_diff_format = sktime.CustomTimeDiff.HMS6


    def set_auto_add_file_name(self, value: bool) -> None:
        """
        Set whether to automatically add the file name to printed statements.

        Args:
            value (bool): True to automatically add the file name, False otherwise.
        
        """
        with self._dprint_settings_lock:
            self._auto_add_file_name = value


        
