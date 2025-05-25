# add license here

# suitkaise/sklock/with_lock.py

"""
Module containing the withlock decorator and the SKLock class decorator.

withlock is a decorator that automatically locks the function it decorates.
SKLock is the class version of withlock.

these use context managers to ensure that locks are used when class or instance
variables get modified, to ensure thread safety. they know when to lock and when to unlock
by scanning an ast node.

"""

# NEEDS:
# 



