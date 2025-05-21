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

import os
from typing import List, Dict, Any, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QLabel, QCheckBox, QComboBox, QSpinBox, 
    QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QScrollArea, QTreeWidget, QTreeWidgetItem,
    QSplitter, QLineEdit, QTextEdit, QSlider, QCompleter,
    QFrame, QStackedWidget, QToolButton, QMenu, QDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QBrush, QFont

from suitkaise_app.int.utils.dprint.dprint_settings import DprintSettings, DprintSettingsError
import suitkaise_app.int.utils.time.sktime as sktime
import suitkaise_app.int.utils.domain.skdomain as skdomain

class DprintTabError(Exception):
    """Custom error for DPrintTab."""
    pass

class MessageListItem(QWidget):
    pass
    # expanded: bool

class DprintTab(QFrame):
    """
    Widget that provides UI to manage Dprint settings.
    This is not a main window, but rather a widget that can be added to a tab.

    """
    from suitkaise_app.int.utils.dprint.dprint import DprintMessage
    message_received = pyqtSignal(DprintMessage)

    def __init__(self, parent=None):
        """
        Initialize the DprintTab widget, and set up the UI to adjust settings
        and display printed Dprints.
        
        """
        super().__init__(parent)

        try:
            # try to get settings
            self.settings = DprintSettings.get_instance()
            if not self.settings:
                raise DprintTabError("DprintSettings instance not found.")
        except DprintSettingsError as e:
            raise DprintTabError(f"DprintSettings error: {e}")

        self.messages = [] # list of DprintMessage objects
        self.filtered_messages = [] # list of filtered DprintMessage objects

        self.init_ui()

        # connect signal to slot
        self.message_received.connect(self.add_message)

        # create a timer to update the messages display
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_messages_display)
        self.update_timer.start(1000)


    def init_ui(self):
        """Initialize UI components for the DprintTab widget."""

        # main layout
        self.main_widget = QWidget(self)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_widget.setLayout(self.main_layout)

        # create a vertical splitter between the message display and the settings
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_layout.addWidget(self.main_splitter)

        # create the left panel for messages and filters
        self.init_left_panel(self.main_splitter)

    def init_left_panel(self):
        """
        Initialize the left panel of the DprintTab widget.

        This panel contains 2 parts:
        1. A header with a filter button (opens a dialog) and search bar.
        2. A scroll area with a list of messages and their details.

        Filters in the header include:
        - Filter by time, has a toggle with newest/oldest
          - also has a submenu that has an option to filter only in certain time range
            - opens a generated timeline that allows the user to:
            - enter timestamps manually
            - move the start point or end point incrementally across the timeline
            - search for or paste a "message" in the start time or end time
              - timestamp of message will be used as the start or end point

        - Filter by tags
          - opens a dialog that displays tags in a 'inf' row, 5 column format
            where each tag populates one cell
          - clicking on the tag will select it
          - can search for the tag to select it
          - can select multiple tags
          - select and deselect all options
          - click and drag to select multiple tags
        
        - Filter by level
          - opens a submenu that shows a min and max level
            - if a level that is not in the range is selected,
              it will default to the min or max level
        
        - Filter by file/directory
            - opens a tree that allows you to select/deselect parts of 
              file structure that this DprintTab is responsible for
              - can select/deselect all
              - can select/deselect all in a directory

        - Filter by log level
            - opens a submenu that shows all 5 log levels
              - just select/deselect the levels there

        Search bar:
        - searches operate on the original message before it got 
          formatted and printed in Dprint
        - search for words in a message, file name, directory name,
          tag, level, or log level
        - can search words and phrases and messages will be filtered
          out if they don't match the search
        - if a file name matches the search, it will be brought to the top
          of the list of messages, with a little indicator saying that
          "this isnt a word match, but a file name match" that will filter
          by file name like the filter dropdown. same for directory name
        - can search for a tag, level, or log level. same concept as above
        - time searching will not work here

        Message display:
        - scroll area that displays all messages, with the most recent
          messages at the top
        - message list might change depending on current filters
        - each message has a little box, that when hovered, will
          display the message's own metadata, that you can use to 
          filter without having to open the dropdown
        - each message will only show one line's worth of text,
          and if all text does not fit on one line, then you can expand
          the message to see all of it
        - if filters are in place, then the active filters will show directly
          next to the actual message, without having to hover over it
        
        
        """

        # == LEFT PANEL: Messages, Filters, and search bar ==
        self.left_panel = QFrame()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_panel.setLayout(self.left_layout)
        # add the left panel to the left side of the splitter
        self.main_splitter.addWidget(self.left_panel)

        self.init_left_panel_header(self.left_layout)

    def init_left_panel_header(self):
        """
        Initialize the header of the left panel of the DprintTab widget.
        This header contains a filter dropdown and a search bar.

        """

        # create the header with filter dropdown and search bar
        self.header_frame = QFrame()
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_frame.setLayout(self.header_layout)

        # add to parent, left layout
        self.left_layout.addWidget(self.header_frame)

        # create filter button and dialog
        self.init_left_panel_filter_system()

    def init_left_panel_filter_system(self):
        """
        Initialize the filter system in the header of the left panel.
        This dropdown allows the user to filter messages by time, tags, level,
        file/directory, and log level.

        """
        # NOTE: add a filter icon and "filter by..." 
        # to the filter button

        # create filter button
        self.filter_button = QPushButton()

        self.filter_button.clicked.connect(self.toggle_filter_dialog)

        # add the filter button to the header layout
        self.header_layout.addWidget(self.filter_button)

    

