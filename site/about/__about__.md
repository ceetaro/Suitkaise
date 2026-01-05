/* 

The about page for the site.

This is where I give basic info, a mission and vision statement, and an explanation of why I created the suitkaise code library.

The README and licenses are also included as dropdowns on this page.

*/

rows = 3
columns = 1

# 1.1

/*

This is where I will be placing my social media links.

They are also placed in the footer of every site page.

*/


# 2.1

title = "About `suitkaise`"

# 3.1

text = "

`suitkaise` is a Python code library.

(this is a dropdown section for technical info)
## Installation and technical info
To install `suitkaise`, run this in your terminal:

```bash
pip install suitkaise
```

`suitkaise` is currently version `0.2.4`.

(this is a dropdown section for the README)
#### `README`

### Suitkaise

Making things easier for developers of all skill levels to develop complex applications.

#### Installation

```bash
pip install suitkaise
```

#### Info

Supported Python versions: 3.11 and above

Currently, `suitkaise` is version `0.2.4`.

All files and code in this repository is licensed under the MIT License.

`suitkaise` contains the following modules:

- cerial: serialization engine

- circuit: flow control

- processing: multiprocessing/subprocesses

- skpath: path utilities

- sktime: timing utilities

#### Documentation

All documentation is available for download:

```python
from suitkaise import docs

docs.download("path/where/you/want/them/to/go")

# auto send them to project root
docs.download()
```

To send them outside of your project root, use the `Permission` class:

```python
from suitkaise import docs, Permission

with Permission():
    docs.download("Users/joe/Documents")
```

