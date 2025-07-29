# XProcess Concept

## What is xprocess (and skthreading)?

xprocess is suitkaise's process and thread manager. It allows you to create new processes similar to multiprocessing, but also allows you to add tasks to complete when initializing every new process/thread. Additionally, it will automatically sync serializable data to other processes (through the process that contains what is right now called "top level storage"). It also automatically handles process crashes or blocks due to errors, is able to report processes' statuses, recall processes, auto create background threads in processes, etc.

## Core Architecture

### Process Setup Options

There are two main approaches to setting up processes:

#### Option 1: Context Manager Approach
Using `xp.ProcessSetup()` with context managers for different lifecycle phases:
- `xp.OnStart()` - Results added to config going into main function kwargs
- `xp.BeforeLoop()` - Results added to this loop's kwargs  
- `xp.AfterLoop()` - Results optionally added to next loop kwargs
- `xp.OnFinish()` - Final cleanup and processing

#### Option 2: Class-Based Approach
Inheriting from `Process` class with dunder methods:
- `__init__()` - Process setup
- `__beforeloop__()` - Called before every loop iteration
- `__afterloop__()` - Called after every loop iteration  
- `__onfinish__()` - Called when process finishes

## Process Configuration

Processes can be configured with special kwargs:
- `join_in`: Join (end process) in n seconds, None being no auto join
- `join_after`: Join after n function loops, None being no auto join

## Integration with SKTree

xprocess integrates seamlessly with sktree for global storage:
- Automatic data syncing between processes
- Path-based organization of process data
- Metadata tracking for process cleanup
- Cross-process communication through shared storage

## Threading Integration

SKThreading provides easy threading and thread management:
- Create single threads or thread pools
- Configurable looping behavior
- Graceful thread termination with `rejoin()`
- Same lifecycle approach as processes but for threads