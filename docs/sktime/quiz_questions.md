# SKTime Quiz Questions

## code creation questions

1. import the sktime module

given: nothing

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

3. sleep for 3 seconds

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

4. sleep without returning the current time

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

Order Independence
Q: "What makes sktime.elapsed() better than manual time subtraction?"
A: Order doesn't matter + automatic current time + uses math.fabs() for precision

Automatic End Time
Q: "If you call sktime.elapsed(start_time) with only one argument, what does it use as the end time?"
A: Current time (when elapsed() is called)

Rate Limiting Concept
Q: "You want to pause for 5 seconds after every 10 API requests. How would you configure a Yawn instance?"
A: sktime.Yawn(sleep_duration=5, yawn_threshold=10)

Return Value Understanding
Q: "What does yawn.yawn() return when it actually sleeps vs when it just counts?"
A: True when it sleeps, False when just counting

Real-world Application
Q: "You're processing 1000 images and want a 3-second cooling break every 50 images. Write the Yawn setup."
A: processor = sktime.Yawn(sleep_duration=3, yawn_threshold=50)

Timer States
Q: "After calling timer.start(), which methods can record a measurement?"
A: stop() and lap() (both record measurements)
Pause/Resume Behavior

Q: "What happens to paused time when using Timer's pause/resume functionality?"
A: Paused time is excluded from measurements and tracked in total_time_paused

Statistics Access
Q: "What's the difference between timer.fastest_time and timer.min?"
A: They're the same (both return minimum time)

Manual Time Addition
Q: "How do you add a pre-measured time of 2.5 seconds to a Timer?"
A: timer.add_time(2.5)

TimeThis Variants
Q: "What's the difference between TimeThis() and TimeThis(my_timer)?"
A: Without timer = new instance each time; with timer = accumulates statistics

Context Operations
Q: "Can you call pause() and resume() on the timer returned by TimeThis context manager?"
A: Yes, it supports all Timer operations

Auto-Timer Access
Q: "After decorating a function with @sktime.timethis(), how do you access its timing statistics?"
A: my_function.timer.mean (timer is attached to the function)

Explicit vs Auto Timers
Q: "What happens when you use @sktime.timethis(my_timer) vs @sktime.timethis()?"
A: Explicit timer accumulates across functions; auto creates per-function timer

Timer Naming Convention
Q: "What naming pattern does @sktime.timethis() use for auto-created global timers?"
A: module_function_timer or module_ClassName_method_timer

Statistical Snapshots
Q: "Why might you use timer.get_statistics() instead of accessing properties directly?"
A: Creates immutable snapshot that won't change with new measurements

Thread Safety
Q: "Can multiple threads safely use the same Timer instance simultaneously?"
A: Yes, Timer uses per-thread sessions

Memory Management
Q: "How do you clear all auto-created global timers in long-running applications?"
A: sktime.clear_global_timers()

Multiple Decorators
Q: "Can you stack multiple @sktime.timethis() decorators on the same function?"
A: Yes, each decorator creates its own timing measurement
# TODO we actually need to test this

Yawn Reset Behavior
Q: "What happens to the yawn counter when a Yawn instance reaches its threshold and sleeps?"
A: Counter automatically resets to 0 after sleeping

Timer Property Aliases
Q: "What are three different ways to access the most recent timing measurement from a Timer?"
A: timer.most_recent, timer.result, or timer.get_time(timer.most_recent_lap)

Error Handling
Q: "What happens if you try to call timer.stop() without first calling timer.start()?"
A: Raises RuntimeError

Percentile Understanding
Q: "If you have 10 timing measurements, what does timer.percentile(90) return?"
A: The 90th percentile value (9th fastest time when sorted)

Yawn Statistics
Q: "What information is available in the dictionary returned by yawn.get_stats()?"
A: current_yawns, yawn_threshold, total_sleeps, sleep_duration, yawns_until_sleep

Timer Index Access
Q: "How do you get the 3rd timing measurement (0-based indexing) from a Timer?"
A: timer.get_time(2)

Context Manager Exception Behavior
Q: "If an exception occurs inside a TimeThis context block, does it still record a timing measurement?"
A: Yes, timing is recorded even if an exception occurs

Sleep Duration Types
Q: "Can sktime.sleep() accept fractional seconds like 0.5 or 1.25?"
A: Yes, it accepts any float value for seconds

