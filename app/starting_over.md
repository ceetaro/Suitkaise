# Starting over (attempt 4)

while this third attempt went a lot better than the second one, there are still some issues that would better be resolved by starting over.

I have honed in on the fact that creating the event system first is the best idea,
but i did not create the correct framework for allowing it to be created.

here is what we definitely need to create before attempting to make the event system again:

## a base Reg class for registries, SKReg

since we have unique needs for how registries function in our system (one at a truly global level, one in SK internal domain and one in external user imported code domain), it might make sense to create a base singleton class that registries can build off of. to make this library ready, we can specify a root path, and all files in or under that root can access the registry.

## SKCereal, for internal and external serialization ✅ DONE!

lets create a custom serializer that uses cloudpickle for internal process communication, and a custom protobuf serializer for external serialization. Lets ensure that both will handle edge cases, signal running threads to stop and gather data so it can be serialized, and correctly serialize complex and dynamic objects.

## ADDED: SKGlobal and SKGlobalStorage
## SKRoot (IntRoot and ExtRoot moved to app specific)

Resource and project structure manager.

## SKFunction (formerly FunctionInstance) and SKFunctionBuilder

instead of using callables that require args and kwargs to be passed every time, we will standardize how functions are used, referenced, and passed in code.

Why are SKFunctions better?

SKFunctions make it easier to manage and create instances of functions with complicated arguments.
Instead of manually creating the arg tuple, you can simply add an argument by its parameter name and
SKFunction will automatically handle it from there.

with callables:
stored_callable: {
  'callable': my_function(),
  'args': (args),
  'kwargs': {kwargs}
}
and then having to do:
class.stored_callable['callable'](*stored_callable['args'], **stored_callable['kwargs'])

or unpack and then call,

you can just do:
my_function = SKFunction.get_function('my_function')
my_function.execute()

We already made a version of this with FunctionInstance and FunctionInstanceBuilder, but we should develop this further.

Here are some new ideas for upgrades and reworks, as well as new additions:

1. adding a type.

Currently, we are using a lot of Union[Callable, FunctionInstance], which would be Callable | FunctionInstance in 3.11. however, both of these are lengthy. lets create a type, AnyFunction, that will operate the same way, and also allows return type specification like the Callable would.

2. adding a decorator to convert callables to SKFunctions.

let's add a decorator, @convert_callables, that will convert any argued callables to SKFunctions automatically.

additionally, lets add the same concept as a utility function.

since we are standardizing the use of SKFunctions, callables being passed would likely be
functions with no positional args or kwargs. lets make sure everything becomes an SKFunction at the start of our functions and methods!

3. register multiple SKFunctions under the same callable.

we may want to register instances of functions with or without args and kwargs. for example, we might register an SKFunction with the callable do_work() and no args or kwargs, and then later register another instance with the same do_work() callable, but with some args and/or a kwargs dict. 

4. adding a decorator to automatically register a function as an SKFunction the first time it is called, and adding a method to register an SKFunction with the provided args and kwargs for the future before executing it.

@autoreg_SKFunction is a decorator that will register the decorated function as an SKFunction without args or kwargs the first time it is called.

say we just finished getting the necessary data to create a ui component across processes using a reconstruction method. it would be helpful and convenient to be able to register that exact reconstruction method with those exact args and kwargs so that the same ui component can be created later on.

note that we can also just register an SKFunction without executing it, but the above method would turn the 2 step process of 'register the SKFunction' and then 'execute the SKFunction' into just one step.

5. adding options for generators, lambdas and async functions.

create subclasses of SKFunction: SKGenerator, SKLambda, and SKAsync

6. ensuring SKFunction data can be correctly serialized, if needed.

SKFunctions need to travel across processes. We need to make sure that they can be correctly serialized.


### Testing SKFunction

SKFunction should be fully functional in all of these aspects before we continue. 


## Recreate ProcessManager and ThreadManager as SKProcess and SKThreading

With a recreated SKFunction system, we can now recreate the ProcessManager and the ThreadManager. Here is the updated idea:

