# -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0; or the GNU General Public License v3.
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

# suitkaise/int/eventsys/context/thread_context.py

"""
This module provides thread local storage for managing 
event collectors and buses in thread-safe manner. 
It allows for the creation, retrieval, and management 
of event collectors (events that use Event.collect()), 
as well as the creation and setting of event buses
for each thread.

"""

import threading

# Single shared thread-local storage for the entire event system
_thread_local = threading.local()

# Collector management functions
def get_collector_stack():
    """Get the current collector stack or initialize it."""
    if not hasattr(_thread_local, 'collector_stack'):
        _thread_local.collector_stack = []
    return _thread_local.collector_stack

def get_current_collector():
    """Get the current active collector or None."""
    stack = get_collector_stack()
    return stack[-1] if stack else None

def push_collector(collector):
    """Add a collector to the stack."""
    stack = get_collector_stack()
    stack.append(collector)

def pop_collector():
    """Remove the top collector from the stack."""
    stack = get_collector_stack()
    if stack:
        return stack.pop()
    return None

def set_parent_collector(collector):
    """Set the current parent collector."""
    _thread_local.parent_collector = collector

def get_parent_collector():
    """Get the current parent collector."""
    return getattr(_thread_local, 'parent_collector', None)

# Bus management
def get_or_create_bus(bus_class):
    """Get the current bus or create a new one."""
    if not hasattr(_thread_local, 'event_bus'):
        _thread_local.event_bus = bus_class()
    return _thread_local.event_bus

def set_bus(bus):
    """Set the current bus."""
    _thread_local.event_bus = bus