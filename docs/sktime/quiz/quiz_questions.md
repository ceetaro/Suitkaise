# SKTime Quiz Questions

## instructions for creating the quiz

- each quiz question will be a separate "page" on the site
- the user should be able to directly interact with code on answer lines
- the code should look like code blocks for each question
- the question title should not be a part of the code block
- the player's answers should be cached and used to track their progress
- use arrows to navigate between questions
- should look modern and be a light mode site

- we can make a python script to generate a question and answer page

- each page should start as the question
- a check button will be used to check the answer
- if the answer is correct, answer persists until quiz is finished
- if not, we give the user an option to reset to the original question state if they want to try again (they can also just continue editing the current state of the code with the attempted answer)
- there is also an option to show answer for a question that is always available

- at the top of the page, there is a display that shows the quiz status/progress

- put any html webpage content in docs/sktime/quiz/, regardless of programming language

## code creation questions

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
1. import the sktime module

given: nothing

answer:
```python
from suitkaise import sktime
```

Explanation:
In order to use suitkaise modules, you need to import the module using "from suitkaise import (module name)". this avoids unnecessary import logic that you might not want to use.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
2. get the current time

given:
```python
from suitkaise import sktime

current_time = # answer goes here
```
answer:
```python
from suitkaise import sktime

current_time = sktime.now()

# or...
current_time = sktime.get_current_time()
```

Explanation:
You can use the `now()` function to get the current time, or the `get_current_time()` function to get the current time. Either works, and they are functionally the same.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
3. sleep for 3 seconds and return the time after sleeping

given:
```python
from suitkaise import sktime

current_time = sktime.now()

three_seconds_later = # answer goes here
```

answer:
```python
from suitkaise import sktime

current_time = sktime.now()

three_seconds_later = sktime.sleep(3)
```

Explanation:
You can use the `sleep()` function to sleep the current thread for a given number of seconds. If you assign the result to a variable, it will return the time after sleeping.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
4. sleep for 3 seconds without returning the current time

given:
```python
from suitkaise import sktime

# how do you sleep without returning the current time?

# replace this line with your answer
```

answer:
```python
from suitkaise import sktime

# how do you sleep without returning the current time?

sktime.sleep(3)
```

Explanation:
You can use the `sleep()` function to just sleep the current thread without returning the time after the sleep call.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
5. get elapsed time using 2 given times

given:
```python
from suitkaise import sktime

time1 = sktime.now()
time2 = time1 + 3

elapsed = # answer goes here
```

answer:
```python
from suitkaise import sktime

time1 = sktime.now()
time2 = time1 + 3

elapsed = sktime.elapsed(time1, time2)

# or...
elapsed = sktime.elapsed(time2, time1)
```

Explanation:
You can use the `elapsed()` function to get the elapsed time between 2 given times. The order of the times doesn't matter, it will automatically handle it using absolute value.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
6. get elapsed time using 1 given time

given:
```python
from suitkaise import sktime

time1 = sktime.now()

elapsed = # answer goes here
```

answer:
```python
from suitkaise import sktime

time1 = sktime.now()

elapsed = sktime.elapsed(time1)
```

Explanation:
You can use the `elapsed()` function with only one time float given. It will automatically use the current time as the second time.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
7. setup a `Yawn` instance that sleeps for 5 seconds after every 10 yawn() calls

given:
```python
from suitkaise import sktime

yawn_instance = # answer goes here
```

answer:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(sleep_duration=5, yawn_threshold=10)

# or...
yawn_instance = sktime.Yawn(5, 10)
```

Explanation:
The order of the arguments is (sleep duration in seconds, how many yawns before sleeping).

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
8. Log when the `Yawn` instance sleeps

given:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(5, 10, # answer goes here)
```

answer:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(5, 10, True)

# or...
yawn_instance = sktime.Yawn(5, 10, log_sleep=True)
```

Explanation:
You can use the `log_sleep` argument to log when a `Yawn` instance sleeps.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
9. check if the `Yawn` instance slept

given:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(5, 10)

for i in range(100):
    if # answer goes here:
        print("Just slept!")
    else:
        print("Still yawning...")
```

