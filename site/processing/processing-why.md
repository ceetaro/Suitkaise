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

So, you have to turn to `multiprocessing` for computational power.

And now you have to deal with so much more.

(start of dropdown)
1. `pickle`

`PicklingError: Can't pickle your object, hahahahaha! Loser.`

Eveything passed from one process to another must be serializable, usually via `pickle`.

But this means that so many essential objects in Python just can't be passed to a different process.





