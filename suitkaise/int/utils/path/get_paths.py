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

# suitkaise/int/utils/path/get_paths.py

"""
Module with utilities related to file paths and directories.

"""

import os


def get_dirs_and_files_from_path(path: str, 
                                 subdirs: bool = False
                                 ) -> tuple[list[str], list[str]]:
    """
    Get all directories and files from a given path.
    Optionally get all subdirectories and their files by searching recursively.

    Args:
        path (str): The path to search for directories and files.
        subdirs (bool): If True, include subdirectories and their files.
                        Defaults to False.

    Returns:
        tuple: A tuple containing two lists:
            - directories: List of directories in the given path.
            - files: List of files in the given path.
    """
    directories = []
    files = []
    if os.path.exists(path):
        for root, dirs, filenames in os.walk(path):
            directories.extend(dirs)
            files.extend(filenames)
            if not subdirs:
                break
    else:
        raise FileNotFoundError(f"Path '{path}' does not exist.")
    
    return directories, files


def get_file_path():
    """
    Get the file path of the current script.

    Returns:
        str: The file path of the current script.
    """
    return os.path.abspath(__file__)

def get_dir_path():
    """
    Get the directory path of the current script.

    Returns:
        str: The directory path of the current script.
    """
    return os.path.dirname(os.path.abspath(__file__))


def get_file_path_of_caller(frames_back: int = 2) -> str:
    """
    Get the file path of the calling function.

    Args:
        frames_back (int): The number of frames to go back in the call stack.
            Default is 2 to skip the current function and the caller of this function.

    Returns:
        str: The file path of the calling function, or None if not found.
        
    """
    import inspect
    frame = inspect.currentframe()
    for _ in range(frames_back):
        if frame is None:
            return None
        frame = frame.f_back

    if frame is None:
        return None
    
    module = inspect.getmodule(frame)
    if module is None:
        return None
    
    return os.path.abspath(module.__file__)