answer:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(5, 10)

for i in range(100):
    if yawn_instance.yawn():
        print("Just slept!")
    else:
        print("Still yawning...")
```

Explanation:
`yawn()` returns True if the `Yawn` instance slept, False otherwise.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
10. reset the `Yawn` instance

given:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(5, 10)

# reset the yawn counter back to 0 on this line
```

answer:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(5, 10)

yawn_instance.reset()
```

Explanation:
You can use the `reset()` method to reset the yawn counter back to 0 without having to sleep or create a new `Yawn` instance.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
11. get statistics about the `Yawn` instance and access them individually

given:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(5, 10)

stats = # answer goes here

current_number_of_yawns = # answer goes here
num_required_to_sleep = # answer goes here
yawns_until_sleep = # answer goes here
total_sleeps = # answer goes here
sleep_duration = # answer goes here
```

answer:
```python
from suitkaise import sktime

yawn_instance = sktime.Yawn(5, 10)

stats = yawn.get_stats()

current_number_of_yawns = stats['current_yawns']
num_required_to_sleep = stats['yawn_threshold']
yawns_until_sleep = stats['yawns_until_sleep']
total_sleeps = stats['total_sleeps']
sleep_duration = stats['sleep_duration']
```

Explanation:
You can use the `get_stats()` method to get statistics about the `Yawn` instance. To access the statistics given, you use dictionary key access.


-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
12. create a `Timer` instance

given:
```python
from suitkaise import sktime

timer = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()
```

Explanation:
You can use the `Timer()` constructor to create a new `Timer` instance.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
13. start the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

# start the timer on this line
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()
```

Explanation:
Use `start()` to start timing a time measurement/lap.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
14. stop the `Timer` instance and return the elapsed time

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()

elapsed = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()

elapsed = timer.stop()
```

Explanation:
Use `stop()` to stop timing a time measurement. If you assign the result to a variable, it will return the elapsed time.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
15. stop the `Timer` instance without returning the elapsed time

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()

# answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()

timer.stop()
```

Explanation:
You can use `stop()` to stop timing a time measurement without returning the elapsed time.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
16. pause the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()

# pause the timer on this line
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()

timer.pause()
```

Explanation:
Use `pause()` to pause the timer. When paused, the timer will not accumulate time for that measurement until `resume()` is called. If already paused, it will warn and do nothing.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
17. resume the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()
timer.start()

# a function that takes some time to run
do_something()

# pause so that user can input answer
timer.pause()

user_answer = input("What is the answer?")

# resume the timer on this line
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()
timer.start()

# a function that takes some time to run
do_something()

# pause so that user can input answer
timer.pause()

user_answer = input("What is the answer?")

timer.resume()
```

Explanation:
Use `resume()` to resume the timer. Resume will silently do nothing if called when the timer is not paused.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
18. lap the `Timer` instance and return the elapsed time

given:
```python
from suitkaise import sktime

timer = sktime.Timer()
timer.start()

elapsed = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()
timer.start()

elapsed = timer.lap()
```

Explanation:
Use `lap()` to stop and then start the timer again. It will return the elapsed time for this lap, and immediately start timing a new lap/time measurement.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
19. add an external time measurement to the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

external_time = 1.5

# add the external time to the timer on this line
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

external_time = 1.5

timer.add_time(external_time)
```

Explanation:
Use `add_time()` to add a pre-measured time to the timer. It will add the time to the next available index in the timer's statistics. It must be a float.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
20. reset the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

# ... many times were measured here...

# reset the timer on this line
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

# ... many times were measured here...

timer.reset()
```

Explanation:
Use `reset()` to clear all measurements and reset the timer.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
21. get the original start time of the `Timer` instance (first time the timer was started)

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

original_start_time = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

original_start_time = timer.original_start_time
```

Explanation:
Use the `original_start_time` property to access the original start time of the timer. If the timer has never been started, it will return None.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
22. get the number of times the `Timer` instance made a time measurement

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

number_of_times = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

