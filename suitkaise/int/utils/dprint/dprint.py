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

