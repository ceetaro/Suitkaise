# add license here

# suitkaise/sklock/with_lock.py

"""
Module containing the withlock decorator and the SKLock class decorator.

withlock is a decorator that automatically locks the function it decorates.
SKLock is the class version of withlock, that scans the class for methods that 
modify class or instance variables, and automatically applies the withlock to 
those methods.

these use context managers to ensure that locks are used when class or instance
variables get modified, to ensure thread safety. they know when to lock and when to unlock
by scanning an ast node.

also, we can add another decorator that can handle deadlocks or waiting for locks to be released.

lets also add lock tracking if possible, tracking when locks are acquired and released,
and when they are held by which threads.

"""

# NEEDS:
# 