number_of_times = timer.num_times
```

Explanation:
Use `num_times` to access the number of times the `Timer` instance made a time measurement.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
23. get the most recent time of the `Timer` instance and its index

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

most_recent_time = # answer goes here
most_recent_index = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

most_recent_time = timer.most_recent
most_recent_index = timer.most_recent_index

# or...
most_recent_time = timer.result
most_recent_index = timer.most_recent_index
```

Explanation:
Use `most_recent` to access the most recent time of the `Timer` instance. `result` does the same thing as `most_recent`. Use `most_recent_lap` to access the index of the most recent time.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
24. get the total time of all measurements of a `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

total_time = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

total_time = timer.total_time
```

Explanation:
Use `total_time` to access the total time of all measurements of the `Timer` instance. If the timer has not yet made any measurements, it will return None.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
25. get the total time paused of the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

total_time_paused = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

total_time_paused = timer.total_time_paused
```

Explanation:
Use `total_time_paused` to access the total time paused of the `Timer` instance. If the timer has never been paused, it will return None.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
26. get the mean, median, min, max, stdev, and variance of the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

mean = # answer goes here
median = # answer goes here
min = # answer goes here
max = # answer goes here
stdev = # answer goes here
variance = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

mean = timer.mean
median = timer.median
min = timer.min
max = timer.max
stdev = timer.stdev
variance = timer.variance
```

Explanation:
Use these properties to access their respective statistics from a `Timer` instance. If the timer has not yet made any measurements, these will return None.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
27. get the 95th percentile of the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

percentile_95 = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

percentile_95 = timer.percentile(95)
```

Explanation:
Use `percentile(N)` to get the Nth percentile of the `Timer` instance. N must be between 0 and 100. If the timer has not yet made any measurements, it will return None.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
28. get the time in index 10 of the `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

time_at_index_10 = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

time_at_index_10 = timer.get_time(10)
```

Explanation:
Use `get_time(index)` to get the time at a given index. If the index is invalid, it will return None.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
29. get the slowest time of the `Timer` instance and its index

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

slowest_time = # answer goes here
slowest_time_index = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

slowest_time = timer.slowest_time
slowest_time_index = timer.slowest_time_index

# or...
slowest_time = timer.max
slowest_time_index = timer.slowest_time_index
```

Explanation:
Use `slowest_time` or `max` to access the slowest time of the `Timer` instance. Use `slowest_time_index` to access the index of the slowest time.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
30. get the fastest time of the `Timer` instance and its index

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

fastest_time = # answer goes here
fastest_time_index = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

fastest_time = timer.fastest_time
fastest_time_index = timer.fastest_time_index

# or...
fastest_time = timer.min
fastest_time_index = timer.fastest_time_index
```

Explanation:
Use `fastest_time` or `min` to access the fastest time of the `Timer` instance. Use `fastest_time_index` to access the index of the fastest time.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
31. get all statistics of a `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

statistics = # answer goes here
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

statistics = timer.get_stats()
```

Explanation:
Use `get_stats()` to get all statistics of the `Timer` instance. It returns a dictionary with all of the instance's statistics.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
32. create a one use timer using the `TimeThis` context manager

given:
```python
from suitkaise import sktime

# create a one use timer on this line with the name "timer"
    # ... timed ...
```

answer:
```python
from suitkaise import sktime

with sktime.TimeThis() as timer:
    # ... timed ...
```

Explanation:
You can use the `TimeThis` context manager to create a one use timer, by not passing in a `Timer` instance as an argument. This will create a new `Timer` instance each time, and record a single time measurement.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
33. create a `TimeThis` context manager for an existing `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

# create a `TimeThis` context manager on this line without a name
    # ... timed ...
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

with sktime.TimeThis(timer):
    # ... timed ...
```

Explanation:
You create a `TimeThis` context manager for an existing `Timer` instance. This will use that timer each time, and accumulate statistics over time. You can create multiple `TimeThis` context managers that use the same `Timer` instance.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
34. pause and resume the `TimeThis` context manager

given:
```python
from suitkaise import sktime

with sktime.TimeThis() as timer:

    do_something()

    # pause the timer on this line

    # wait for user input
    user_input = input("Press enter to continue...")

    # resume the timer on this line

    do_something_else()
