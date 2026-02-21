"""
1000x round-trip stress test for WorstPossibleObject with verbose output.
Run with Code Runner.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise import cucumber
from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject

ROUNDS = 1000

wpo = WorstPossibleObject(verbose=True)
failures = []

for i in range(ROUNDS):
    data = cucumber.serialize(wpo, verbose=True)
    restored = cucumber.deserialize(data, verbose=True)

    passed, issues = wpo.verify(restored)
    if not passed:
        failures.append((i + 1, issues))

    restored.verbose = False
    if hasattr(restored, 'cleanup'):
        restored.cleanup()

wpo.verbose = False
if hasattr(wpo, 'cleanup'):
    wpo.cleanup()

time.sleep(2)

if failures:
    print(f"\nFAILED — {len(failures)}/{ROUNDS} round-trips had issues:")
    for rnd, issues in failures:
        print(f"  Round {rnd}: {issues}")
else:
    print(f"\nPASSED — {ROUNDS}/{ROUNDS} round-trips verified successfully.")
