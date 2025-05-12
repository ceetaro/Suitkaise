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

# suitkaise/int/eventsys/core/cycle/cycle_part.py

"""
Module containing the CyclePart class, and its supporting objects, which are used to 
construct a "part" that can be added to a Cycle. 

"""

import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Callable

@dataclass
class ResourceReqs:
    """Resource requirements for a CyclePart."""
    cpu_cores: int = 1
    memory_mb: int = 0
    gpu_count: int = 0
    network_bandwidth_mbps: int = 0
    custom_resources: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_resources is None:
            self.custom_resources = {}


@dataclass
class ExecMetadata:
    """Execution metadata for a CyclePart."""
    timeout: float = None
    retry_limit: int = None
    retry_count: int = 0
    retry_delay: float = 0
    error_handler: Optional[Callable[[Exception], Any]] = None
    error_handler_args: Tuple = ()
    error_handler_kwargs: Dict[str, Any] = None
    data_dependencies: List[str] = None
    output_schema: Dict[str, type] = None

    def __post_init__(self):
        if self.data_dependencies is None:
            self.data_dependencies = []
        if self.output_schema is None:
            self.output_schema = {}


class CyclePart:
    """
    CyclePart class to be used in CycleBuilder to create Cycles.
    
    A CyclePart represents a single executable part of a cycle, complete with its own
    threading.Event flags, process/thread location, resource requirements, and custom
    execution logic.
    
    """
    
    def __init__(self,
                 )
