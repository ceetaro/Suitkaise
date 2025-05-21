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

# suitkaise/int/processing/reservations.py

"""
Constants for reserved process and thread names.

"""

class ReservedProcesses:
    """Constants for reserved process names."""
    # reserved process names
    BRIDGE_COMM = 'bridge_communication'
    INT_EXEC = 'internal_execution'
    INT_UI = 'internal_ui'
    EXT_EXEC = 'external_execution'
    EXT_UI = 'external_ui'
    EXT_STATE = 'external_state_mannager'
    DEVWINDOW = 'developer_window'

class ReservedThreads:
    """Constants for reserved thread names."""
    # reserved thread names
    BRIDGE = 'bridge_thread' # in the bridge communication process
    INT_STATION = 'int_station_thread' # in the internal execution process
    EXT_STATION = 'ext_station_thread' # in the external execution process


