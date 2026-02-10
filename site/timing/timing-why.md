/*

why the sktime module was created

what problems it solves

*/

rows = 2
columns = 1

# 1.1

title = "Why `timing`?"

# 1.2

text = "
I was so tired of using `time.time()`, running some code, calling `time.time()` again, and then subtracting the difference to get how long it took.

```python
start_time = time.time()

# some code

end_time = time.time()

time_taken = end_time - start_time
```

And it gets even more annoying when you need to time multiple things.

```python
start_time = time.time()
# some code
end_time = time.time()

time_taken = end_time - start_time

# then ...

start_time2 = time.time()
# some code
end_time2 = time.time()

time_taken2 = end_time2 - start_time2
# ...
```

Or when I wanted to time a specific function, I had to return the resulting time with it as a tuple.

```python
def my_function():
    start_time = time.time()

    # whatever the function actually does

    end_time = time.time()

    return function_result, end_time - start_time

# later...
result, time_taken = my_function()
```

Then I had to manually add the times to a list.

```python
times1.append(time_taken)
```

And then calculate stats.

```python
import statistics

mean = statistics.mean(times1)
median = statistics.median(times1)

# ...
```

And you have to do this for every function you need to time.

```python
times2.append(time_taken)

times3.append(time_taken)

# and so on...
```

I wanted a super quick way to do this, that also made sense.

And I ended up with 2 really awesome things!

(insert 2 blank lines)

## `@timethis` decorator

Without `timing` - *7 lines*
(start of dropdown)
```python
import time # 1
from typing import Any

times_my_function = [] # 2

def my_function() -> tuple[Any, float]:
    start_time = time.time() # 3

    # whatever the function actually does

    end_time = time.time() # 4

    return function_result, end_time - start_time # 5

result, time_taken = my_function() # 6

times_my_function.append(time_taken) # 7
```
(end of dropdown)

With `timing` - *2 lines*

- you can just slap `@timethis()` on any function you need to time
- stored as a property of the function
- don't have to edit a function to time it

```python
from suitkaise.timing import timethis # 1

@timethis() # 2
def my_function():

    # whatever the function actually does

    return result

result = my_function()
```

(insert 2 blank lines)

## `TimeThis` context manager

Without `timing` - *6 lines*
(start of dropdown)
```python
import time # 1

times = [] # 2

start_time = time.time() # 3

# whatever you need to time

end_time = time.time() # 4

time_taken = end_time - start_time # 5
times.append(time_taken) # 6
```
(end of dropdown)


With `timing` - *4 lines*

- no manual tracking
- context manager makes it clear what is being timed

```python
from suitkaise.timing import TimeThis, Sktimer # 1

t = Sktimer() # 2

with TimeThis(t): # 3

    # whatever you need to time

# block exits ...

time_taken = t.most_recent # 4
```
