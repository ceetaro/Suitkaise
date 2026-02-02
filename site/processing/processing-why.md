/*

why the processing module was created

what problems it solves

*/

text = "
You have 2 choices:

1. Accept that Python is single-threaded

2. Deal with `multiprocessing` bullshit

As CPUs get more and more cores, this answer essentially becomes number 2.

Your program that gets away with 1 core usage when the high end CPUs had 4 cores...

now has to deal with 24 core laptops.

So, you have to turn to `multiprocessing` or a similar library for computational power.

And now you have to deal with so much more BS.

(start of dropdown)
Pickle

`PicklingError: Can't pickle your object, hahahahaha! loser.`

Eveything passed from one process to another must be serializable, usually via `pickle`.

But this means that so many essential objects in Python just can't be passed to a different process.

Even if you use serializers like `cloudpickle` or `dill`, you still have to deal with locks, loggers, and other objects that are not serializable.

So you either have to tiptoe around them and not use them, or manually serialize and deserialize them. Neither are fun.

With `processing`, you don't have to deal with any of that. `cucumber` handles all of that for you, opening up the road to making complex multi-process code.

### What is `cucumber`?

`cucumber` is a serialization engine, and another module in the `suitkaise` library.

It is built off of base `pickle`, with specialized handlers for essentially all of the complex objects that other serializers cannot handle.

To learn more, navigate to the `cucumber` module page using the sidebar.

(end of dropdown)

(start of dropdown)
Spaghetti code

Standard `multiprocessing` code is a mess, forcing you to put setup, work, cleanup, looping logic, error handling, and more all into one giant function. Everything just gets hard to manage and starts blending together in our minds. Lots of floating variables, conditional loops, and other things that just cloud everything up.

If only there was an object, that all Python devs use on a daily basis, that organizes complex code with several different pieces into one cohesive unit...

Oh, wait...

Classes exist.

`processing` includes the `Skprocess` class.

Inherit from this class like you would inherit `ABC` from `abc`.

```python
from abc import ABC

class MyAbstractClass(ABC):
```

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):
```

And get access to an entire lifecycle of methods to easily separate your code into sensible pieces.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    def __init__(self):

        # super().__init__() is called automatically for you
        # setup your process here
        # initialize attributes
        # configure Skprocess attributes

    def __prerun__(self):

        # here, you can setup before the main part
        # connect to databases, make API calls, read files...

    def __run__(self):

        # this is the main part
        # you can just write your code here
        # it repeats for you, no need to write looping code

    def __postrun__(self):

        # this is where you clean up your work for this iteration

    def __onfinish__(self):

        # this is when you clean up the process before it exits

    def __result__(self):

        # this returns the result of the process
        # don't have to worry about confusing mid-function returns
        # store your results as instance attributes
        # and return them here

    def __error__(self):

        # this is __result__() when an error occurs
        # you can return a result here, or just raise an error
```

Best part? Once you code the class with at least the `__run__` method, you can just use super simple syntax to run it.

```python
from suitkaise.processing import Skprocess

class DoubleThisNumber(Skprocess):

    def __init__(self, starting_num, number_of_doubles):

        self.starting_num = 1
        self.process_config.runs = number_of_doubles


    def __run__(self):
        
        self.starting_num *= 2

    def __result__(self):

        return self.starting_num


doubler = DoubleThisNumber(1, 5)
doubler.start()

doubler.wait()
result = doubler.result() # == 32
```

There are also other methods! To learn more, head to the `how to use` page.

(end of dropdown)

(start of dropdown)
Queue management

Creating queues. "Yay, yippie! I love queues!" said no one ever.

Making sure that they connect how you want them to.

Putting data in them. Getting data out of them.

Setting up timeouts so that they don't freeze things up.

Having to manually clear out all of them so you don't get deadlocked.

None of this is enjoyable, per se.

### `tell()` and `listen()`

`tell()` and `listen()` are methods you inherit from `Skprocess` that allow you to send and receive data between the parent and subprocess.

