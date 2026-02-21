# About `suitkaise`

Note: for technical info, see the [technical info](technical-info) page.

`suitkaise` is a Python code library.

It's for developers of all skill levels, and was created with 3 main goals in mind:

1. To make things easier and faster for all developers.

2. To bridge the knowledge gap for inexperienced developers to create professional level programs

3. Change the world of parallel processing in Python

There are many things in Python that are difficult or nuanced for beginners, and many more that are just annoying, overwhelming, and time consuming for all developers.

I have taken a few of the most foundational and useful parts of modern Python and made them faster, clearer, and easier to use.

Every module I have made started as a "dream API".

"If it could just be like this..."

"If it worked like this..."

"I would use this so much more if it looked like this..."

I created things that I wished worked like the concepts I wrote. Then I went backwards to actually make it work.

## What `suitkaise` does

Think of the printing press, an invention that made production of paper media faster, more standardized, and less prone to human error. People didn't have to write books by hand anymore, saving them a large amount of time and effort.

The result: the world was flooded with books, and the "Information Age" began.

There are many things in Python that need their own printing press to make using them faster, more standardized, and less prone to human error.

Parallel processing, Python-to-Python serialization, file path handling, and more.

`suitkaise` gives you these printing presses.

The name is inspired by "hacker laptops", where the user opens a briefcase and hacks some mainframe in 5 seconds. That's the level of speed and ease you get with `suitkaise`.

### `processing` - Unlocks the full potential of parallel programming in Python.

60% of parallel processing is batch processing, where you process N number of items at once instead of just 1. `processing` gives you a `Pool` class that makes batch processing easy, with 3 standard pooling patterns.

The other 40% is creating long-running, complex subprocesses that do more than just look up data or compute something. Creating these is generally a nightmare even for experienced developers.

`processing` gives you an `Skprocess` class that makes creating these easy, with coded lifecycle methods to setup, run, cleanup, and more. These classes include timing, error handling, and run the process internally, so you don't have to worry about managing the process yourself.

Finally, `processing` gives you a `Share` class.

Every developer knows how to create a class instance and add objects to it.

And that's all you have to do with `Share`. Instantiate it, add objects to it, and pass it to your subprocesses. It ensures that everything syncs up and remains in sync for you. Even complex classes can be added and used just like you would use it normally.

How? `cerial`, the serialization engine that can handle a vast amount of things that `pickle`, `cloudpickle`, and `dill` cannot, including complex, user created class instances that would fail to serialize with the other options.

### `cerial` - Serialize anything.

`cerial` outperforms all competitors in coverage, almost entirely eliminating errors when converting to and from bytes. Things like locks, generators, file handles, and more are all covered. Additionally, it has faster speed than `cloudpickle` and `dill` for many simple types, and is also faster in most cases for the more complex types as well.

Why is this awesome? You don't have to worry about errors anymore. You now have access to a custom class, the objects you want to use in it but couldn't before, and the ability to just share data between processes without thinking, all powered by this engine. You don't even have to use the other modules to get an upgrade. This is just simply better.

### `paths` - everything path related is so much more simple

It includes `Skpath`, a path object that uses an auto-detected project root to normalize all of your paths for you. It is cross platform compatible. An `Skpath` made on Murphy's Mac will be the same as the same `Skpath` made on Gurphy's Windows laptop.

It also includes an `@autopath` decorator that can be used to automatically streamline all of your paths to a specific type, getting rid of type mismatches in their entirety.

### `timing` - times your code with one line

`timing` gives you a `Sktimer` class that is the core piece of this module. It powers `@timethis` and the `TimeThis` context manager, which allow you to time your code with one line.

Additionally, `Sktimer` collects far more statistical data than `timeit`, including mean, median, standard deviation, percentiles, and more.

### `circuits` - manage your execution flow more cleanly

`circuits` gives you two patterns to manage your code. 

What separates them from other circuit breaker libraries is their use in parallel processing.

  - `Circuit` - auto-resets after sleeping, great for rate limiting, resource management, and more
  
  - `BreakingCircuit` - stays broken until manually reset, great for stopping execution after a certain number of failures with extra control

`circuits` is fully thread-safe.

`BreakingCircuit` also works with `Share`, so you can share the circuit breaker state across process boundaries.


### `sk` - modify your functions and methods without changing their code

`sk` can be used as a decorator or a function, and adds some special modifiers to your functions and methods. 

  - `.retry()` - retry it when it fails
  - `.timeout()` - return an error if it takes too long
  - `.background()` - run it in the background and get the result later using Futures
  - `.asynced()` - get an async version of it if it has calls that block your code from running using `asyncio.to_thread()`
  - `.rate_limit()` - limit the number of calls it makes per second


## Why you should use `suitkaise`

`suitkaise` is for the developer.

As previously mentioned, when I created `suitkaise`, I made the end goal first: what I myself as a developer would want to use.

All of `suitkaise` is thousands of iterations improving on this goal API, which was created to address different problems I myself have encountered as a developer.

Here are the problems that `suitkaise` was made for.

(start of section for multiprocessing)
### Multiprocessing

Parallel processing, or multiprocessing, is one of the essential concepts for modern software development.

But it is also a pain in the ass to set up.

Many users aren't just plugging the same function into multiple processes to make things go faster.

They might be using multiple subprocesses to make software run smoother, manage UI, gather real time data, manage resources or databases, and more.

These are all much more involved than just creating a processing pool to work with a single function that has different inputs. They require things like:

