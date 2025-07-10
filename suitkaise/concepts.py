# process pool concept

# --------

# NOTE: we are changing ProcessConfig to PConfig
# NOTE: we are changing QuickProcessConfig to QPConfig

# to support upcoming concepts, 
# we need to accept a key during xprocess.create_process().

# from...
xprocess.create_process(Process, PConfig)

# to...
xprocess.create_process(key="a_key", Process, PConfig)

# and the way we handle results will change as well.

# before, we just returned the result on its own, but now:
# we return pdata class, with result as an entry
class pdata:

    def __init__(self, pname, pid, num_loops):

        self._pname = pname
        self._pid = pid
        self._num_loops = num_loops
        self._completed_loops = None
        self._result = None # eventually result from __result__ or error

    # as well as methods for updating metadata and to_dict

# and access result like this:
with CrossProcessing() as xp:

    # returns pdata now!
    process1 = xprocess.create_process(key="a_key", Process, PConfig)

# raises error if process1.result is an error
result1 = process1.result


# ~~we should also add a property method to get depth level of current process!~~
# --------

#  adding a standardized PTask type (key, Process classes, and PConfigs)
tasks: list[PTask]

results = {}
errors = {}

# pool processes cannot loop
with ProcessPool(size=8) as pool:

    for task in tasks:
        # submit() takes a key, Process class and PConfig just like create_process()
        # can also take the PTask class
        pool.submit(task)


# accessing data returned using __result__:
try:
    result = pool.get_result("key" or task_num)
    # returns a class PTaskResult with the data in pdata's result
    # {
    #   "key": key
    #   "pclass_name": Process class name
    #   "worker_pid": worker process's pid
    #   "worker_number": 1-8
    #   "task_num": if second task SUBMITTED, would be 2
    #   "result": the result or error being returned (error gets raised as PoolTaskError)
    # }

    results.append(result) # or results.append(result.result) if you want raw result data


except PoolTaskError as e:
    # pool task error will also inform you of what failed:
    # Process class name
    # task number
    # failing worker process number and id
    # error(s) that was/were caught during task to raise that PoolTaskError
    # and then the message that user adds to error.
    errors.append(result)


# or... all at once!
task_results = ProcessPool.submit_all(List[PTask]=tasks, size=4, parallel=False)
# returns all results in a list of PoolTaskResults
# if there are multiple errors, they are all collected into one PoolTaskError and raised at once

# expected behavior:
try:
    task_results = ProcessPool.submit_all(a Plist of tasks=tasks, size=4)

except PoolTaskError as e:
    for result in task_results:
        if result.error:
            # do something with each error specifically if you want


# !!! context manager gives control, but we still have that easy one liner! !!!

# the only difference is that we keep the worker processes active until all tasks are complete.

# once all tasks are finished, all the processes rejoin gracefully just like usual.

# subprocesses at depth 2 (deepest possible layer) CANNOT create process pools, as this 
# would go over the maximum XPROCESS_DEPTH.

# process pool can support parallelism! if there are 8+ tasks and we have 8 workers,
# then all 8 should be active, but wait until all are empty until starting next batch.
# however, if we are creating a pool with the one liner:
task_results = ProcessPool.submit_all(only 5 tasks) # default workers (size) is 8

# then we will only create 5 processes!

# additionally, empty worker processes will be rejoined fully if there are no more tasks
# left to do.

# parallelism in process pools:
# base ProcessPool assumes asynchronous behavior, but can be changed within manager.

with ProcessPool(size=8) as pool: # starts in async mode


# EXAMPLE 1
    # can still manipulate order asynchronously
    sent_back = []
    for task in tasks:
        if isinstance(task.pclass, LongerExpensiveOperation) and task not in sent_back:

            # send to back of list
            tasks.remove(task)
            tasks.append(task)
            sent_back.append(task)
            break

        elif not isinstance(task.pclass, LongerExpensiveOperation):
            pool.submit(task)

        # we now only have LongExpensiveOperations left
        else:
            pool.submit_multiple(tasks)

# EXAMPLE 2
    sent_back = []
    for task in tasks:
        if isinstance(task.pclass, ParallelOperation) and task not in sent_back:

            # send to back of list
            tasks.remove(task)
            tasks.append(task)
            sent_back.append(task)
            break

        # catch for when all that is left is ParallelOperation
        elif isinstance(task.pclass, ParallelOperation) and task in sent_back:
            break

        else:
            pool.submit(task)

    pool.set_parallel()
    # remaining are all ParallelOperation and get completed in parallel
    # submit them all at once if you want
    pool.submit_multiple(tasks)

    # these will start and finish 8 at a time!

    # or...
    pool.set_parallel(size=2)
    # remaining are all ParallelOperation and get completed in parallel
    # but, we want them completing only 2 at a time
    pool.submit_multiple(tasks)

    # these will start and finish ONLY 2 at a time!      

    # to revert to async behavior:
    pool.set_async()

    # additionally, 8 processes remain open even if parallel size is 2
    # because our pool size is 8 


# we also have some explicit classes where behavior cant change:

# if the second process finishes before all others, it can take the next task immediately
with AsyncProcessPool(size=6) as pool:

    for task in tasks:
        pool.submit(task)

    # block will still wait to exit until all workers are in shutdown ready state



# if the second process finishes before all others, it has to wait for them to finish.
with ParallelProcessPool(size=4) as pool:

    for task in tasks:
        pool.submit(task)

    # fills first four tasks before starting next 4

# -----------------
# set_parallel and set_async will exist in CrossProcess and SubProcess as well, 
# not ONLY ProcessPool!

# question: how exactly should we control parallelism or process execution in general in the 
# main process creation managers, CrossProcessing and SubProcessing? what exactly is parallelism
# outside the context of a processing pool?

# how do we control processes that depend on other processes? just conditionals and
# set_parallel and set_async?

# we could add things like: 

xp.wait(seconds)
xp.wait_for("a_key" or list["of_keys"]) # wait until one or more processes rejoin

# for dependency tracking/control,
# but both of these could just be handled with conditional logic and might complicate things
# i want to see how powerful this system is without extra control other than set+parallel/async,
# just using clean, strong base logic

# do you think we should create xp.wait and wait_for? (and their internal counterparts)


# question: is parallelism just processes running at the same time, or is it processes starting
# and ending in a group together?

# Implementation

# Phase 1: Core Changes

# Add key parameter to create_process()
# Implement pdata class (should it be PData or pdata?)
# Rename configs (ProcessConfig → PConfig, QuickProcessConfig → QPConfig or QConfig)
# Update result handling to return PData

# Phase 2: Process Pool

# Implement PTask and PTaskResult classes
# Create ProcessPool with async/parallel modes
# Add submit(), submit_multiple() and submit_all() methods
# submit_all() is only for the one line ProcessPool creation
# Implement PoolTaskError handling

# Phase 3: Parallelism Control

# Add set_parallel()/set_async() to CrossProcessing
# Implement group coordination logic
# Add specialized pool classes (AsyncProcessPool, ParallelProcessPool)

# we are NOT adding wait() and wait_for() right now.




# CURRENT basic concepts (fdl, sktime, skpath)




# FINALIZED basic processing concepts, before adding data syncing with Manager
#   or creating the api












# expanded SKGlobal and SKTree concepts