It's as simple as this.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    def __init__(self):
        
        # ...

    def __run__(self):

        thing_to_do = self.listen(timeout=1.0)

        did_thing_succeed = do_thing(thing_to_do)

        self.tell(did_thing_succeed)



p = MyProcess()
p.start()

if user_wants_to_change_theme:
    p.tell(f"change the UI theme to {new_theme}")

    theme_changed = p.listen(timeout=1.0)

    if not theme_changed:
        p.stop()

p.wait()

try:
    current_theme_data = p.result()
except ProcessError as e:
    print(f"Process failed: {e}")
    current_theme_data = None

```

(end of dropdown)

(start of dropdown)
Retries

Usually, you have to write a lot of code to handle retries. You have to let the process fail, get information that it crashed, and then restart it manually.

With `processing`, you can just set the `lives` config to a number greater than 1, and the process will retry itself if it fails, keeping all progress except progress from the failed iteration.

So, if something ran for 1000 runs and then crashed, it won't have to rerun the first 999 times. The engine will just reattempt the last run from `__prerun__` onwards.

If the process fails too many times and runs out of `lives`, it will automatically call `__error__()` and return an error, plus whatever else you want to return as a result in the failing state.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    def __init__(self):
        self.process_config.lives = 3
```

(end of dropdown)

(start of dropdown)
Timing is busy work

Want to know how long something took to run in a process?

```python
import time

# for everything you need to time...
start_time = time.time()
do_first_thing()
end_time = time.time()

time_taken = end_time - start_time

first_thing_times.append(time_taken)

# ...
second_thing_times.append(time_taken)
third_thing_times.append(time_taken)

return result, (first_thing_times, second_thing_times, third_thing_times)
```

I don't like having to do this. I'm assuming you don't either.

---

Say you implement the lifecycle methods in your process.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    def __prerun__(self):
        # ...

    def __run__(self):
        # ...

    def __postrun__(self):
        # ...

    def __onfinish__(self):
        # ...

    def __result__(self):
        # ...

    def __error__(self):
        # ...

p = MyProcess()
p.start()

if something:
    p.stop()

p.wait()

# access times
prerun_timer = p.__prerun__.timer
run_timer = p.__run__.timer
postrun_timer = p.__postrun__.timer
onfinish_timer = p.__onfinish__.timer
result_timer = p.__result__.timer
error_timer = p.__error__.timer

# combined prerun, run, and postrun times for each iteration
all_3_combined = p.timer
```
Timers act just like `Timer` objects from `sktime`, another `suitkaise` module.

For more information on timers, head to the `sktime` module page.

(end of dropdown)

(start of dropdown)
Adding in timeouts

Adding in timeouts to a real program is very nuanced/difficult.

First off, you need to actually be able to interrupt blocking code -- something that changes depending on the platform the program is running on.

If you're on Mac or Linux, you can use `SIGALRM` to interrupt blocking code.

If you're on Windows, you need to use a thread-based timeout.

Then, you have to set up timers manually track if the timeout was reached.

It sounds simple, but in reality it is anything but.

To save you time, `Skprocess` allows you to easily set timeouts for each lifecycle method in one line by updating the `process_config` attribute.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):

    def __init__(self):

        self.process_config.timeouts.prerun = 5.0
        self.process_config.timeouts.run = 10.0
        self.process_config.timeouts.postrun = 5.0
        self.process_config.timeouts.onfinish = 10.0
        self.process_config.timeouts.result = 2.0
        self.process_config.timeouts.error = 1.0
```

This will automatically raise a `ProcessTimeoutError` if the timeout is reached as well.

(end of dropdown)

(start of dropdown)
Error handling

We both know that error handling is a necessary evil.

So `Skprocess` raises custom errors depending on the section that the error occurred in, wrapping the original error so you can see what actually happened when.

They all inherit from a `ProcessError` class, making it easy to catch all process errors with a single `except ProcessError` block.

```python
try:
    result = p.result()

except ProcessError as e:

    # e is a ProcessError
    print(f"Process failed: {e}")
    print(f"Original error: {e.original_error}")
    print(f"Run number: {e.current_run}")


```
(end of dropdown)

