# `sktime` Concept

## Table of Contents

1. [Overview](#1-overview)
2. [Core Concepts](#2-core-philosophy)
3. [Basic Time Operations](#3-basic-time-operations)
4. [`Yawn` Class - Conditional Sleep](#4-yawn-class---conditional-sleep)
5. [`Timer` Class](#5-timer-class---statistical-analysis)
6. [`TimeThis` Context Manager](#6-timethis-context-manager)
7. [`timethis` Decorator](#7-enhanced-timethis-decorator)
8. [Why using `sktime` is great](#8-why-using-sktime-is-better)
9. [Real Examples](#9-real-examples)
10. [Function-by-Function Examples](#10-function-by-function-examples)
11. [Performance Considerations](#11-performance-considerations)
12. [Importing `sktime`](#12-importing-sktime)

***For a quick read of the most important parts, see sections 7-12.***

## 1. Overview

`sktime` provides comprehensive timing functionality that goes far beyond basic `time.time()` calls, offering specialized classes and utilities for different timing scenarios. It's designed to <u>**save you time**</u> and be a foundational piece in your development process.

## 2. Core Concepts

`sktime` transforms timing from a manual, error-prone process into an *intuitive, powerful toolkit* that is extremely easy to use. Whether you need quick performance measurements, sophisticated statistical analysis, or specialized timing behaviors like rate limiting, `sktime` provides the right tool for the job in as few lines of code as possible.

People and AI alike can easily understand the concepts in `sktime` much better than reading several files of time related code, and `sktime` is much better than simple `time.*()` calls.

**Key principles:**
- **Simplicity**: Common operations are 1-2 lines, complex operations are less than 10.
- **Flexibility**: Order-independent elapsed time calculation and multiple usage options for `Timer`
- **Instant statistics**: Built-in stat analysis for performance monitoring and debugging
- **Zero overhead**: Works right off import with low resource usage
- **Powerful**: Pro-grade tools for performance monitoring that can be used even by complete beginners

## 3. Basic Time Operations

### Core Functions
- `sktime.now()`: Current Unix timestamp with clear naming (equivalent to `time.time()`)
- `sktime.get_current_time()`: Longer, more explicit alias (equivalent to `time.time()`)
- `sktime.sleep(seconds)`: Sleep functionality integrated with SKTime naming (equivalent to `time.sleep()`)
- `sktime.elapsed(time1, time2)`: Order-independent elapsed time calculation

You can also just use the `time` module directly with `sktime`, but that requires an extra import.

The `elapsed` function is super easy to use:
- uses `math.fabs()` for best precision when calculating absolute value of floats

```python
from suitkaise import sktime

start = sktime.now()

sktime.sleep(2)

elapsed = sktime.elapsed(start) # end time automatically set to current time

# with 2 times
start = sktime.now() # 100
sktime.sleep(2)
end = sktime.now() # 102

elapsed1 = sktime.elapsed(start, end)  # |100 - 102| = 2
elapsed2 = sktime.elapsed(end, start)  # |102 - 100| = 2

elapsed3 = sktime.elapsed(start)       # Uses current time as end
```

## 4. `Yawn` Class - Conditional Sleep

Yawn lets you add delays that only happen after multiple calls, instead of delaying every single time. Use this to rate limit requests to APIs or manage program pauses due to user input, wait for processing to finish, etc. Also helpful for reducing memory pressure during high usage periods.

**When you might use Yawn:**
- Limit API calls to stay under rate limits
- Delay request batches to websites to avoid being blocked
- Let the system cool down during high usage periods
- Retry failed network requests with increasing delays

### Basic Example
```python
from suitkaise import sktime

# use it to sleep a program using too much memory
mem_use_limiter = sktime.Yawn(sleep_duration=3, yawn_threshold=5)

# while the program is running, this loop will not do work while the memory usage is too high
while program_running:
    if mem_usage > max_recommended_mem:
        mem_use_limiter.yawn()
        sktime.sleep(0.5)
    else:
        do_work() # run your program code
        sktime.sleep(0.5)
```

### Web Scraping Example
```python
from suitkaise import sktime
import requests

# Real example: Web scraping with respectful rate limiting
# Sleep for 10 seconds after every 20 requests
rate_limiter = sktime.Yawn(sleep_duration=10, yawn_threshold=20, log_sleep=True)

urls_to_scrape = [
    "https://api.github.com/users/octocat",
    "https://api.github.com/users/torvalds",
    # ... hundreds more URLs
]

for url in urls_to_scrape:
    # Make the request
    response = requests.get(url)
    process_response(response)
    
    # Check if we should take a break
    rate_limiter.yawn()  # Only sleeps after 20 calls
    
    # Small delay between each request
    sktime.sleep(0.1)
```

### Image Processing Example
```python
from suitkaise import sktime

# Real example: File processing with cooling breaks  
processor = sktime.Yawn(sleep_duration=5, yawn_threshold=50)

for image_file in large_image_directory:
    # Process intensive image operations
    resize_image(image_file)
    apply_filters(image_file)
    
    processor.yawn()  # Take a 5-second break every 50 images
```

**Key features:**
- Automatic counter reset after sleep
- Optional logging when sleep occurs
- No sleep overhead until threshold is reached

## 5. `Timer` Class

The `Timer` class makes it easy to time anything and everything. It gives you high level features with only a few lines of code. There are multiple ways to use it, including manual timing using `start()` and `stop()`, lap timing using `lap()`, using it in the `TimeThis` context manager, and using it inthe `@timethis` decorator. It also gathers comprehensive statistics for you and has pause/resume functionality.

**When you might use `Timer`:**
- Need to figure out what part of your code is causing lag spikes due to slow operations
- Need to handle consistent timing without inconsistencies like user input
- Timing something over and over to see if it's getting faster or slower
- Using multiple timers to time different parts of the same code
- Collect statistics on everything during runtime
- Optimize your code for performance based on results from Timers

### Basic `Timer` Usage

#### Using `start()` and `stop()`
```python
# Example 1: Using start() and stop()
from suitkaise import sktime

timer = sktime.Timer()
timer.start()


# Download a large file
current_file = download_file("https://example.com/data.zip")

# Pause timer while user decides what to do next
timer.pause()

user_choice = input(f"Process {current_file} now? (y/n): ")  # This time won't be counted

# Resume once input is received
timer.resume()

# Process the file
if user_choice.lower().strip() == 'y':
    process_downloaded_file()

elapsed = timer.stop()  # Records measurement in statistics
print(f"Total processing time: {elapsed:.2f}s (excluding user input)")
```

#### Using `lap()`
```python
from suitkaise import sktime

timer = sktime.Timer()
timer.start()

# list of files to process
files = ['data1.csv', 'data2.csv', 'data3.csv']

# process each file
for filename in files:
    process_csv_file(filename)
    timer.lap()  # Records time for this file and continues

# stop the timer
timer.stop()
print(f"Average file processing: {timer.mean:.2f}s")
print(f"Slowest file: {timer.slowest_time:.2f}s")
```

#### Using `add_time()` to add pre-measured time floats
```python
# Example 3: Adding pre-measured times
from suitkaise import sktime

timer = sktime.Timer()

# time something as normal...

timer.add_time(1.5)  # Add a time you measured elsewhere
timer.add_time(2.1)  # Add another measurement from somewhere else
print(f"Average of added times: {timer.mean:.2f}s")
```

### All Available `Timer` Properties and Methods

#### **Core Operations**
- `timer.start()` - Start timing a new lap
- `timer.stop()` - Stop timing and record lap 
- `timer.lap()` - Record lap and continue timing
- `timer.pause()` - Pause the current timing
- `timer.resume()` - Resume timing (excludes paused time)
- `timer.add_time(seconds)` - Manually add a time float
- `timer.reset()` - Clear everything and reset timer

#### **Measurement Access**
- `timer.num_times` - Number of times recorded
- `timer.most_recent` - Most recent time
- `timer.most_recent_lap` - Index of most recent time
- `timer.result` - Most recent time  
- `timer.get_time(index)` - Get time by standard 0-based index

#### **Time Totals**
- `timer.total_time` - Sum of all times
- `timer.total_time_paused` - Total time spent paused

#### **Statistical Properties**  
- `timer.mean` - Average of all times
- `timer.median` - Median of all times
- `timer.min` / `timer.fastest_time` - Minimum time
- `timer.max` / `timer.slowest_time` - Maximum time
- `timer.stdev` - Standard deviation
- `timer.variance` - Variance
- `timer.slowest_lap` - Index of slowest time
- `timer.fastest_lap` - Index of fastest time

#### **Advanced Analysis**
- `timer.percentile(percent)` - Calculate any percentile (0-100)
- `timer.get_statistics()` - Get comprehensive statistics dict

#### **Misc**
- `timer.original_start_time` - Original start time of the timer
- `sktime.now() - timer.original_start_time` - Real world time passed since timer first started

### Statistical Analysis Features

After accumulating measurements, `Timer` provides comprehensive statistics:

```python
# Run multiple measurements
for i in range(100):
    timer.start()
    expensive_operation()
    timer.stop()

# Get detailed statistics
stats = timer.get_statistics()

# print stats like this:
print(f"Number of measurements: {stats['num_times']}")

# or directly reference single stat properties
print(f"Number of measurements: {timer.num_times}")
```

## 6. `TimeThis` Context Manager

`TimeThis` is a context manager that puts a timer around a block of code using Python's `with` statement and `sktime.Timer`. It automatically starts timing when you enter the block and stops when you exit. It's perfect when you want to time something specific without manually calling `start()` and `stop()`.

**When you might use `TimeThis`:**
- Timing small blocks of code inside functions
- Timing large chunks of code consisting of multiple functions
- Timing how long a thread is active
- Organize timers by using them inside context managers
- Add multiple measurements to the same timer from different blocks of code
- Quickly test or script different approaches and test each one

### `TimeThis` without `Timer` Argument (Creates New `Timer` Each Time)

When used without a `Timer` argument, `TimeThis` creates a new `Timer` instance for each context. This means each usage is independent with separate statistics. This will only give you 1 time measurement to access.

#### Example 1 - Different Compression Algorithms
```python
from suitkaise import sktime

# Real example: Testing different compression algorithms
with sktime.TimeThis() as timer:
    compress_file_with_gzip("large_dataset.csv")

print(f"GZIP compression took: {timer.most_recent:.3f}s")

# This creates a completely different timer instance  
with sktime.TimeThis() as timer2:
    compress_file_with_lzma("large_dataset.csv")
    
print(f"LZMA compression took: {timer2.most_recent:.3f}s")

# Each timer is independent - perfect for comparing approaches
print(f"GZIP timer has {timer.num_times} measurement")   # 1
print(f"LZMA timer has {timer2.num_times} measurement")  # 1
```

#### Example 2 - User Interaction
```python
# Real example: Database query with user interaction
with sktime.TimeThis() as timer:
    results = database.query("SELECT * FROM users WHERE active=1")
    
    # Pause timing while user reviews results
    timer.pause()
    user_wants_export = input(f"Found {len(results)} users. Export to CSV? (y/n): ")
    timer.resume()
    
    if user_wants_export.lower() == 'y':
        export_to_csv(results)
    
print(f"Database operation took: {timer.most_recent:.3f}s (excluding user input)")
```

### `TimeThis` With Explicit `Timer` (accumulates statistics)

When provided with an explicit `Timer`, `TimeThis` uses that timer to accumulate statistics across multiple contexts.

#### Example 1 - Multiple API Calls
```python
# Real example: API call performance monitoring
api_timer = sktime.Timer()

# Time multiple API calls to build statistics
with sktime.TimeThis(api_timer) as timer:
    response = requests.get("https://api.github.com/users/octocat")

print(f"API call 1: {timer.most_recent:.3f}s")

with sktime.TimeThis(api_timer) as timer:
    response = requests.get("https://api.github.com/users/torvalds")

print(f"API call 2: {timer.most_recent:.3f}s")

with sktime.TimeThis(api_timer) as timer:
    response = requests.get("https://api.github.com/users/gvanrossum")

print(f"API call 3: {timer.most_recent:.3f}s")

# Now analyze API performance across all calls
print(f"Total API calls: {api_timer.num_times}")  # 3
print(f"Average response time: {api_timer.mean:.3f}s")
print(f"Fastest API call: {api_timer.fastest_time:.3f}s")
print(f"Slowest API call: {api_timer.slowest_time:.3f}s")
```

#### Example 2 - Database Query Performance
```python
# Real example: Database query performance
db_timer = sktime.Timer()

queries = [
    "SELECT * FROM users WHERE active=1",
    "SELECT COUNT(*) FROM orders WHERE date >= '2024-01-01'", 
    "SELECT p.name, SUM(oi.quantity) FROM products p JOIN order_items oi ON p.id=oi.product_id GROUP BY p.id"
]

for query in queries:
    with sktime.TimeThis(db_timer):
        database.execute(query)

print(f"Average query time: {db_timer.mean:.3f}s")
print(f"Slowest query took: {db_timer.slowest_time:.3f}s")
```

### `TimeThis` with `pause()`, `resume()`, and `lap()` Operations

The timer returned by `TimeThis` supports all `Timer` operations including `pause()`, `resume()`, and `lap()`:

```python
shared_timer = sktime.Timer()

with sktime.TimeThis(shared_timer) as timer:
    setup_work()
    
    # Pause during user interaction
    timer.pause()
    user_choice = get_user_input()  # Time excluded
    timer.resume()
    
    process_user_choice(user_choice)
    
    timer.lap()  # Record intermediate measurement
    
    finalize_work()
    # Context exit records final measurement

print(f"Measurements recorded: {shared_timer.num_times}")  # 2 (lap + final)
print(f"Total processing time: {shared_timer.total_time:.3f}s")
print(f"Time spent paused: {shared_timer.total_time_paused:.3f}s")
```

### When to Use Each Approach

**Use `TimeThis()` without `Timer` when:**
- You want quick, one-off timing measurements
- Each timing is independent and doesn't need comparison
- You're doing simple benchmarking or debugging

**Use `TimeThis(timer)` with explicit `Timer` when:**
- You want to accumulate statistics across multiple runs
- You need to compare performance across different executions
- You're doing statistical analysis or performance monitoring
- You want to track performance over time

## 7. `@timethis` Decorator

The `@timethis` decorator supports both explicit `Timer` instances and automatic global timer creation, providing the ultimate convenience.

### Auto-created timer (quickest way to use `Timer`)
```python
@sktime.timethis()  # No timer argument - creates global timer automatically
def quick_function():
    # Code to time
    pass

# Call the function
quick_function()

# Access the auto-created timer with super simple access
print(f"Last execution: {quick_function.timer.most_recent:.3f}s")

# Call multiple times to build statistics
for i in range(100):
    quick_function()

print(f"Average: {quick_function.timer.mean:.3f}s")
```


### Explicit `Timer` (for gathering data from multiple functions)
```python
performance_timer = sktime.Timer()

@sktime.timethis(performance_timer)
def critical_function():
    # Important code here
    pass

# Build statistics over many calls
for i in range(1000):
    critical_function()

# Analyze performance
print(f"Average execution: {performance_timer.mean:.3f}s")
print(f"Slowest execution: {performance_timer.slowest_time:.3f}s")
```

**Global `@timethis` timer naming convention (for debugging):**
- Module-level functions: `module_function_timer`
- Class methods: `module_ClassName_method_timer`
- Each function gets its own dedicated timer
- Zero runtime overhead looking up the timer (resolved at decoration time)

## 8. Why using `sktime` is great

`sktime` eliminates the frustration of timing code manually. Instead of importing `time`, calculating differences, worrying about order, and building your own statistics - you just use `sktime` and get the same results immediately. Even more convenience is offered to you in the form of the `@timethis` decorator, which you can just slap on a function and get all the main benefits of the `Timer` class.

**What makes it so easy:**
- **One import for everything**: Import `sktime` and you have all timing tools ready
- **No setup required**: Can work instantly with smart defaults - zero or minimal configuration needed (great for beginners as well)
- **Order doesn't matter**: Functions like `elapsed()` can take just a start time and insert current time automatically
- **Smart**: `Timer` knows when it is paused, and `Yawn` knows when to sleep.
- **Error handling**: Errors are handled automatically, enforcing good coding practices and dealing with type mismatches.
- **Real-world ready**: Handle rate limiting, performance monitoring, and user interactions easily
- **AI friendly**: AI agents and chatbots don't have to worry about replicating complex timing when working with code, they can just use it simply like you do.

***It's the simplicity of the code versus the complexity of the result - it will save you a bunch of time and effort, and new developers will have a much easier time outputting professional grade content!***

## 9. Real Examples

### Beginner/Learning Projects

#### 1. Homework Script Performance - "Why is my code so slow?"
**Problem:** Script works but takes forever, and you don't know which part is being slow. Grade somewhat depends on code performance, if your professor notices that it's visually slow or laggy, you'll get a lower grade. Without `sktime`, you don't have the skills to create a working timing system to find the issue.
```python
from suitkaise import sktime

@sktime.timethis() # just add this!
def read_csv_file():
    with open("student_grades.csv") as f:
        return f.readlines()

@sktime.timethis()
def calculate_averages(lines):
    grades = []
    for line in lines[1:]:  # Skip header
        student_grades = [float(x) for x in line.strip().split(',')[1:]]
        grades.append(sum(student_grades) / len(student_grades))
    return grades

@sktime.timethis()
def write_results(averages):
    with open("averages.txt", "w") as f:
        for avg in averages:
            f.write(f"{avg:.2f}\n")

# Run your homework script
data = read_csv_file()
averages = calculate_averages(data)
write_results(averages)

# Instantly see what's slow - no complex setup needed!
print(f"Reading CSV: {read_csv_file.timer.mostrecent:.3f}s")
print(f"Calculating: {calculate_averages.timer.mostrecent:.3f}s")  
print(f"Writing results: {write_results.timer.mostrecent:.3f}s")
# Output: "Calculating: 2.456s" - found your issue!
```

#### 2. Web Scraping
**Problem:** You are a professional Pokemon player using a third-party website to practice for an upcoming tournament, and you want to gather data from other players at the top level by recording the data from their matches. You want to analyze as many as possible, but making requests to search for replays too fast is disrespectful and could get you banned.
```python
from suitkaise import sktime
import requests

# Be respectful - pause 10 seconds after every 10 requests
rate_limiter = sktime.Yawn(10, 10, log_sleep=True)

def record_battle():
    rate_limiter.yawn()  # Prevents bot detection
    # find ongoing battles that have at least one player with rating 1800 or higher
    url = find_ongoing_battle(rating=1800)
    battle_ongoing = requests.get(url)
    if battle_ongoing:
        # create a thread to record this battle
        create_recording_thread(url)
    sktime.sleep(0.5) # wait 0.5 seconds between requests

# Every 10 requests, sleep for 10 seconds so that more battles can start and requests aren't spammed
```

#### 3. Timed SAT Prep Application
**Problem:** You are developing software to help students prepare for the SAT, and you want to easily time how long it takes them to answer each question, as the SAT itself is timed.
```python
from suitkaise import sktime

def run_quiz():
    quiz._timer = sktime.Timer()
    
    quiz._timer.start()
    
    for question_num, question in enumerate(quiz.quiz_questions, 1):
        # display question and wait for user to answer
        answer = quiz._display_question(question)

        # once user answers, record the time and pause for explanation
        quiz._timer.pause()

        # process answer and explain
        quiz._process_answer_and_explain(answer)
        if answer.correct:
            sktime.sleep(1) # wait 1 second before proceeding to next question
        else:
            sktime.sleep(10) # wait 10 seconds before allowing them to proceed to next question

        quiz._open_next_question()
        while not quiz._proceed_to_next_question():
            if quiz._user_wants_to_quit():
                break
            else:
                sktime.sleep(0.1) # wait 0.1 seconds

        quiz._timer.lap()
        quiz._timer.resume()

    total_time = quiz._timer.stop()
    
    # Get detailed timing stats
    print(f"Total answering time: {total_time:.1f} seconds")
    if total_time / 60 > 45:
        print(f"Quiz took {total_time / 60:.1f} minutes, which is over the 45-minute allotted time.")

    print(f"Average per question: {quiz._timer.mean:.1f}s")
    
    # Find your slowest question
    print(f"Slowest question took: {quiz._timer.slowest_time:.1f}s")
    print(f"Fastest question took: {quiz._timer.fastest_time:.1f}s")
    print(f"Total questions: {quiz._timer.num_times}")
```

### Professional/Advanced Projects

#### 4. "Why is my website so slow?" - Zero-Setup Performance Monitoring
**Problem:** Users complaining about slow website, need to find bottlenecks without complex APM tools.
```python
from suitkaise import sktime
from flask import Flask

app = Flask(__name__)

@app.route('/api/search')
@sktime.timethis()  # Just add this decorator - that's it!
def search_products():
    # Your existing code doesn't change at all
    results = database.query("SELECT * FROM products WHERE...")
    return {"products": results}

@app.route('/api/checkout')
@sktime.timethis()  # Every function gets its own timer automatically
def process_checkout():
    # Complex checkout logic
    validate_payment()
    update_inventory()
    send_confirmation_email()
    return {"success": True}

@app.route('/debug/performance')
def show_performance():
    """Check this URL to see what's slow"""
    return {
        "search_endpoint": {
            "avg_time": f"{search_products.timer.mean:.3f}s",
            "slowest_call": f"{search_products.timer.slowest:.3f}s",
            "total_calls": search_products.timer.count,
            "last_24h_calls": "TODO: filter by timestamp"
        },
        "checkout_endpoint": {
            "avg_time": f"{process_checkout.timer.mean:.3f}s",
            "slowest_call": f"{process_checkout.timer.slowest:.3f}s", 
            "total_calls": process_checkout.timer.count
        }
    }
    # Visit /debug/performance to instantly see: "checkout taking 3.2s avg!"
```

#### 5. Database Query Optimization - "Which queries are killing us?"
**Problem:** Database getting slower, need to identify problem queries without complex monitoring.
```python
from suitkaise import sktime
import sqlite3

# Just wrap your existing database class
class DatabaseConnection:
    @sktime.timethis()
    def get_user_profile(self, user_id):
        # Your existing query - no changes needed
        return self.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    
    @sktime.timethis() 
    def get_user_orders(self, user_id):
        # Another existing query
        return self.execute("""
            SELECT o.*, p.name 
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            WHERE o.user_id = ?
        """, (user_id,))
    
    @sktime.timethis()
    def search_products(self, query):
        # Potentially slow search
        return self.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{query}%",))

# Use your database normally
db = DatabaseConnection()

# After running for a while, check what's slow
user = db.get_user_profile(123)
orders = db.get_user_orders(123) 
products = db.search_products("laptop")

# Instantly see which queries need optimization
print(f"User profile: {db.get_user_profile.timer.mean:.3f}s avg")
print(f"User orders: {db.get_user_orders.timer.mean:.3f}s avg")  
print(f"Product search: {db.search_products.timer.mean:.3f}s avg")
# Output: "Product search: 2.847s avg" - found your problem!

# You could even generate line charts of the data for real time visuals!
```

#### 6. Batch Job Monitoring - "How long until this finishes?"
**Problem:** Long-running data processing jobs with no visibility into progress or performance.
```python
from suitkaise import sktime

def process_customer_data():
    # Time the overall job
    job_timer = sktime.Timer() 
    job_timer.start()
    
    customers = get_all_customers()  # 50,000 customers
    
    for i, customer in enumerate(customers):
        # Time each customer batch
        if i % 100 == 0:  # Every 100 customers
            job_timer.lap()
            
            if i > 0:  # Skip first lap
                # Calculate progress and ETA
                batches_done = job_timer.num_times - 1
                batches_remaining = (len(customers) // 100) - batches_done
                avg_batch_time = job_timer.mean
                eta_seconds = batches_remaining * avg_batch_time
                
                print(f"Processed {i:,} customers")
                print(f"Avg batch time: {avg_batch_time:.1f}s")
                print(f"ETA: {eta_seconds/60:.1f} minutes")
                print(f"Total time so far: {job_timer.total_time/60:.1f} minutes")
        
        # Your actual processing code
        update_customer_metrics(customer)
        send_personalized_email(customer)
    
    total_time = job_timer.stop()
    print(f"Job completed in {total_time/60:.1f} minutes!")
```

## 10. Function-by-Function Examples

### Basic Time Functions

#### `now()` and `get_current_time()` - Stop Manual Timestamp Management

Without `sktime`: ***2 lines***
```python
import time # 1 (first line of code to get this to work)

current_timestamp = time.time() # 2 (second line of code to get this (current time) to work)

# sleep for 1 second
time.sleep(1) # 2 (second line of code to get this (sleep) to work)
```

With `sktime`: ***2 lines***
- 2 options for current time that are more clear and easier to spot in code
```python
from suitkaise import sktime # 1

current_timestamp = sktime.now() # 2 (as in "time right now")

# or the more explicit version
current_timestamp = sktime.get_current_time() # 2 (obvious wording)

# sleep for 1 second
sktime.sleep(1) # 2
```

Real use case: Timestamping events or storing timestamps as metadata
```python
def log_event(message):
    timestamp = sktime.now()
    event.data["timestamp"] = timestamp
```

This is just better names for `time.time()` and a `time.sleep()` function, so that you don't have to import `time` AND `sktime`.

#### `elapsed()` - easy way to calculate elapsed time

Without `sktime`: ***8 lines***
- no auto end time 
- imported `math.fabs()` ensures accuracy with float values, but requires extra code
- only basic error handling

```python
import time # 1
from math import fabs # 2

start_time = time.time() # 3
# ... do work ...
end_time = time.time() # 4

try: # 5
    elapsed = fabs(end_time - start_time) # 6, have to use absolute value to handle order mismatch
except TypeError: # 7
    print("Error: start_time and end_time must be of type float") # 8

# ========================================================================================

# The error-prone way without absolute value - wrong order gives negative time
elapsed = start_time - end_time  # Negative time, causes issues or requires extra code to handle
```

With `sktime`: ***3-4 lines*** 
- argument option with automatic end time (uses current time)
- for 2 argument option, order doesn't matter, `sktime` will handle it
- error handling for type mismatches

```python
from suitkaise import sktime # 1

start_time = sktime.now() # 2
# ... do work ...
time_to_complete = sktime.elapsed(start_time) # 3, current time is end time automatically

# ========================================================================================

# or give 2 times
end_time = start_time + 60 # 3 (60 seconds later)
time_to_complete = sktime.elapsed(start_time, end_time) # 4
# or...
time_to_complete = sktime.elapsed(end_time, start_time) # 4 (order doesn't matter, sktime will handle it)
```

### `timethis()` decorator - super powerful for how easy it is to use

Without `sktime`: ***> 50 lines*** (5 lines for basic setup)
- more than 50 lines of code to achieve a simple version of what `sktime` does
- have to manually calculate statistics and create a class object to use across project (200-400 lines)

```python
import time # 1

times = [] # 2
for i in range(100):
    start = time.time() # 3
    expensive_function()
    end = time.time() # 4
    times.append(end - start) # 5

# ========================================================================================

# Manual statistical calculation (error-prone and takes time to set up)
# > 30 lines of code
import statistics

mean_time = statistics.mean(times)
median_time = statistics.median(times)
# ... lots of fetching and manual statistical calculations
```

With `sktime`: ***3 lines***
- uses comprehensive `Timer` class
- zero setup decorator that automatically times functions every time they are called

```python
from suitkaise import sktime # 1

@sktime.timethis() # 2
def expensive_function():
    # Your code here
    pass

# Run many times
for i in range(100):
    expensive_function()

# Get comprehensive set of statistics automatically with 1 line of code
stats = expensive_function.timer.get_statistics() # 3

# ========================================================================================

# or access individual statistics
mean = timer.mean
median = timer.median
percentile_95 = timer.percentile(95)
std = timer.stdev
# ... and more!

# ========================================================================================

# or use an explicit timer instance
timer = sktime.Timer()

timer.start()
expensive_function()
elapsed_time = timer.stop()

print(f"Time taken: {elapsed_time:.3f}s")

# ========================================================================================

# time multiple functions with one timer
timer = sktime.Timer()

def MyClass:

    @sktime.timethis(timer)
    def expensive_function(self):
        # Your code here
        pass

    @sktime.timethis(timer)
    def expensive_function_2(self):
        # Your code here
        pass

def expensive_function_api(self):
    MyClass.expensive_function()

def expensive_function_2_api(self):
    MyClass.expensive_function_2()

# timer collects these into one set of times:
# direct calls of expensive_function
# direct calls of expensive_function_2
# calls of expensive_function through expensive_function_api
# calls of expensive_function_2 through expensive_function_2_api
```

### `TimeThis` context manager

Without `sktime`: ***? lines***
- have to create a custom class object and then a context manager to use it

With `sktime`: ***3-4 lines***
```python
# no given timer, creates a new one each time
from suitkaise import sktime # 1

with sktime.TimeThis() as timer: # 2
    expensive_function()

result = timer.result # 3
print(f"Time taken: {result:.3f}s")
```

```python
# given timer, uses that timer each time and collects stats over time
from suitkaise import sktime # 1

timer = sktime.Timer() # 2

with sktime.TimeThis(timer): # 3
    expensive_function()

# get stats
stats = timer.get_statistics() # 4

# print stats
print(f"Time taken: {stats['mean']:.3f}s")
# ...
```


## 11. Performance Considerations

### Timing Overhead
`sktime` is designed for minimal overhead in common operations:

- **Basic functions** (`now()`, `get_current_time()`): Near parity with `time.time()` in call overhead.
- **`elapsed()`**: Within a small constant factor of manual `abs(t2 - t1)` with the benefit of order independence and one-arg convenience.
- **Timer operations**: `start()/stop()`, `lap()`, and `pause()/resume()` are lightweight and thread-safe.
- **Statistical calculations**: Computed lazily when accessed via properties or `get_statistics()`.

You can run the included microbenchmarks to see colored, human-readable numbers on your machine:

```bash
pytest -q tests/test_sktime/test_performance.py
```

Example output (will vary by machine/CI):

```
time.time() avg call                     < 0.000001 s
sktime.now() avg call                    < 0.000001 s
Timer start+stop (noop) avg              0.000001 s
@timethis wrapped call avg               0.000001 s
```

### Implementation details affecting precision

- **High-resolution intervals**: Internals use `time.perf_counter()` for interval timing in `Timer`, `TimeThis`, and `@timethis`. Wall time functions (`now()`, `get_current_time()`) continue to use `time.time()`.
- **Paused-time accounting**: `Timer.total_time_paused` reports a strict sum of paused durations accumulated across recorded measurements.

### Managing global decorator timers

When using `@timethis()` without an explicit `Timer`, a per-function timer is auto-created and stored in a small registry for convenient access via `your_func.timer`. In long-lived/dev environments, you can reset this registry:

```python
from suitkaise import sktime

sktime.clear_global_timers()  # clears registry of auto-created timers
```

### Memory Efficiency
- Timer instances store measurements efficiently
- Optional memory limits for long-running timers
- Percentile calculations use efficient algorithms
- No memory leaks in long-running applications

### Multi-threading and Multi-processing
- Thread-safe across multiple threads (per-thread sessions under the hood)
- Compatible with multi-processing; decorate top-level functions if using process pools


### Production Considerations
```python
# For high-frequency operations, use manual timing
timer = sktime.Timer()
for i in range(1000000):
    timer.start()
    fast_operation()  # Very fast operation
    timer.stop()

# For production monitoring, use sampling
production_timer = sktime.Timer()

@sktime.timethis(production_timer)
def api_endpoint():
    # Only time every 100th call in production
    if random.randint(1, 100) == 1:
        return expensive_operation()
    return cached_result()
```

## 12. Importing `sktime`

Two supported import styles:

```python
# Module import
from suitkaise import sktime

# Usage
timer = sktime.Timer()
current_time = sktime.now()
rate_limiter = sktime.Yawn(2, 5)

# Direct imports
from suitkaise.sktime import Timer, now, Yawn

# Usage
timer = Timer()
current_time = now()
rate_limiter = Yawn(2, 5)
```

The module import style is recommended in examples as it makes the `sktime` namespace clear and prevents naming conflicts.

---

`sktime` transforms timing from a manual chore into being less than 10 lines away from high grade time monitoring for your entire codebase.