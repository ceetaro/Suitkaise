/*

why the circuit module was created

what problems it solves

*/

text = "
This is a super simple module that I added in.

Here is why:

- cleaner code — no more while True with break
- thread safety — share a circuit across multiple threads
- easier to think about — circuit breakers are real-world things
- readable — while not circ.broken is easy to spot when reading code
- error handling — counts failures and makes for clearer error handling
optional sleep — add cooldown periods after failure thresholds
- optional sleep — add cooldown periods after failure thresholds

It is purely for your quality of life! Cheers

Without `circuit` - *8 lines*
(start of dropdown)
```python
# count failures manually
import time # 1

failures = 0 # 2
max_failures = 5 # 3

while failures < max_failures:
    try:
        result = something_that_might_fail()
        break  # Success, exit loop
    except SomeError:
        failures += 1 # 4
        if failures >= max_failures: # 5
            break # 6
        time.sleep(0.5)  # 7

if failures >= max_failures: # 8
    print("Failed after the given number of attempts")
```
(end of dropdown)


With `circuit` - *4 lines*

- clearer
- no variables to track
- no clutter

```python
from suitkaise import circuit # 1

circ = circuit.Circuit(5, 1) # 2

while not circ.broken:
    try:
        result = something_that_might_fail()
        break  # Success, exit loop
    except SomeError:
        circ.short()  # 3

if circ.broken: # 4
    print("Failed after the given number of attempts")
```