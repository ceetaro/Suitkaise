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

# suitkaise/main.py

"""
Main module for running the Suitkaise application.
This module serves as the entry point for the application, initializing
the necessary components and starting the main event loop.

It is responsible for setting up the environment and ensuring that
all required dependencies are loaded before the application starts.

It is also responsible for handling command-line arguments and
configuration settings.

"""


import suitkaise_app.int.time.sktime as sktime

def main():

    # initialize fully global registries and programs
    # bridge
    # sk color registry
    # sktime
    # processing pool that both int and ext can use
      # - this will ensure user has enough resources to test their program when needed
    sktime.setup_time()



    global internal # a dictionary to store variables for SK source code
    internal = {}

    global external # a dictionary to store variables for user imported projects
    external = {}

    # create the 2 main processes that run int and ext, respectively
    # these should run in parallel, 




if __name__ == "__main__":
    main()