- Error handling
- Detailed logging and debugging
- Cross process communication
- Thoughtful lifecycle management
- And more

Trying to do all of this manually for each individual scenario is overwhelming and time consuming, even with Python's `multiprocessing.Process` class.

So I made my own class.

Inherit from the special `Skprocess` class to create your own custom processes.

```python
from suitkaise.processing import Process

class MyProcess(Process):

    def __init__(self, num_loops: int):
        self.counter = 0

        # run N times
        self.config.num_loops = num_loops


    def __preloop__(self):

        # here, you can setup before the main part
        # connect to databases
        # make API calls
        # read files


    def __loop__(self):

        # this is the main part
        # you can just write your code here
        # it repeats for you, no need to write looping code


    def __postloop__(self):

        # this is where you clean up your work
        # close connections
        # add results to attributes

    
    def __onfinish__(self):

        # this is when you clean up the process
        # calculate summaries
        # save results to files
        # send emails


    def __result__(self):

        # this returns the result of the process
        # don't have to worry about confusing returns
        # store your results as instance attributes
        # and return them here


    def __error__(self):

        # this is __result__() when an error occurs

```

Everything is separated into pieces that make much more sense. You have set spaces for setup, your main work, and cleanup/teardown. And, everything follows simple class practices.

Control the process with simple methods:

```python
p = MyProcess(num_loops=10)

# start the process
p.start()

# wait for the process to finish
p.wait()

# access the result
result = p.result
```

(end of section for multiprocessing)

(start of section for cant pickle)
### Can`t pickle

When you try to pickle an object, you might get an error like this:

```
TypeError: cannot pickle 'MyObject' object
```

After hours of debugging, these feel like slaps in the face.

```
TypeError: can't pickle your object, hahahahaha! skill issue.
```

So many essential objects in Python are not pickleable, even if you use custom picklers like `cloudpickle` or `dill`.

Your thread locks don't pickle.

Your database connections don't pickle.

Your functions don't always pickle.

Your loggers don't pickle correctly.

Your class objects don't pickle unless they are extremely basic.

Your circular references don't reconstruct correctly.

There are also so many other weird BS quirks that you have to account for, like locally-defined functions, lambdas, closures, and more.

So, I made my own serialization engine that handles all of this: `cucumber`.

I wanted a serialization engine that could handle anything. I never wanted a pickling error again in my life.
    
But being able to serialize "anything" is a steep challenge. To prove that `cucumber` could do it, I needed a rival, an enemy, a final boss to defeat. One that, after winning, would let me say "I think I can serialize anything now."

So, I created the `WorstPossibleObject`.

- 5 levels of nested classes.

- Every collection type placed in each level at random, nested with random objects.

- Objects including complex classes, loggers, functions, and more, that nothing else serializes.

- Every object initialized at least once on every level.

- Each object with a different random seed.

Basically, "how can I make this as bad as possible?"

Then, I created an engine to beat it.

Then, I battled it thousands of times, forcing the engine to successfully serialize it and deserialize it multiple times per battle. Not a single error was allowed to occur.

Once the engine won, I felt confident that I could serialize anything. But there will always be some gap, some edge case, some exception not accounted for.

Therefore, I have written a special way for you to handle things yourself if need be.

`__serialize__()` and `__deserialize__()` methods in your classes will be used first by `cucumber`, before it uses the default handling.

You can use them to override the default serialization and deserialization behavior for your own objects.

### File path handling

Do you ever pull a repo from your Windows PC at work and it doesn't work on your Mac at home?

Or, maybe your laptop at home is also Windows, but the project is placed in a different directory than the one you use at work.

And then everything breaks.

Right now, Python doesn't have true, consistent, or standardized cross-platform path handling. While it isn't too hard to do manually, it opens the door for miscommunications, errors, and more.

`paths` ensures that you can't make mistakes, and simplifies a lot of the manual work down into one line.

First off, there's `Skpath`.

`Skpath` is a path object that automatically detects the project root and uses it to normalize paths for you. These paths work cross machine and cross platform, as long as the project structure is the same.

No need to convert paths between operating systems.

No need to worry about where your project is located.

No needing to manually convert paths to work correctly everywhere.

### Timing your code

I used to hate having to write code to time things.

So I created `timing`.

!!! FINISH THIS SECTION !!!

## Using `suitkaise` with AI

Currently, AI agents like ChatGPT that you use with something like Cursor are not trained to use `suitkaise`.

That doesn't mean you can't use `suitkaise` with AI.

### Install the docs and place them in your project

The docs are available for download through the `suitkaise` CLI.

1. `pip install suitkaise`
2. Add a `setup.sk` file to your project root
3. With your cwd inside the project root, run `suitkaise docs` from the terminal to download the docs to your project root.

Once you do this, AI agents will have access to the docs, including a detailed API reference for each module and internal workings.

Use this prompt:
```
I am using suitkaise, a Python code library.

The docs for the lib are attached under suitkaise-docs.

Please read them and familiarize yourself with the library before continuing.
```

## How to give feedback

There are multiple ways to give feedback or report bugs. I am most likely to check the feddback forms first.

- use the feedback page (link to feedback page)

- use the GitHub issues page (link to issues page)

- use the Discord server (link to Discord server)

- use the Reddit subreddit (link to Reddit subreddit)

- email <not-api>suitkaise@suitkaise.info</not-api>

- DM any `suitkaise` social media account



