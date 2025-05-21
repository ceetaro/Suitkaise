# -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0 or the GNU General Public License, Version 3.
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

# suitkaise/scan.py

"""
Placeholder scanning script to copy file structures and contents to the clipboard.

This script provides a graphical interface for scanning and displaying 
directory structures, allowing users to copy the structure and contents of files
to the clipboard. It uses PyQt6 for the GUI and pyperclip for clipboard operations.

Main use: external documentation

Run this script directly until a more permanent solution is implemented in 
the internal developer window.

"""

import os
import sys
from pathlib import Path
from functools import partial
import pyperclip

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QPushButton, QListWidget,
    QCompleter, 
)

from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPoint, QStringListModel
)

# permissions: scan.py can read all files in the project, and their contents. it cannot
# write to any files, and cannot execute any files.

class DirectoryScanner(QMainWindow):
    """
    A graphical interface for scanning and displaying directory structures.
    This class creates a window with a tree view of directories that can be
    clicked to copy their structure to the clipboard.
    """
    def __init__(self):
        super().__init__()

        self.DEBUG = True

        self.version = "suitkaise"

        self.in_results = False
        self.DEFAULT_SEARCH_DELAY = 300
        
        self.setup_window() # set up the main window
        self.setup_search() # set up internal search logic
        self.setup_connections() # set up signal-slot connections
        
        self.current_selection = None

        self.root = self.find_project_root() # find the project root directory
        self.populate_tree() # create the tree view
        self.expand_to_App() # expand the tree to show the App directory


    def setup_window(self):
        """Sets up the user interface for the application."""
        self.create_window()
        self.create_main_widget()
        self.create_tree_box()
        self.create_button_sidebar()
        self.create_copy_bar()
        self.create_main_layout()


    def debug_log(self, source, message):
        """Helper to track what's happening in our search logic"""
        if self.DEBUG:
            print(f"[{source}] {message}")


    def setup_search(self):
        """Sets up the search bar and results dropdown."""
        self.create_search_paths()
        self.setup_search()


    def create_window(self):
        # Set the window properties
        self.setWindowTitle("Directory Scanner")
        self.setGeometry(100, 100, 800, 600) # x, y, width, height


    def create_main_widget(self):
        # create the main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)


    def create_tree_box(self):
        # Create the main directory tree widget
        self.tree_box = QWidget()
        
        self.create_tree()
        self.create_tree_search()
        self.create_tree_layout()


    def create_tree(self):
        self.tree = QTreeWidget() # create the tree widget
        self.tree.setHeaderHidden(True)


    def create_tree_search(self):
        """
        Creates a search bar with completion suggestions using QCompleter.
        The search bar starts with an empty completer, which gets updated
        when the tree is populated with paths.
        """
        # Main container for search bar
        self.tree_search = QWidget()

        # Create search bar input
        self.tree_search_input = QLineEdit() 
        self.tree_search_input.setPlaceholderText("Search Project Structure...")

        # Create an empty completer initially
        # We'll update its model when paths are available
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.tree_search_input.setCompleter(self.completer)

        # Layout for search bar
        self.tree_search_layout = QVBoxLayout(self.tree_search)
        self.tree_search_layout.addWidget(self.tree_search_input)

    def update_completer(self):
        """
        Updates the completer's suggestions with the current paths.
        This should be called whenever the search_paths dictionary is updated.
        """
        if hasattr(self, 'completer'):  # Make sure completer exists
            path_list = list(self.search_paths.keys())
            self.completer.setModel(QStringListModel(path_list))
        

    def create_tree_layout(self):
    # create a layout for the tree widget
        self.tree_layout = QVBoxLayout(self.tree_box)

    # add the search bar and tree to the layout
        self.tree_layout.addWidget(self.tree_search)
        self.tree_layout.addWidget(self.tree)


    def create_search_paths(self):
    # store directory paths on launch for quicker searching
        self.search_paths = {}


    def create_button_sidebar(self):
    # create a button container and its layout
        self.button_sidebar = QWidget()

        self.create_expand_collapse_buttons()
        self.create_sidebar_layout()


    def create_copy_bar(self):
    # create a container for the copy buttons
        self.copy_bar = QWidget()

        self.create_copy_buttons()
        self.create_copy_layout()


    def create_expand_collapse_buttons(self):
    # create expand/collapse buttons
        self.btn_expand_one = QPushButton("+ 1")
        self.btn_collapse_one = QPushButton("- 1")
        self.btn_expand_all = QPushButton("+ All")
        self.btn_collapse_all = QPushButton("- All")


    def create_copy_buttons(self):
    # create copy buttons
        self.btn_copy_selected = QPushButton("Copy Selected")
        self.btn_copy_selected.setEnabled(False)  # start disabled

        self.btn_copy_contents = QPushButton("Copy File Contents")
        self.btn_copy_contents.setEnabled(False)  # start disabled

        self.btn_copy_all = QPushButton("Copy All")


    def create_sidebar_layout(self):
        self.sidebar_layout = QVBoxLayout(self.button_sidebar)

    # create layouts for expand/collapse buttons
        one_layout = QHBoxLayout()
        one_layout.addWidget(self.btn_expand_one)
        one_layout.addWidget(self.btn_collapse_one)

        all_layout = QHBoxLayout()
        all_layout.addWidget(self.btn_expand_all)
        all_layout.addWidget(self.btn_collapse_all)

    # add the layouts to the button container
        self.sidebar_layout.addLayout(one_layout)
        self.sidebar_layout.addLayout(all_layout)

    
    def create_copy_layout(self):
        self.copy_layout = QHBoxLayout(self.copy_bar)

    # create layout for copy buttons
        self.copy_layout.addWidget(self.btn_copy_all)        
        self.copy_layout.addWidget(self.btn_copy_selected)
        self.copy_layout.addWidget(self.btn_copy_contents)

    # align the copy buttons to the right
        self.copy_layout.addStretch(1)


    def create_main_layout(self):
    # create specialized layout structure
        self.main_layout = QVBoxLayout(self.main_widget)

        horizontal1 = QHBoxLayout()
        horizontal1.addWidget(self.tree_box)
        horizontal1.addWidget(self.button_sidebar)

        horizontal2 = QHBoxLayout()
        horizontal2.addWidget(self.copy_bar)

        # add the layouts to the main layout
        self.main_layout.addLayout(horizontal1)
        self.main_layout.addLayout(horizontal2)


    def find_project_root(self):
        """
        Searches for the project root directory by looking for marker files.
        
        This method starts from the current directory and moves upward until it finds
        these files and directories:
        - LICENSE.APACHE
        - LICENSE.GPL
        - README.md
        - pyproject.toml
        - __init__.py
        - suitkaise/
        - tests/
        - docs/
        - data/
        
        Returns:
            Path: A pathlib.Path object pointing to the project root directory
        
        Example:
            If run from /home/user/projects/Suitkaise/Setup/some_file.py
            It will return /home/user/projects/Suitkaise
        """
        # Start from the current directory where the script is running
        currentpath = Path.cwd()

        while True: # Loops until a break or return statement is reached
            files_to_check = [
                'README.md',
                '__init__.py',
                'LICENSE.APACHE',
                'LICENSE.GPL',
                'pyproject.toml',
            ]
            subdirs_to_check = [
                'suitkaise',
                'tests',
                'docs',
                'data',
            ]

            is_root = True
            for file in files_to_check:
                if not (currentpath / file).exists():
                    is_root = False
                    break

            for subdir in subdirs_to_check:
                if not (currentpath / subdir).exists():
                    is_root = False
                    break

            if is_root:
                print(f"Found project root: {currentpath}")
                return currentpath
            
            
            # Double check if the current path is the root
            # but files havent been found
            if currentpath.parent == currentpath:
                print("Warning: Could not find project root with the expected files.")
                return Path.cwd()
            
            # Move up one directory
            currentpath = currentpath.parent


    def populate_tree(self):
        """
        Creates an interactive tree view of the project's directory structure.
        
        This method starts from the project root, creates the SK folder as the main
        container, and then recursively builds the visual tree structure beneath it.
        Each directory becomes a clickable item that, when selected, will copy its
        structure to the clipboard.
        """
        self.tree.clear()
        self.search_paths.clear()

        # Create the root item (Suitkaise)
        root_item = QTreeWidgetItem(self.tree)
        root_item.setText(0, self.root.name)
        root_item.setData(0, Qt.ItemDataRole.UserRole, str(self.root))

        # Add files directly under the root (excluding directories and hidden files)
        try:
            root_files = sorted([
                item for item in self.root.iterdir()
                if item.is_file() and not item.name.startswith('.')
            ], key=lambda x: x.name.lower())
            
            for file_path in root_files:
                file_item = QTreeWidgetItem(root_item)
                file_item.setText(0, file_path.name)
                file_item.setData(0, Qt.ItemDataRole.UserRole, str(file_path))
        except Exception as e:
            print(f"Warning: Error processing root files: {e}")

        # Create the SK folder item
        sk_item = QTreeWidgetItem(root_item)
        sk_item.setText(0, self.version)
        sk_path = self.root / self.version
        sk_item.setData(0, Qt.ItemDataRole.UserRole, str(sk_path))

        # Add directories under SK
        self.add_directory(sk_path, sk_item)

        # Store paths for searching
        self.store_path(root_item)
        
        # Update completer with new paths
        self.update_completer()

        # Connect click handler
        self.tree.itemClicked.connect(self.handle_item_click)


    def store_path(self, item: QTreeWidgetItem, parent_path=""):
        """
        Stores a single item's path and the item itself in our search_paths dictionary.
        Uses the path as the key and the item as the value.
        """
        current_path = f"{parent_path}/{item.text(0)}" if parent_path else item.text(0)
        self.search_paths[current_path] = item
        
        for i in range(item.childCount()):
            self.store_path(item.child(i), current_path)


    def setup_search(self):
        """
        Sets up the search functionality with debouncing timer.
        Much simpler now that we're using an integrated approach.
        """
        self.create_search_paths()
        

    def select_tree_item(self, path: str):
        """
        Finds and selects an item in the tree based on its full path.
        
        This method takes a path string (like "Suitkaise/App/Tools") and navigates
        through the tree to find and select the corresponding item. It splits the
        path into parts and traverses the tree structure to locate the target item.
        
        Args:
            path: str, the full path of the item to select (components separated by '/')
        """
        # split the path into individual components
        path_parts = path.split('/')

        # start from the root item
        current_item = self.tree.topLevelItem(0)
        # double check that the first part is the root directory
        if not current_item or current_item.text(0) != path_parts[0]:
            return
        
        # loop through the remaining parts of the path
        for part in path_parts[1:]:
            found = False
            # loop through the current item's children
            for i in range(current_item.childCount()):
                child = current_item.child(i)
                if child.text(0) == part:
                    # found the next part of the path
                    current_item = child
                    found = True
                    break

            # if the part wasn't found, stop searching
            if not found:
                return
            
        # select the final item
        self.tree.setCurrentItem(current_item)
        current_item.setSelected(True)
        self.tree.scrollToItem(current_item)
        # expand the selected item if it can be expanded
        if current_item.childCount() > 0:
            current_item.setExpanded(True)
        



    def add_directory(self, path: Path, parent_item: QTreeWidgetItem):
        """
        Recursively adds both directory and file items to the tree.
        
        Args:
            path: A Path object pointing to the current directory being processed
            parent_item: The QTreeWidgetItem under which to add items
            
        This method walks through the directory structure, creating tree items
        for both subdirectories and files. Each item stores its full path and
        maintains the hierarchical relationship.
        """
        try:
            # Get all items in the directory and sort them
            items = sorted(
                # Filter out hidden items and __init__.py files
                [item for item in path.iterdir() 
                if not item.name.startswith('.') and item.name != '__init__.py'],
                # Sort directories first, then alphabetically
                key=lambda x: (not x.is_dir(), x.name.lower())
            )

            for item_path in items:
                # Create a new tree item
                tree_item = QTreeWidgetItem(parent_item)
                tree_item.setText(0, item_path.name)
                tree_item.setData(0, Qt.ItemDataRole.UserRole, str(item_path))

                # If it's a directory, recursively add its contents
                if item_path.is_dir():
                    self.add_directory(item_path, tree_item)

        except PermissionError:
            print(f"Warning: Permission denied for {path}")
        except Exception as e:
            print(f"Warning: Error processing {path}: {e}")

    def setup_connections(self):
        """Sets up all signal-slot connections for the application."""
        # Tree item signals
        self.tree.itemClicked.connect(self.handle_item_click)
        self.tree.itemExpanded.connect(self.handle_item_expanded)
        self.tree.itemCollapsed.connect(self.handle_item_collapsed)

        # button signals
        self.btn_expand_one.clicked.connect(self.expand_one)
        self.btn_collapse_one.clicked.connect(self.collapse_one)
        self.btn_expand_all.clicked.connect(self.expand_tree)
        self.btn_collapse_all.clicked.connect(self.collapse_tree)

        self.btn_copy_selected.clicked.connect(self.copy_selected)
        self.btn_copy_all.clicked.connect(self.copy_all)
        self.btn_copy_contents.clicked.connect(self.copy_contents)

        # search signals
        self.completer.activated.connect(self.select_tree_item)

    def handle_item_click(self, item: QTreeWidgetItem, column: int):
        """
        Handles item clicks - selects item and toggles expansion.
        Also enables/disables appropriate copy buttons based on selection type.
        """
        # store the current selection
        self.current_selection = item
        
        self.btn_copy_selected.setEnabled(True)
        self.btn_copy_contents.setEnabled(True)

        path = Path(item.data(0, Qt.ItemDataRole.UserRole))
        if path.is_dir():
            item.setExpanded(not item.isExpanded())
        
        # ensure the item stays selected
        self.tree.setCurrentItem(item)

    def read_file_contents(self, file_path: Path) -> str:
        """
        Reads and returns the contents of a file.
        
        Args:
            file_path: Path object pointing to the file
            
        Returns:
            str: Contents of the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def get_scan_comment(self, file_path: Path) -> str:
        """
        Checks file for the first comment containing '<scan>' and returns
        the rest of that line.
        
        Args:
            file_path: Path object pointing to the file
            
        Returns:
            str: The comment text after '<scan>' or empty string if not found
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '#' in line and '<scan>' in line:
                        # Get everything after '<scan>'
                        comment = line.split('<scan>')[1].strip()
                        return comment
        except Exception:
            pass
        return ""


    def handle_item_expanded(self, item: QTreeWidgetItem):
        """
        Called when a tree item is expanded.
        Could be used for tracking expanded states or performing
        additional operations when items are expanded.
        """
        pass

    def handle_item_collapsed(self, item: QTreeWidgetItem):
        """
        Called when a tree item is collapsed.
        Could be used for tracking collapsed states or performing
        additional operations when items are collapsed.
        """
        pass

    def expand_one(self):
        """
        Expands one level of the tree from the currently selected item.
        If no item is selected, expands the root level.
        """
        if self.current_selection:
            for i in range(self.current_selection.childCount()):
                child = self.current_selection.child(i)
                child.setExpanded(True)
        else:
            # If no selection, expand root level
            root = self.tree.topLevelItem(0)
            if root:
                root.setExpanded(True)

    def collapse_one(self):
        """
        Collapses one level of the tree from the currently selected item.
        If no item is selected, collapses the root level.
        """
        if self.current_selection:
            for i in range(self.current_selection.childCount()):
                child = self.current_selection.child(i)
                child.setExpanded(False)
        else:
            # If no selection, collapse root level
            root = self.tree.topLevelItem(0)
            if root:
                root.setExpanded(False)

    def expand_tree(self):
        """
        Expands the entire tree and ensures the App directory is expanded.
        This is also called on startup to set the initial expansion state.
        """
        self.tree.expandAll()
        
        # Find and ensure App directory is expanded
        root = self.tree.topLevelItem(0)
        if root:
            for i in range(root.childCount()):
                child = root.child(i)
                if child.text(0) == "App":
                    child.setExpanded(True)
                    break

    def collapse_tree(self):
        """
        Collapses the entire tree.
        """
        self.tree.collapseAll()

    def copy_selected(self):
        """
        Copies the directory structure of the currently selected item to the clipboard.
        
        This function now handles paths differently based on whether they are:
        - At the root level (Suitkaise)
        - At the SK folder level
        - Inside the SK folder
        """
        if not self.current_selection:
            return
            
        # Get the path of the selected item
        path = Path(self.current_selection.data(0, Qt.ItemDataRole.UserRole))
        
        # Generate and copy the structure
        structure = self.generate_directory_structure(path)
        pyperclip.copy(structure)

    def copy_all(self):
        """
        Copies the entire directory structure starting from the root.
        
        Since we now have the SK folder as a container, this function ensures
        the output shows the proper hierarchical structure.
        """
        # For copy_all, we always start from the root
        structure = self.generate_directory_structure(self.root)
        pyperclip.copy(structure)

    def copy_contents(self):
        """
        Copies both directory structure and file contents.
        
        This function has been updated to:
        1. Show proper paths relative to the SK folder when appropriate
        2. Handle file reading and structure generation for the new organization
        3. Maintain clear separation between structure and content sections
        """
        if not self.current_selection:
            return
                
        # Initialize our content list
        contents = []
        
        # Get the path of the selected item
        path = Path(self.current_selection.data(0, Qt.ItemDataRole.UserRole))
        
        # Add the directory structure first
        structure = self.generate_directory_structure(path)
        contents.append(structure)
        
        # Add separator between structure and contents
        contents.append("\n\n=== FILE CONTENTS ===\n")
        
        # Helper function to get relative path display
        def get_display_path(file_path):
            try:
                # If path contains SK, show path from SK onwards
                if self.version in file_path.parts:
                    sk_index = file_path.parts.index(self.version)
                    return '/'.join(file_path.parts[sk_index:])
                # Otherwise show path relative to root
                return str(file_path.relative_to(self.root))
            except ValueError:
                return str(file_path)
        
        # Add file contents based on whether we're copying a file or directory
        if path.is_file():
            if path.name != '__init__.py':
                try:
                    rel_path = get_display_path(path)
                    contents.append(f"\n--- {rel_path} ---\n")
                    contents.append(self.read_file_contents(path))
                except Exception as e:
                    contents.append(f"\nError reading {path}: {str(e)}\n")
        else:
            # For directories, get all file contents recursively
            for file_path in sorted(path.rglob('*')):
                if file_path.is_file() and file_path.name != '__init__.py':
                    try:
                        rel_path = get_display_path(file_path)
                        contents.append(f"\n--- {rel_path} ---\n")
                        contents.append(self.read_file_contents(file_path))
                    except Exception as e:
                        contents.append(f"\nError reading {file_path}: {str(e)}\n")
        
        # Copy everything to clipboard
        pyperclip.copy('\n'.join(contents))

    def generate_directory_structure(self, start_path: Path) -> str:
        """
        Creates a text representation of the directory structure with scan comments.
        
        We now clean up the path representation by removing any current directory
        notation ('./') that might appear in the path. This ensures paths are displayed
        in a clean, user-friendly format starting with 'Suitkaise/' rather than
        'Suitkaise/./'.
        
        Args:
            start_path: Path object pointing to the directory to display
            
        Returns:
            str: Formatted string showing directory structure with clean paths
        """
        try:
            # Clean up the path representation for the root case
            if start_path == self.root:
                # Simply use the root name with a trailing slash
                result = [f"{self.root.name}/"]
            else:
                try:
                    # Get the relative path and clean it up
                    rel_path = start_path.relative_to(self.root)
                    # Convert to string and remove any './' notation
                    clean_path = str(rel_path).replace('./', '')
                    full_path = f"{self.root.name}/{clean_path}"
                    if not full_path.endswith('/'):
                        full_path += '/'
                    result = [full_path]
                except ValueError:
                    # Fallback if path is not relative to root
                    result = [f"{start_path.name}/"]

            # Rest of the function remains the same...
            items = sorted(
                [item for item in start_path.iterdir()
                if not item.name.startswith('.') and item.name != '__init__.py'],
                key=lambda x: (not x.is_dir(), x.name.lower())
            )

            for i, path in enumerate(items):
                is_last = i == len(items) - 1
                prefix = '└── ' if is_last else '├── '
                
                scan_comment = ""
                if path.is_file():
                    scan_comment = self.get_scan_comment(path)
                    if scan_comment:
                        scan_comment = f" # {scan_comment}"
                        
                suffix = '/' if path.is_dir() else ''
                result.append(prefix + path.name + suffix + scan_comment)

                if path.is_dir():
                    self._add_subdirectory_to_structure(path, result, is_last, 1)

            return '\n'.join(result)
        except Exception as e:
            return f"Error generating structure: {str(e)}"

    def _add_subdirectory_to_structure(self, path: Path, result: list, 
                                    is_last_parent: bool, depth: int):
        """
        Helper method to recursively add subdirectory contents to the structure.
        
        This has been separated out to make the code more maintainable and easier
        to understand.
        """
        try:
            items = sorted(
                [item for item in path.iterdir()
                if not item.name.startswith('.') and item.name != '__init__.py'],
                key=lambda x: (not x.is_dir(), x.name.lower())
            )

            for i, subpath in enumerate(items):
                is_last = i == len(items) - 1
                indentation = '    ' if is_last_parent else '│   '
                prefix = indentation * depth + ('└── ' if is_last else '├── ')
                
                scan_comment = ""
                if subpath.is_file():
                    scan_comment = self.get_scan_comment(subpath)
                    if scan_comment:
                        scan_comment = f" # {scan_comment}"
                        
                suffix = '/' if subpath.is_dir() else ''
                result.append(prefix + subpath.name + suffix + scan_comment)

                if subpath.is_dir():
                    self._add_subdirectory_to_structure(subpath, result, is_last, depth + 1)
                    
        except Exception as e:
            result.append(indentation * depth + f'└── <Error: {str(e)}>')

    def expand_to_App(self):
        """
        Expands the tree to show the App directory's contents on startup.
        
        This method navigates through the directory structure:
        1. Expands the root item (Suitkaise)
        2. Expands the SK folder
        3. Finds and expands the App directory
        4. Sets App as the current (selected) item
        """
        root = self.tree.topLevelItem(0)
        if root:
            # Expand the root to see SK folder
            root.setExpanded(True)
            
            # Find and expand SK folder
            for i in range(root.childCount()):
                sk_folder = root.child(i)
                if sk_folder.text(0) == self.version:
                    sk_folder.setExpanded(True)
                    
                    # Look for App directory inside SK
                    for j in range(sk_folder.childCount()):
                        app_dir = sk_folder.child(j)
                        if app_dir.text(0) == "SUITE":
                            app_dir.setExpanded(True)
                            self.tree.setCurrentItem(app_dir)
                            break
                    break


def main():
    """
    Initializes and runs the directory structure scanner application.
    
    This function performs several important steps:
    1. Creates the Qt application instance
    2. Creates our scanner window
    3. Displays the window
    4. Starts the event loop that handles user interactions
    
    The function uses sys.exit() to ensure proper cleanup when the app closes.
    """
    # We need to create exactly one QApplication instance per application
    # sys.argv passes any command line arguments to the application
    app = QApplication(sys.argv)
    
    # Create our main window (DirectoryScanner instance)
    scanner = DirectoryScanner()
    
    # Make our window visible to the user
    scanner.show()
    
    # Start Qt's event loop
    # The event loop is like a continuous cycle that:
    # - Watches for user actions (clicks, key presses)
    # - Updates the display
    # - Handles internal application events
    sys.exit(app.exec())

# This is a Python idiom that means "only run this code if this file is run directly"
# (not when it's imported as a module)
if __name__ == "__main__":
    main()






            