- 1 main SKProcessCommander that works with two sub SKProcessManagers. One sub SKProcessManager is present in both the internal code and for external user imported code. It communicates things like how many processes can use how many resources on each side. It doesnt directly create processes, just manages what side can create n processes and how resources should be allocated.
- 2 SKProcessManagers that work to create, monitor, and shutdown processes cleanly. They connect to the highest level commander if there is one, but if there isn't (as in a user program is running outside of Suitkaise) they will initialize a commander themselves.
- Like before, we can have processes auto initialize things like BusStations and SKThreaders by registering init functions that each process should use no matter what.

- An SKThreader in every process, that handles the creation, monitoring, and requesting to stop/join of threads cleanly, as well as the initialization of any object necessary (like a Bus). These should automatically initialize things like a Bus.

### Testing SKProcess and SKThreading

Both of these should be fully functional and reviewed for performance optimizations before continuing.

## Create SKCycle

SKCycle is a combination of parts that work to create well structured loops, that can be performed across multiple processes and threads. It consists of:

- Cycle: the main execution engine that runs the structured workflow
- CycleBuilder: creates the execution structure with proper syncing
- CyclePart: represents an individual operation in the Cycle
- CycleRegistry: register CycleParts and Cycles

### 1. CyclePart

Represents a single task that needs to be executed as part of a larger workflow. It is essentially a single function/operation that accomplishes a specific goal. 

A CyclePart needs to know:
- what it should do
- where it should do it (what process)
- how it should handle errors or failures
- how long it should allow for execution before timing out

When you create a CyclePart, you can also register it in the registry.

Use SKFunctions when creating CycleParts, because the CyclePart wont directly perform the operation itself. Instead, it finds the component to execute the function, asks it to run the operation in a new thread, and waits for the execution to complete. Then, it collects results and errors.

Cycle cannot create new threads itself, but the function in the CyclePart can.

If something goes wrong, the CyclePart can retry until it reaches the timeout threshold.


### 2. CycleBuilder

CycleBuilders are context managers that take created CycleParts and combine them to create Cycles. They ensure that the Cycles have the correct structural logic to operate in order. 

How to build a Cycle:

Cycles have 2 measuring components, levels and positions, that enforce how the Cycle operates. You have 2 options at a given level and position: 
- add a part/cycle (cycle just adds its parts with level/position as its root level)
- split and add multiple parts/cycles

at level one, you must add a part, but you can split after that. when you split, that is what creates new positions. so if you...

add(the part, level=1, (default position)) at level 1
split([list of 3 parts], level=2, (default position)) at level 2

you have these level/positions currently filled:
1-1
2-1
3-1, 3-2, 3-3

so now at level 4 you would have to do...
add/split(the part(s), 4, 1), add/split(the part(s), 4, 2), or add/split(the part(s), 4, 3)

Build level by level.
- you can only add parts to the lowest level in each split. Plan in advance!
- once you have added a part or split at a position, that position is filled and can't have another part.
- when you need multiple parts at the same level and position, you must create them then using a split.

The CycleBuilder creates a tree-like structure to track the parts and splits you have added. 

Synchronization options (can be added to the Cycle itself or to single splits)
- Level sync: all parts from this root parts level must complete before a single part on the next level starts. applies to all levels onward.
- parallel sync: splits can complete in parallel and don't have to worry about other splits' progress. however, the cycle cannot start again until all parallel branches complete.
- sequential sync: force a part to wait for another part to finish before starting. 
- independent: all added parts run at their own pace and don't wait for other to complete before starting again.
- pipeline: instead of collecting results separately, you can create a pipeline from one part to another and it will pass its result directly to the requested part. the requested part will run a data validation method if it has one.
- conditional execution: this part and ones below it will only run if a condition is met.
- limit rate: only n number of parts can execute at once in this cycle, and others will just have to wait. other than this, respects other sync modes.

When you add parts with synchronization, build it using build() or build_and_register() and then you have a Cycle!

### CycleReg

Short for Cycle Registry, this is a central storage that keeps track of all registered CycleParts and Cycles. Allows the rest of the system under that domain to use them. Follows the 3 part singleton concept outlined throughout this doc.

