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

# suitkaise/int/utils/dprint/dprint.py

"""
Module containing the DPrint class for custom printing, and the DprintTagRegistry class
for managing tags.

Print to console, Devwindow, and/or a log.

Instead of using the standard print function, this module provides a DPrint class
that allows for customized printing options:

- toggle console prints on and off
- toggle level of print to show (can set level when Dprinting)
- toggle prints with tags on and off (you can add tags to the DPrint class)
- toggle prints only within a specific directory/file
- add newlines automatically to printed statements
- print in a more readable and interactable format
- auto add timestamp and time since program start

"""
import logging
import uuid
import suitkaise_app.int.utils.time.sktime as sktime
from typing import Optional, List, Dict, Any

from suitkaise_app.int.utils.dprint.dprint_settings import DprintSettings, DprintSettingsRegistry

class DprintingError(Exception):
    """Custom exception for Dprint errors."""
    pass

class DprintMessage:
    """
    Container for Dprints to send to DprintTab.
    
    """

    def __init__(self, 
                 original_message: str,
                 level: int,
                 tags: List[str],
                 file_path: str,
                 log_level: Optional[str] = None,
                 timestamp: Optional[str] = None,
                 time_since_start: Optional[str] = None):
        self.message = original_message
        self.level = level
        self.tags = tags
        self.file_path = file_path
        self.log_level = log_level
        self.timestamp = timestamp
        self.time_since_start = time_since_start
        self.id = uuid.uuid4()