```

answer:
```python
from suitkaise import sktime

with sktime.TimeThis() as timer:

    do_something()

    timer.pause()

    # wait for user input
    user_input = input("Press enter to continue...")

    timer.resume()

    do_something_else()
```

Explanation:
You can use the `pause()` and `resume()` methods to pause and resume the timer, just like you would with a standalone `Timer` instance.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
35. return the elapsed time of the most recent time measurement from a `TimeThis` context manager

given:
```python
from suitkaise import sktime

with sktime.TimeThis() as timer:

    # ... timed ...

elapsed = # answer goes here
```

answer:
```python
from suitkaise import sktime

with sktime.TimeThis() as timer:

    # ... timed ...

elapsed = timer.most_recent
```

Explanation:
Just like with a standalone `Timer` instance, you can use the `most_recent` property to access the most recent time measurement from a `TimeThis` context manager. Make sure that you access the most recent time outside the context manager.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
36. use the `@timethis` decorator to time a function without an existing `Timer` instance

given:
```python
from suitkaise import sktime


# add decorator here
def count_to_10():
    for i in range(10):
        print(i)
```

answer:
```python
from suitkaise import sktime

@sktime.timethis()
def count_to_10():
    for i in range(10):
        print(i)
```

Explanation:
You can use the `@timethis` decorator to time a function, even without using an existing `Timer` instance. It will automatically create a new `Timer` instance for each function you want to track.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
37. use the `@timethis` decorator to time a function with an existing `Timer` instance

given:
```python
from suitkaise import sktime

timer = sktime.Timer()

# add decorator here
def count_to_10():
    for i in range(10):
        print(i)

# add another decorator here using the same timer
def count_to_20():
    for i in range(20):
        print(i)
```

answer:
```python
from suitkaise import sktime

timer = sktime.Timer()

@sktime.timethis(timer)
def count_to_10():
    for i in range(10):
        print(i)

@sktime.timethis(timer)
def count_to_20():
    for i in range(20):
        print(i)
```

Explanation:
You can use the `@timethis` decorator to time a function with an existing `Timer` instance. It will use that timer each time, and accumulate statistics over time. You can pass the same timer to multiple different functions.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
38. directly access a function's `Timer` instance created by the `@timethis` decorator

given:
```python
from suitkaise import sktime

@sktime.timethis()
def count_to_10():
    for i in range(10):
        print(i)

timer = # answer goes here
```

```python
from suitkaise import sktime

@sktime.timethis()
def count_to_10():
    for i in range(10):
        print(i)

# get the most recent time measurement of the timer
timer = count_to_10.timer.most_recent
```

Explanation:
You can use the `timer` property to access the `Timer` instance of a function that has been decorated with the `@timethis` decorator. This property acts exactly the same as a regular `Timer` instance, so you can use it exactly the same way.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
39. access a function's `Timer` instance from a different module using global variables

given:
```python
from suitkaise import sktime

@sktime.timethis()
def count_to_10():
    for i in range(10):
        print(i)

# ... in another module ...

# module name = "module_name"
count_to_10_timer = # answer goes here
```

answer:
```python
from suitkaise import sktime

@sktime.timethis()
def count_to_10():
    for i in range(10):
        print(i)

# ... in another module ...

# module name = "module_name"
count_to_10_timer = f_globals.get("module_name_count_to_10_timer")

# or...
count_to_10_timer = f_globals.get('module_name_count_to_10_timer')
```

Explanation:
You can use the `f_globals` dictionary to access all active global variables in your current process. 

Class methods naming: {module_name}_{class_name}_{method_name}_timer
Module level functions naming: {module_name}_{function_name}_timer

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
40. clear all global timers created by the `@timethis` decorator for test environments

given:
```python
from suitkaise import sktime

# clear all global timers on this line
```

answer:
```python
from suitkaise import sktime

sktime.clear_global_timers()
```

Explanation:
You can use the `clear_global_timers()` function to clear all global timers created by the `@timethis` decorator. Use this when testing, or if you have been running your program fro a long time and want to clean up your cached data.

-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------
-----------------------------------------------------------------------------------

