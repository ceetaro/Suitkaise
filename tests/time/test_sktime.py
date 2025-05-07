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

# tests/time/test_sktime.py

# Main file being tested: suitkaise/time/sktime.py

"""
Test file to test the sktime module.

"""

import uuid
import random

import suitkaise.time.sktime as sktime

# NOTE: Currently, tests look good.

def test_sktime(_random: bool = False):
    if _random:
        print("Randomizing sleep time")
        sleep_time = random.randint(1, 20)
        sleep_time2 = random.randint(1, 6)
        num_yawns = random.randint(1, 5)
    else:
        print("Using fixed sleep time")
        sleep_time = 5
        sleep_time2 = 10
        num_yawns = 3


    sktime.setup_time()

    time1 = sktime.now(dprint=True)

    # wait for 1 second
    sktime.sleep(1)
    time2 = sktime.now(dprint=True)
    print(f"\ntime2 - time1: {time2 - time1}\n")

    id = "chain1"
    # start a yawn
    sktime.yawn(2, 4, 5, id, dprint=True)

    sktime.sleep(sleep_time, dprint=True)

    sktime.yawn(num_yawns, 23, 16, id, dprint=True)

    for i in range(num_yawns):
        sktime.sleep(sleep_time2, dprint=True)
        sktime.yawn(2, 1, 3, id, dprint=True)

    time3 = sktime.now(dprint=True)
    print(f"time3 - time2: "
          f"{sktime.to_custom_time_diff_format(sktime.elapsed(time2, time3))}\n")


test_sktime(_random=False)

print("\n==================\n")

counter = 0
while counter < 3:
    test_sktime(_random=True)
    counter += 1
    print(f"Random test {counter}")