Timer Reset Effects
Q: "After calling timer.reset(), what happens to num_times and most_recent?"
A: num_times becomes 0, most_recent becomes None

Yawn Logging
Q: "How do you enable logging messages when a Yawn instance sleeps?"
A: Set log_sleep=True in the constructor

Timer Lap vs Stop
Q: "What's the key difference between timer.lap() and timer.stop() in terms of timer state?"
A: lap() continues timing for next measurement, stop() ends the current timing session

Statistical Properties
Q: "Name three statistical measures automatically calculated by Timer (besides mean and median)?"
A: stdev (standard deviation), variance, min/max

Multiple Timer Usage
Q: "Can you time different functions with the same explicit Timer instance?"
A: Yes, using @sktime.timethis(shared_timer) on multiple functions

Import Styles
Q: "What are the two supported ways to import and use sktime functions?"
A: from suitkaise import sktime (then sktime.now()) or from suitkaise.sktime import now

TimeThis Flexibility
Q: "Inside a TimeThis context, can you call timer.lap() to record intermediate measurements?"
A: Yes, TimeThis supports all Timer operations including lap()

Negative Sleep Handling
Q: "What happens if you call sktime.sleep(-1)?"
A: Raises ValueError (mirrors time.sleep() behavior)

Timer Original Start Time
Q: "How can you calculate total real-world time since a Timer was first started?"
A: sktime.now() - timer.original_start_time

Performance Comparison
Q: "True or False: sktime.now() has significantly more overhead than time.time()"
A: False, overhead is minimal (within small constant factor)

Fastest vs Slowest Access
Q: "How do you find which measurement index corresponds to the fastest timing?"
A: timer.fastest_lap (returns the index of fastest measurement)

Yawn Thread Safety
Q: "Can multiple threads safely call yawn.yawn() on the same Yawn instance?"
A: Yes, Yawn operations are thread-safe

Timer Statistics Immutability
Q: "If you get stats = timer.get_statistics(), do the values in stats change when you add more measurements?"
A: No, get_statistics() returns an immutable snapshot

Empty Timer Behavior
Q: "What does timer.mean return on a fresh Timer with no measurements?"
A: None

Elapsed Type Validation
Q: "What happens if you call sktime.elapsed('not_a_number', 5.0)?"
A: Raises TypeError

Code Completion - Timer Setup
Q: "Complete this pattern for timing a batch job with progress tracking:
timer = sktime.Timer()
timer.start()
for i, item in enumerate(items):
    process_item(item)
    if i % 100 == 0:
        ______ # What goes here for progress measurement?"
A: timer.lap()

Code Completion - Context Manager
Q: "Complete this pattern for timing with user interaction:
with sktime.TimeThis() as timer:
    load_data()
    ______  # User reviews data
    user_input = input('Continue? ')
    ______  # Resume timing
    process_data()"
A: timer.pause(), timer.resume()

Choose Best Tool
Q: "You need to monitor API response times across 1000+ requests for statistical analysis. Which sktime tool is most appropriate?"
A: @sktime.timethis() decorator (automatic, rich statistics, minimal code)

Scenario - Database Optimization
Q: "You suspect certain database queries are slow but don't know which ones. What's the fastest way to add timing to multiple query methods?"
A: Add @sktime.timethis() decorator to each query method

Scenario - Batch Processing
Q: "You're processing 10,000 files and want to estimate completion time. Which Timer features help?"
A: timer.lap() for each batch + timer.mean for average + extrapolation

Debug Naming
Q: "A function called process_data in module analytics.py gets @sktime.timethis(). What's the auto-created timer name?"
A: analytics_process_data_timer

Real-world - Rate Limiting
Q: "You're downloading 500 files from an API that allows 50 requests per minute. How do you configure rate limiting?"
A: sktime.Yawn(sleep_duration=60, yawn_threshold=50) 

Performance Best Practice
Q: "For very high-frequency operations (millions per second), what's a better approach than decorating every call?"
A: Manual timer.start()/timer.stop() with sampling (time every Nth operation)

Memory Efficiency
Q: "True or False: Timer instances consume significant memory when storing thousands of measurements"
A: False, measurements are stored efficiently

Class Method Decoration
Q: "Can you use @sktime.timethis() on class methods and instance methods?"
A: Yes, works on all callable types including class/instance methods