You can also view more at [suitkaise.info](https://suitkaise.info).
(end of dropdown section for the README)

(this is a dropdown section for the licenses)
#### `suitkaise` is licensed under the MIT License. View license here.

MIT License

Copyright (c) 2025 Casey Eddings

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

(end of dropdown section for the licenses)
(end of dropdown section for technical info)


`suitkaise` is for developers of all skill levels, and was created with 3 main goals in mind:

1. To bridge the knowledge gap for inexperienced developers to create professional level programs

2. To make things easier and faster for all developers.

3. Change the world

There are many things in Python that are difficult or nuanced for beginners, and many more that are just annoying, overwhelming, and time consuming for all developers.

I have taken a few of the most foundational and useful parts of Python and made them faster, clearer, and easier to use.

Every module I have made started as a "dream API".

"If it could just be like this..."

"If it worked like this..."

"I would use this so much more if it looked like this..."

I created things that I wished worked like the concepts I wrote, and then went backwards to actually make it work.

I'm not a fan of trying to explain why without specifics, so I'm just going to list a bunch of annoying things that I've had to deal with over time and how `suitkaise` solves them.

(this is a dropdown section for multiprocessing)
## Multiprocessing

Multiprocessing is a powerful tool, but it is also a pain in the ass to set up.

Many users aren't just plugging the same function into multiple processes to make things go faster.

They might be using multiple subprocesses to make software run smoother, manage UI, gather real time data, manage resources or databases, and more.

These are all much more involved than just creating a processing pool to work with a single function that has different inputs. They require things like:

- Error handling
- Detailed logging and debugging
- Cross process communication
- Thoughtful lifecycle management
- and more

Trying to do all of this manually for each individual scenario is overwhelming and time consuming.

I turned processing into one class.

Inherit from the special `Process` class to create your own custom processes.

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

Everything is separated into pieces that make much more sense.

Everything is encapsulated into a single class.

You can start the process with one line.

```python
p = MyProcess(num_loops=10)

# start the process
p.start()

# wait for the process to finish
p.wait()

# access the result
result = p.result
```

(button)
Read more here.
(end of button)

(end of dropdown section for multiprocessing)

(this is a dropdown section for can't pickle X)
## Can't pickle

When you try to pickle an object, you might get an error like this:

```
TypeError: can't pickle your object, hahahahaha!
```

So many essential objects in Python are not pickleable, even if you use custom picklers like `cloudpickle` or `dill`.

Your thread locks don't pickle.

Your database connections don't pickle.

Your functions don't pickle.

Your loggers don't pickle.

Your class objects don't pickle.

Solution: use `cerial` to serialize your objects.

I wanted a serialization engine that could handle anything. I never wanted a pickling error again in my life.
    
But being able to serialize "anything" is a steep challenge. I needed a rival, an enemy, a final boss to defeat. One that, after winning, would let me say "I think I can serialize anything now."

So, I created the `WorstPossibleObject`.

5 levels of nested classes.

Every collection type placed in each level at random, nested with random objects.

Objects including complex classes, loggers, functions, and more, that nothing else serializes.

Every object initialized at least once on every level.

Basically, "how can I make this as bad as possible?"

Then, I created an engine to beat it.

And battled it thousands of times, forcing the engine to successfully serialize it and deserialize it multiple times per battle. Not a single error was allowed to occur.

Once the engine won, I felt confident that I could serialize anything.

But even if I can't, I have written a special way for you to.

`__serialize__()` and `__deserialize__()` methods in your classes will be used first by `cerial`, before it uses the default handling.

You can use them to override the default serialization and deserialization behavior for your own objects.

As a bonus, `cerial` processes dataclasses 2x faster than `cloudpickle`, the fastest serializer for dataclasses.


(button)
Read more here.
(end of button)

(end of dropdown section for can't pickle)

(this is a dropdown section for filepaths)
## My filepaths don't work when I run my project on something else.

Do you ever pull a repo from your Windows PC at work and it doesn't work on your Mac at home?

Or, maybe your laptop at home is also Windows, but the project is placed in a different directory than the one you use at work.

And then everything breaks.

Solution: use `SKPath`.

`SKPaths` automatically detect your project root using a custom detection system, and calculate a path relative to your project root.

This way, as long as you have the same project, the paths will still work, regardless of where you are.

No need to convert paths between operating systems.

No need to worry about where your project is located.

No needing to manually convert paths to work correctly everywhere.

Cross-platform compatibility.

## I'm newer to programming and I'm having trouble organizing my `while` loop code in a way that makes sense to me.

Try using `Circuit` to manage your loops.

- cleaner code
- easy to think about
- automatic error handling

```python
from suitkaise import Circuit

results = []
circ = Circuit(shorts=3)

while circ.flowing:
    result = risky_operation()

    if result:
        results.append(result)
    
    else:
        circ.short()
```

## I hate having to write code to time things.

```python
from suitkaise import sktime

# automatically times the function every time it is called
@sktime.timethis()
def my_function():
    # Your real code here
    r_int = random.randint(0, 100)
    sktime.sleep(r_int)

# run my_function many times
for i in range(100):
    my_function()

# get stats
mean = my_function.timer.mean
stdev = my_function.timer.stdev
```

```python
from suitkaise import sktime

with sktime.TimeThis() as timer:

    r_int = random.randint(0, 100)
    sktime.sleep(r_int)

most_recent = timer.most_recent
first_time = timer.get_time(0)
```

## Something is lagging severely and I don't know what.

Just add `sktime.timethis()` to each function you want to time.

```python
from suitkaise import sktime

@sktime.timethis()
def potential_lagger_1():
    # Your real code here
    pass

@sktime.timethis()
def potential_lagger_2():
    # Your real code here
    pass

@sktime.timethis()
def potential_lagger_3():
    # Your real code here
    pass
```

Your program runs...

```python
# get stats
mean_1 = potential_lagger_1.timer.mean
mean_2 = potential_lagger_2.timer.mean
mean_3 = potential_lagger_3.timer.mean

print(f"Potential lagger 1: {mean_1:.3f}s")
print(f"Potential lagger 2: {mean_2:.3f}s")
print(f"Potential lagger 3: {mean_3:.3f}s")
```

## Some of my team uses `pathlib` and some use strings, and I am tired of converting back and forth.

And I don't want to use `pathlib.Path.resolve()` every single time.

Use `skpath.autopath()` to automatically convert paths to whatever the function accepts.

```python
from suitkaise import skpath

@skpath.autopath()
def my_function(path: str):
    
    # all Paths are converted to strings
    # all strings are left as is

@skpath.autopath()
def my_function_2(path: Path)

    # all strings are converted to Paths
    # all Paths are left as is
```

---

## Using `suitkaise` with AI

Currently (since I have no motion), AI agents like ChatGPT that you use with something like Cursor are not trained to use `suitkaise`.

Even with AI, using `suitkaise` benefits you. 

Why? Because I tried to have AI do all of these kinds of things for me and it failed miserably (I still say Please and Thank You, don't worry).

However, there are 2 ways to let AI use `suitkaise`:

1. Have it search this page! Copy this into your prompt:

```text
I would like you to understand and use the suitkaise modules in my project.

It is installable using `pip install suitkaise`.

Can you go to the website (suitkaise.info) and look at the "how to use" section for each module?
```

2. Download the official docs and place them in your project.

(Button) Download (end of button)

Or, run this as python code in your terminal:

```python
from suitkaise import docs

docs.download("path/where/you/want/them/to/go")

# auto send them to project root
docs.download()
```

In order for the docs to install outside of your project root:
```python
from suitkaise import docs, Permission

with Permission():
    docs.download("Users/joe/Documents")
```

They will appear as a folder in the specified directory.

---

### Has `suitkaise` solved your problem? We want to know!

That's the whole point of `suitkaise`, so yeah, let us know at `suitkaise@suitkaise.info`.