class Dprint:
    """
    Class for custom printing.

    This class allows for customized printing options:
    - toggle console prints on and off
    - toggle level of print to show (can set level when Dprinting)
    - toggle prints with tags on and off (you can add tags to the DPrint class)
    - toggle prints only within a specific directory/file
    - add newlines automatically to printed statements
    - print in a more readable and interactable format
    - auto add timestamp and time since program start
    
    To apply custom printing options, edit the DprintSettings.

    """

    def __init__(self,
                 message: str = "",
                 level: Optional[int] = None,
                 log_level: Optional[str] = None,
                 tags: Optional[List[str]] = None,
                 print_to_console: Optional[bool] = None,
                 should_log: Optional[bool] = None,
                 add_newline: Optional[bool] = None,
                 add_time: Optional[bool] = None,
                 add_file_name: Optional[bool] = None) -> None:
        """
        Print a message using Dprint.

        Args:
            level (int): The level of the print message. Default is 1.
            tags (list[str]): List of tags to associate with the print message.
            print_to_console (bool): Whether to print to console. Default is None.
                If None, uses the default setting.
            should_log (bool): Whether to log the message. Default is None.
                If None, uses the default setting.
            add_newline (bool): Whether to add a newline after the message. Default is None.
                If None, uses the default setting.
            add_time (bool): Whether to add a timestamp. Default is None.
                If None, uses the default setting.
        
        """
        self.message = message
        self.original_message = message

        from suitkaise_app.int.utils.path.get_paths import get_file_path_of_caller

        self.file_path = get_file_path_of_caller()

        self.settings = DprintSettings.get_instance()
        if level is None:
            level = self.settings._current_print_level
        if self.level in self.settings._valid_print_levels:
            self.level = self.settings._get_lowest_level()
        else:
            raise DprintingError(f"Invalid print level: {level}. "
                                 f"Valid levels are: {self.settings._valid_print_levels}")
        
        if log_level is None:
            print("Warning: log_msg_type is None. Defaulting to 'info'.")
            self.log_level = "info"

        elif log_level not in self.settings._valid_log_levels:
            print(f"Warning: log_msg_type '{log_level}' is not valid. "
                  f"Defaulting to 'info'.")
            self.log_level = "info"

        else:
            self.log_level = log_level

        self.tags = tags
        invalid_tags = []
        for tag in self.tags:
            if tag not in self.settings._valid_tags:
                invalid_tags.append(tag)

        if invalid_tags:
            raise DprintingError(f"Invalid tags: {invalid_tags}. "
                                 f"Valid tags are: {self.settings._valid_tags.keys()}")
        
        self.print_to_console = print_to_console if print_to_console is not None \
                                else self.settings._print_to_console
        
        self.should_log = should_log if should_log is not None \
                          else self.settings._should_log
        
        self.add_newline = add_newline if add_newline is not None \
                           else self.settings._auto_add_newlines
        
        self.timestamp = sktime.now()
        self.time_since_start = sktime.get_time_since_start()

        if add_time is not None:
            self.add_timestamp = add_time
            self.add_time_since_start = add_time

        else:
            self.add_timestamp = self.settings._auto_add_timestamp
            self.add_time_since_start = self.settings._auto_add_time_since_start
        
        self.timestamp_format = self.settings._timestamp_format   
        self.time_diff_format = self.settings._time_diff_format  

        if add_file_name is not None:
            self.add_file_name = add_file_name
        else:
            self.add_file_name = self.settings._auto_add_file_name

        printed = self._dprint()




    def _dprint(self) -> bool:
        """
        Print a message to console, log, and or a Devwindow using the 
        specified settings and attributes.
        
        """      
        try:
            level_included = False
            if self.level >= self.settings._current_print_level:
                level_included = True

            tag_included = False
            for tag in self.tags:
                if tag in self.settings._tags_to_include:
                    tag_included = True
                    break

            file_included = False
            if self.file_path in self.settings._files_to_include:
                file_included = True

            if level_included and tag_included and file_included:
                if self.print_to_console:
                    printed = self._print_to_console()

                if self.should_log and self.log_level:
                    logged = self._log_message()

            displayed = self._print_to_dprint_tab()

            if printed and logged and displayed:
                return True
            else:
                raise DprintingError("Failed to process Dprint message.")

        except DprintingError as e:
            print(f"Error Dprinting message '{self.message}': {e}")
            return False
        

    def _print_to_console(self) -> bool:
        """
        Print the message to the console.
        
        """
        try:
            if self.add_file_name:
                # get last part of the file path
                file_name = self.file_path.split("/")[-1]
                # add file name to start of message
                self.message = f"{file_name} -- " + self.message

            if self.add_timestamp:
                fmted_ts = sktime.to_custom_time_format(self.timestamp, self.timestamp_format)
                fmted_td = sktime.to_custom_time_diff_format(self.time_since_start, self.time_diff_format)
                if self.message.endswith("\n"):
                    self.message = self.message + f"- {fmted_ts}\n"
                else:
                    self.message = self.message + f"\n- {fmted_ts}\n"
                self.message += f"- Time since start: {fmted_td}\n"
                
            if self.add_newline and not self.message.endswith("\n"):
                self.message += "\n"

            print(self.message)
        except DprintingError as e:
            print(f"Error printing message '{self.message}': {e}")
            return False
        return True

    def _log_message(self) -> bool:
        """
        Log the message.
        
        """
        try:
            logger = logging.getLogger(self.file_path)
            if not logger:
                logger = self.settings._logger

            if not logger:
                raise DprintingError("Logger not found.")

            if self.log_level == "info":
                message = f"Info: {self.message}"
                logger.info(message)
            elif self.log_level == "debug":
                message = f"Debug: {self.message}"
                logger.debug(message)
            elif self.log_level == "warning":
                message = f"WARNING: {self.message}"
                logger.warning(message)
            elif self.log_level == "error":
                message = f"ERROR: {self.message}"
                logger.error(message)
            elif self.log_level == "critical":
                message = f"CRITICAL!!!\n{self.message}\nEND CRITICAL\n"
                logger.critical(message)
            else:
                raise DprintingError(f"Invalid log level: {self.log_level}. "
                                     f"Valid levels are: {self.settings._valid_log_levels}")
            
        except DprintingError as e:
            print(f"Error logging message '{self.message}': {e}")
            return False
        return True
    
    def _print_to_dprint_tab(self) -> bool:
        """
        Print the message to the Dprint tab,
        by converting the DPrint into a DprintMessage.
        
        """
        try:
            from suitkaise_app.int.utils.dprint.dprint_tab import DprintTab
            message = DprintMessage(
                self.original_message,
                self.level,
                self.tags,
                self.file_path,
                self.log_level,
                self.timestamp,
                self.time_since_start
            )

            # returns the active tab instance linked to same settings or creates one 
            dprint_tab = DprintTab.get_active_tab(self.settings._id)
            if not dprint_tab:
                raise DprintingError("DprintTab not found.")
            
            dprint_tab.message_received.emit(message)
            return True
        
        except DprintingError as e:
            print(f"Error sending message '{self.message}' to Dprint tab: {e}")
            return False
        


        

        
            


        
            
            

        
        
        



        

        

        

            