class FilterDialog(QDialog):
    """
    Dialog for filtering messages in the DprintTab widget.

    This dialog allows the user to filter messages by time, tags, level,
    file/directory, and log level.

    Can be toggled on and off by clicking the filter button in the header,
    and therefore tracks its current state (open or closed).

    """


    def __init__(self, parent=None, settings=None, messages=None):
        """Initialize the filter dialog."""

        super().__init__(parent)

        self.setWindowTitle(f"Dprint -- Filter Messages")
        self.setMinimumSize(680, 680)

        self.settings = settings
        if not self.settings:
            raise DprintTabError("DprintSettings instance not found.")
        self.messages = messages or []
    
        self.filter_state = {
            "time": {
                "sort_from": "newest",
                "from_time": None,
                "to_time": None,
            },
            "tags": {
                "selected_tags": [],
            },
            "level": {
                "min_level": None,
                "max_level": None,
            },
            "log_level": {
                "selected_levels": [],
            },
            "file": {
                "selected_files": [],
            }
        }

        # create the filter options
        self.init_filter_dialog_ui()

    
    def init_filter_dialog_ui(self):
        """
        Init the filter options as outlined in init_left_panel.

        This includes:
        - Filter by time
        - Filter by tags
        - Filter by level
        - Filter by file/directory
        - Filter by log level
        
        """
        # create main layout
        self.main_layout = QVBoxLayout(self)


        # create a custom tab widget for the filter options
        self.filter_tab_widget = QTabWidget()
        self.filter_tab_widget.setTabsClosable(False)
        self.filter_tab_widget.setMovable(False)

        # create tabs
        self.time_tab = self.create_time_tab()
        self.tags_tab = self.create_tags_tab()
        self.levels_tab = self.create_levels_tab()
        self.file_tab = self.create_file_tab()

        # add tabs to the tab widget
        self.filter_tab_widget.addTab(self.time_tab, "Time")
        self.filter_tab_widget.addTab(self.tags_tab, "Tags")
        self.filter_tab_widget.addTab(self.levels_tab, "Levels")
        self.filter_tab_widget.addTab(self.file_tab, "File")

        # add the tab widget to the main layout
        self.main_layout.addWidget(self.filter_tab_widget)

        # add buttons to the bottom of the dialog
        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_changes)
        self.button_layout.addWidget(self.apply_button)

        self.cancel_button = QPushButton("Revert")
        self.cancel_button.clicked.connect(self.revert_changes)
        self.button_layout.addWidget(self.cancel_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close_filter_dialog)
        self.button_layout.addWidget(self.close_button)

        # add the button layout to the main layout
        self.main_layout.addLayout(self.button_layout)


    def create_time_tab(self):
        """
        Create the time filter tab.
        This tab allows the user to filter messages by time.

        """
        # create the time tab
        self.time_tab = QWidget()
        self.time_tab_layout = QVBoxLayout(self.time_tab)

        # input are for From and To fields
        self.input_frame = QFrame()
        self.input_layout = QHBoxLayout(self.input_frame)
        self.time_tab_layout.addWidget(self.input_frame)

        # toggle for sorting by newest or oldest
        

        # from section
        self.from_section = QHBoxLayout()
        self.from_label = QLabel("From")
        self.from_section.addWidget(self.from_label)

        self.from_paste_button = QPushButton("Paste") # NOTE: change to clipboard icon
        self.from_paste_button.setToolTip("Paste a copied messsage, and use its time")
        self.from_paste_button.clicked.connect(self.paste_time_format(clicked="from"))
        self.from_section.addWidget(self.from_paste_button)

        self.from_input_time_button = QPushButton("Enter Time") # NOTE: change to clock icon
        self.from_input_time_button.setToolTip("Enter a time")
        self.from_input_time_button.clicked.connect(self.open_input_time_popup(clicked="from"))
        self.from_section.addWidget(self.from_input_time_button)


        self.from_search_for_time_button = QPushButton("Search") # NOTE: change to search icon
        self.from_search_for_time_button.setToolTip("Search for a message to use its time")
        self.from_search_for_time_button.clicked.connect(self.open_search_for_time_popup(clicked="from"))
        self.from_section.addWidget(self.from_search_for_time_button)

        self.input_layout.addLayout(self.from_section)

        # to section
        self.to_section = QHBoxLayout(self.to_section)
        self.to_label = QLabel("To")
        self.to_section.addWidget(self.to_label)

        self.to_paste_button = QPushButton("Paste")
        self.to_paste_button.setToolTip("Paste a copied messsage, and use its time")
        self.to_paste_button.clicked.connect(self.paste_time_format(clicked="to"))
        self.to_section.addWidget(self.to_paste_button)

        self.to_input_time_button = QPushButton("Enter Time")
        self.to_input_time_button.setToolTip("Enter a time")
        self.to_input_time_button.clicked.connect(self.open_input_time_popup(clicked="to"))
        self.to_section.addWidget(self.to_input_time_button)

        self.to_search_for_time_button = QPushButton("Search")
        self.to_search_for_time_button.setToolTip("Search for a message to use its time")
        self.to_search_for_time_button.clicked.connect(self.open_search_for_time_popup(clicked="to"))
        self.to_section.addWidget(self.to_search_for_time_button)

        self.input_layout.addLayout(self.to_section)

        # create timeline
        self.create_time_tab_timeline()

    def create_time_tab_timeline(self):
        """Create the timeline for the time filter tab."""
        # create the timeline
        self.timeline_frame = QFrame()
        self.timeline_layout = QVBoxLayout(self.timeline_frame)
        self.timeline = PrecisionSlider #... implement correctly

        self.timeline_bottom_part = QFrame()
        self.timeline_bottom_layout = QHBoxLayout(self.timeline_bottom_part)

        # this is where we show from what message to what message
        # we might add more, so i split the layout into two parts


    # def paste_time_format(self, clicked):
    # def open_input_time_popup(self, clicked):
    # def open_search_for_time_popup(self, clicked):

    def create_tags_tab(self):
        



























