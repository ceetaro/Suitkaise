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

# suitkaise/int/eventsys/mgr/event_mgr.py

"""
This is the manager file for initializing the event system and key registry.
It sets up the event system and registers keys for various events.
This module is responsible for managing the event system and ensuring that
the necessary components are initialized correctly.

"""

# manager file for initializing the event system and key registry
import suitkaise_app.int.eventsys.keyreg.keyreg as keyreg
import suitkaise_app.int.eventsys.keyreg.register_keys as register_keys


def setup_event_system():
    """
    Initialize the event system and key registry.
    This function sets up the event system and registers keys for various events.
    """
    # Initialize the key registry
    keyreg.initialize_key_registries()

    # Register default keys
    register_keys.register_default_keys()




def main():
    """
    Main function to set up the event system.

    Call this directly to test the event system setup.

    """
    setup_event_system()


if __name__ == "__main__":
    main()