When you build a CyclePart or Cycle, you can optionally register it. I did not include automatic registering to reduce unnecessary memory usage.

You can access a part or Cycle by the name you gave it when registering it.

### Cycle

The Cycle is the actual engine that runs your parts. It takes the data blueprint that you made in CycleBuilder and assembles the Cycle.

Here is how it will work:
1. organizes all parts into their correct levels and positions.
2. starting from level 0, it executes all parts according to sync modes set. if a sync mode is set for the whole Cycle, this will override the different modes set throughout the Cycle.
3. smartly keeps threads open if multiple parts need to execute in the same thread (part of the same component). or sends messages to an active thread in a group
4. ensures that set sync mode is being adhered to.
5. handles errors and retries part execution if the timeout hasn't been reached another attempt can reasonably be made in the remaining time.
6. if errors persist or timeouts happen, it will check if this part/branch has dependent parts and possibly stop the Cycle for parts under current level/pos. other independent parts of the Cycle will continue.

The Cycle will respect your open processes and threads, and send messages instead of just creating new threads.

Cycle will run in a continuous loop by default, but you can have a Cycle run once if you want.

#### Handling errors

When something goes wrong during a Cycle, it can handle the situation in many ways, depending on what has been set.

- Instant fail: stop the entire cycle when an error occurs. The cycle is in an error state when it finishes.
- Clean fail: other, independent parts keep going until they finish, but parts after/dependent on the part that caused the error are not run. Cycle is in an error state when it finishes.
- Skip: same as fail fast, but does not give Cycle error state.
- Retry: if this part fails and there is time for another possible attempt, then loop this part again.
- Fallback fail: returns a default value, and cycle finishes in error state.
- Fallback skip: same as Fallback fail, but does not give Cycle the error state.
- Propagate: if part raises an error, pass it as the result and let later parts decide to continue.

#### Data flow

- Input and output: each part can receive input and produce output. This allows you to pass data to other parts that might depend on it.
- Explicit pipeline dependincies: parts receiving data from a pipeline can validate the data they receive.
- centralized data: all parts in a Cycle run can access a shared data repository. this allows for flexible data sharing/access.
- accessing data from other branches: you can access data from any completed part, regardless of level or position. you can also ask a parent for data and it can give you a child's data if it matches the conditions.
- when parts finish, their data gets validated.



## new considerations

### upgrade to using Python 3.11

right now, we are using python 3.9. lets upgrade to using 3.11.

### creating a suitkaise library

We should work to create an official library first, with components that sync to a devwindow for the user. things like SKFunction, SKColor, SKCycle, etc. that can be used without the need of an app user interface. Add the library utilities here:

- SKReg
- SKRoot
- SKFunction
- SKProcess
- SKThreading
- SKCycle
- (and more)

any generalized components that any user could import and use should go here. the event system will not go in the library, but will use the library utilities.

### testing, testing, testing (and incremental implementation)

instead of creating a module and then testing it after, or creating a complex user interface and testing it after, lets slow down the process and test as we go. even if it doesnt make sense to test, test. Even if it feels a little abstract, testing will give us a much more solid understanding of exactly what is happening, leading to less overwhelm.

### using multiprocessing.Manager()
singletons will not cross processes without help. we should use multiprocessing.Manager() to...

1. create cross process global dictionaries holding the registries we need each process to be able to access.

this includes:
- a top level global for the Bridge
    - another global if we have registries or other similar singletons that both internal and external code will use.

- 2 more global dicts, internal and external, that store registries for each domain respectively

2. sync IntStation and ExtStation cleanly

- instead of sending all events to the bridge, having the bridge process them, and then send them back, we can use the current BridgeDirection to just sync them using the Manager().
  - Bridge still exists as a rules engine and controls how data flows
  - actual event data flows through shared Manager() objects
  - stations respect bridge rules but exchange directly

### adding kwargs to functions where it makes sense to

in the upcoming attempt, lets utilize kwargs more often, for things like base classes or receiving classes and their metadata as kwargs.