class PrecisionSlider(QSlider):
    """A custom slider that provides more precise control for fine adjustments."""
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        
        # Set smaller page step for finer control when clicking on the track
        self.setPageStep(5)
        
        # Add properties to reduce jitter
        self._last_value = 0
        self._update_threshold = 1  # Only update when change is >= this amount
        
        # Same styling as before
        self.setStyleSheet("""
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;  /* Larger handle is easier to control */
                height: 18px;
                margin: -9px 0;
                border-radius: 9px;
            }
            QSlider::groove:horizontal {
                background: #d6d6d6;
                height: 6px;  /* Slightly thicker groove */
                border-radius: 3px;
            }
        """)
    
    def mousePressEvent(self, event):
        """Override to implement smoother clicking behavior."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate position with better precision
            val = self._pixelPosToRangeValue(event.position().x())
            # Only update if the change is significant
            if abs(val - self.value()) >= self._update_threshold:
                self._last_value = val
                self.setValue(val)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def _pixelPosToRangeValue(self, pos):
        """Convert pixel position to slider value with better precision."""
        # Create a style option for the slider
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        
        # Get the slider's style object
        style = self.style()
        
        # Get the slider groove and handle rectangles
        if style is None:
            raise RuntimeError("Style object is None. Ensure the widget is properly initialized.")
        groove_rect = style.subControlRect(QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderGroove, self)
        handle_rect = style.subControlRect(QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderHandle, self)
        
        # Calculate the slider length and range
        slider_length = groove_rect.width()
        slider_min = self.minimum()
        slider_max = self.maximum()
        
        # Calculate the position adjusted for handle width
        handle_width = handle_rect.width()
        available_space = slider_length - handle_width
        
        # Calculate the relative position (0.0 to 1.0)
        if available_space > 0:
            # Adjust for handle position and constrain within valid range
            adjusted_pos = max(0, min(pos - groove_rect.x() - handle_width / 2, available_space))
            pos_ratio = adjusted_pos / available_space
            return int(slider_min + pos_ratio * (slider_max - slider_min))
        
        return slider_min

    def mouseMoveEvent(self, event):
        """Override to implement dragging behavior with less jitter."""
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Calculate position with better precision
            val = self._pixelPosToRangeValue(event.position().x())
            # Only update if the change is significant
            if abs(val - self._last_value) >= self._update_threshold:
                self._last_value = val
                self.setValue(val)
            event.accept()
        else:
            super().mouseMoveEvent(event)
















        





        

        



        # NOTE: add items to the filter dropdown

        
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







    