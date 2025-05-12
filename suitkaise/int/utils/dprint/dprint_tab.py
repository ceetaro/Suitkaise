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

# suitkaise/int/utils/dprint/dprint_tab.py

"""
Module containing widget that provides UI to manage Dprint settings,
and displays printed Dprints with options to filter and sort them.

This tab can be added to a tab in any Devwindow, or run as a standalone window.

"""

from PyQt6.QtWidgets import (
    QWidget,
)

class DprintTab(QWidget):
    """
    Widget that provides UI to manage Dprint settings.
    This is not a main window, but rather a widget that can be added to a tab.

    """

    def __init__(self, parent=None):
        """
        Initialize the DprintTab widget, and set up the UI to adjust settings
        and display printed Dprints.
        
        """

        super().__init__(parent)
        
        # settings to add
        # - toggle printing to console
        # - see available print levels
        # - be notified when a print level is changed, added, or removed
        # - set current print level

        # - select/deselect tags to print
        # - see a list of available tags
        # - be notified when a tag is added or removed

        # - toggle logging
        # - see available log levels
        
        # - select/deselect dirs or files to print
        #   - this is done in a tree, where each directory and file is a node with a checkbox
        
        # - toggle auto adding newlines at the end of each print
        # - toggle use of shortened previews 
        #   - (one "line" in the preview vs. different size lines to accommodate the text)
        # - toggle auto adding time stamps and time since start
        # - pick formats for the time stats with example previews
        # - toggle auto adding file name to the print


        # adding a Dprint to the tab
        # - dprint needs to collect all relevant options as metadata
        # - message
        # - level
        # - tags
        # - file path
        # - log level
        # - time

        # dprint will take all dprints regardless of if they printed or not. 
 
        # sorting and filtering the Dprints
        # - filter by time
        # - filter by tag
        # - filter by level
        # - filter by file
        # - filter by directory
        # - filter by log_level







    