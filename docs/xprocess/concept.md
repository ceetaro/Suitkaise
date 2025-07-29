# XProcess Concept

## What is xprocess (and skthreading)?

xprocess is suitkaise's process and thread manager. It allows you to create new processes similar to multiprocessing, but also allows you to add tasks to complete when initializing every new process/thread. Additionally, it will automatically sync serializable data to other processes (through the process that contains what is right now called "top level storage"). It also automatically handles process crashes or blocks due to errors, is able to report processes' statuses, recall processes, auto create background threads in processes, etc.

## Core Philosophy

Transform multiprocessing from expert-level complexity to beginner-friendly magic through declarative configuration and automatic lifecycle management.

## Key Features

- **Process Lifecycle Management**: Sophisticated process lifecycle with automatic sync
- **Automatic Data Sync**: Between processes through global storage
- **Process Crash Handling**: Automatic recovery from crashes and errors
- **Background Thread Creation**: Auto-create background threads in processes
- **Process Status Reporting**: Monitor and recall processes
- **Configurable Join Behavior**: Time-based, iteration-based, or manual control

## Process Lifecycle Architecture

Four-phase process execution:
1. **OnStart()** - Execute once on process creation
2. **BeforeLoop()** - Execute before each function iteration  
3. **[Main Function Execution]** - Your actual work
4. **AfterLoop()** - Execute after each function iteration
5. **OnFinish()** - Execute once before process termination

## Advanced Features

- Automatic data sync between processes through global storage
- Process crash handling and recovery
- Background thread auto-creation within processes
- Process status reporting and recall capabilities
- Configurable join behavior (time-based, iteration-based, manual)

## Design Philosophy

The goal is to make sophisticated multiprocessing accessible to developers of all skill levels while maintaining the power needed for complex applications.