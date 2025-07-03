Revamping Suitkaise

NOTE: code is conceptual, and in the ballpark of what I want it to look like. Syntax may be wrong and code may be incorrect.

what is xprocess (and skthreading)? xprocess is suitkaise's process and thread manager. it allows you to create new processes similar to multiprocessing, but also allows you to add tasks to complete when initializing every new process/thread. additionally, it will automatically sync serializable data to other processes (through the process that contains what is right now called "top level storage"). it also automatically handles process crashes or blocks due to errors, is able to report processes' statuses, recall processes, auto create background threads in processes, etc. 

goal with xprocess (with some other ideas mixed in that are covered below)

```python
# file name: my_file1.py
from suitkaise import xprocess, sktree
from my_events import create_event_bus

# initialize cross processing
xp = xprocess.CrossProcessing()
# get or create global storage, organized into containers that follow your project structure
tree = sktree.connect()

# create a new process
# params: name, func, func args, func kwargs
# we have some special kwargs that can be added
ui_process_config = {
    "join_in": None, # join (end process) in n seconds, None being no auto join (user has to join manually)
    "join_after": None, # join after n function loops, None being no auto join
}

# args and kwargs can be added, but they weren't in this case. I am just displaying that it takes these.
ui_process = xp.create_process("UI_handler", ui_loop(), args=None, kwargs=ui_process_config)

# add tasks that processes have to run before main work
with xp.ProcessSetup() as setup:
    # results here are added to config going into main function kwargs
    with xp.OnStart() as start:
        # create an event bus in another thread
        bus = create_event_bus()

        process_name = xp.get_process_name()
        pid = xp.get_process_id()
        process_metadata = {
            "process_name": process_name,
            "pid": pid,
            "remove_on_process_join": True
        }

    # results here are added to this loop's kwargs
    with xp.BeforeLoop() as before:
        current = xp.get_current_loop()
        loop_time_result_name = f"{process_name}-{current}" # added to kwargs of main func
        to_add = {
            "current_loop": current,
            "loop_time_result_name": loop_time_result_name
        }
        before.add_these(to_add)

    # results optionally added to next loop kwargs
    with xp.AfterLoop(add_for_next=False) as after:
        time = xp.get_last_loop_time()
        tree.add(name=loop_time_result_name, value=time, path="my_file1", metadata=process_metadata)
        after.add({"last_loop_time": time})

    with xp.OnFinish() as finish:
        to_select = {"pid": pid, "remove_on_process_join": True}
        tree.select_all_with(to_select, "my_file1")
        # dummy function that handles loop time stats
        report = generate_loop_time_report()
        report_name = f"{process_name} loop times report"
        # add to project root container
        tree.add_to_root(report_name, report)
        tree.remove_selected() # and "deselects"
        cleanup()

# NOTE: if tree.add() has no path argued, defaults to caller file path (in this case, my_file1's path)

setup1 = setup.build() # returns the data in workable form from the context manager

# creating a process including setup1 from xp.ProcessSetup
ui_process = xp.create_process("UI_handler", ui_loop(), setup1, args=None, kwargs=ui_process_config)

```

goal with new skglobal (simple ver.):

skglobal uses multiprocessing.Manager to create shared containers that can contain global variables registered as key-value pairs.

It also uses an internal system and (maybe?) Queue() to sync local storages to the main global storage.

How the main storage syncs.

Sending to main storage: when a global is added in a certain process, it gets added to a local (and internal) storage, with the process name and id. This data allows the data to get added to the correct process once it makes it to the main global storage.

Data is organized first by path to store at, then process id.

The global variable must have this data/metadata:
- unique name in specified path container (process_id can exist in dir 1 container and dir 2 container)
- specified path to store global at (defaults to caller file path)
- process id
- serializable value (some custom handlers for non-serializables will be added)

The top level storage checks each process's local storage (users cannot access values here, it functions internally), and syncs all of the globals waiting in there to its own storage, organizing them according to their path and their original process. The local storage then removes the variables on successful transfer, holding on to any that failed to transfer due to not having the correct data or not being serializable. It goes process by process, checking local storages and syncing. We do need a way to report if a process local storage actually needs to sync, to save time checking empty ones.

Receiving a global variable from main storage: since some globals might have the same name (key), and because it is slow to search through possibly thousands of global variables, we need some ways to retrieve globals from the storage quickly, cheaply, and error free.


```python
from suitkaise import skglobals as skg
from suitkaise import skpath

# make a connection to main global storage (stores in cache)
# gs = global storage
gs = skg.connect()

# tell program to search in a certain location

# option 1
search_for = {
    "path": skpath.SKPath("my_dir/my_file1"),
    "registry": "timing_rej"
    "value": dict
}
gs.search(search_in)

# option 2
with gs.SKGlobalSearch() as searcher:
    searcher.add_path(skpath.SKPath("my_dir/my_file1"))
    searcher.add_rej("timing_rej")
    searcher.add_expected_value(dict)

gs.search(searcher.config)

# get individual global variables
ui_timing_report = gs.get("UI_handler loop times report")
parser_timing_report = gs.get("bkgparser loop times report")

# get all
loop_time_reports = gs.get_all_with("loop times report")
# or...
loop_time_reports = gs.get_all_from_search()
```

Create a registry to hold global variables, optionally with persistent state.

```python
from suitkaise import RejSingleton, skglobals, sktree, ResolutionFinder

# get or create global storage, organized into containers that follow your project structure
tree = sktree.connect()

try:
    # create a singleton registry that works across processses with one line!
    user_settings = RejSingleton("user_settings")
    tree.add_to_root(user_settings)

except RejSingletonExistsError as e:
    # search and get the existing user settings
    tree.search({"expected_value": RejSingleton, "path": tree.all_paths()})
    user_settings = tree.get("user_settings")

    if user_settings.path != tree.root_path:
        tree.move(user_settings.name, tree.root_path)

# there is also a context manager to do this, with skglobals.ResetSearchAfter()
with skglobals.ResetSearchAfter(tree) as rsa:
    # search and get global variables

# **block exits**
# calls tree.reset_search()

# manual release of search filters (context manager auto calls this on exit)
tree.reset_search()

# now, we want to add some default settings! but we want to make sure that the whole program can access and view these settings.

# option 1 - manual update call

# since user settings are something that you need every time the user opens the program, we should save them to a file so that they remain for the next use!
# Rej and RejSingleton have a method to update metadata for the registry and its entries
# does nothing if value already matches new value
user_settings.update_metadata({"save_to_file": True})

# now lets add some default settings! since we are connected to the tree, the tree will update the data
user_settings.add_entry("resolution", ResolutionFinder.find_max_resolution())
user_settings.add_entry("brightness", 50)

# updates "user_settings" with new values/entries
tree.update(user_settings.name, user_settings)

# then... later...
user_settings.update_entry("brightness", 70)
tree.update(user_settings.name, user_settings)

# option 2
# use a tuple here, in case you want to update multiple variables at once [tuple=(name, value)]
with tree.AutoUpdate(("user_settings", user_settings))

    user_settings.update_metadata({"save_to_file": True})

    user_settings.add_entry("resolution", ResolutionFinder.find_max_resolution())
    user_settings.add_entry("brightness", 50)

# **block exits**
# calls tree.update(user_settings)

# disconnect from the tree to free up memory
tree.disconnect()
```
Internally, global variables are retrieved in batches organized by process. Background threads constantly checks if a request to get a variable is made. Requests separate into 3 categories: get a single variable,
get all variables from a registry (or the registry itself and its entries), and get select variables that have certain metadata or qualities. Since these take different amounts of time, we should separate how we handle these requests so that simple requests don't have to wait for a long search or long validation period. The main storage then sends all requested variables back to the process's internal local storage, and then the code that called get() can retrieve the variable it needs!

An SKTree is a form of SKGlobalStorage that organizes the storage by creating empty containers to match your project structure. If you want all of your ui related variables and settings to go under the ui directory,
you can easily just do that!

You cannot have a regular global storage and a tree -- once you use one, you cannot use the other, so plan carefully!!!

there is also a quick context manager option to connect and disconnect from a global storage or tree.
```python
with skglobals.QuickAccess(tree, variable_tuples_to_auto_update_on_exit)
    # get, remove, search for, or update global variables

# **block exits**
# variables in args get auto updated with new values (same tuple method as AutoUpdate)
# disconnects from tree
```

Now, we have a working singleton pattern registry, that all processes can view, stored neatly in the project root under a smart registry with a sensible name. Now, as long as "user_settings" exists, anything connecting to the tree can refer to these settings! Additionally, the settings will save and be exaclty the same the next time the program is run! (if you want)

we also have: Rej - a simple registry pattern without singleton behavior

While the RejSingleton made more sense for the example above, because we wanted to follow a singleton pattern,we also have a regular Rej option, for simple registry creation or creation of multiple similar registries.

```python
from random import randint
from typing import Type
from suitkaise import Rej
import time

# current version: v2.0.0.1
from ..version import current_version

# create a registry to register results

results = Rej("SEEDS")
# save the generated seeds to a file automatically
results.update_metadata({"save_to_file": True})

def generate_seed(name: str, seed_length: int)
    """Generate a certain number of randints to create a seed."""
    seed = None
    while len(str(seed)) < seed_length:
        if seed is None:
            next_digit = randint(1, 9)
            seed += next_digit
        else:
            next_digit = randint(0, 9)
            seed = seed * 10 + next_digit

    seed_info = {
        "name": name,
        "seed": seed,
        "created_at": time.time(),
        "version": current_version,
        "length": seed_length
    }
    results.add_entry(name, seed_info)
    return seed

# now, when you call the generate_seed function, it auto enters itself into a registry of all generated seeds, and returns just the result to you!
map_gen_seed = generate_seed("MyWorld1_MAPSEED", 4096)

# get the seed later, even on a different app launch (for example, if you add a new area in an update)
current_mapseed = Rej.get_entry("SEEDS", "MyWorld1_MAPSEED")
# regenerate unexplored areas of the map with the same seed to avoid corruption
updated_map = regen_unexplored(map_data=current_mapdata, mapseed=current_mapseed)
```

Adding permissions to a registry or variable
```python
# we have already connected to the tree and refined our search...
important_backup_data = tree.get("important_backup_data")

permissions = {
    "can_view": [xprocess.all_processes, skpath.SKPath()] # no arg: current file path
    "can_edit": "a_process_id_or_name.an_optional_thread_id_or_name"
}
# can either do "can_view/edit" or "cant_view/edit". CANNOT do "can_view" and "cant_view"
# if a process-thread or file can't view, it can't edit even if it is listed under can_edit.

# right now, we are in that process and thread! so lets update the permissions
important_backup_data.update_permissions(permissions)

# or add/remove permission
important_backup_data.add_permissions(permissions)
# removing will fail if no file has edit access after operation
important_backup_data.remove_permissions(permissions)

# say we messed up and no files have permissions to edit
important_backup_data.grant_temp_edit_permission()
# then fix permissions
# once permissions change, unless this file was added to permissions, it no longer has edit access
```

Permissions can be either processes, threads, threads in certain processes, or code called from a certain module/file. This is not the module the code originated in, but the one calling the code.

We should have 2 classes, ProcessInfo and ThreadInfo, that hold important data for that thread/process, which can allow process names or pids to point to a complete object with necessary information. We can store this information globally in the original process responsible for managing global storage and other processes.

For multiprocess usage:
My intention is that users use the original, single process as a central hub/process manager, and other processes get created as needed to handle actual work/execution.

For single process usage:
Since users don't have to worry about other processes, the only extra overhead that will persist throughout runtime is the global storage and possibly a thread manager storing and managing thread states and each thread's ThreadInfo.

SKThreading: easy threading and thread management. can easily create single threads or thread pools.

goal with skthreading:
```python
from suitkaise import skthreading, skglobals
from random import randint

def do_work(value1: int, value2: int)
    result = convert_to_word_form(value1) + " " + convert_to_word_form(value2)
    return result

# the user can decide if they want the thread to loop or not, and we handle looping, joining looping threads, looping a certain number of times, etc internally and gracefully. 
with skthreading.ThreadSetup as setup:
    setup.loop_infinitely = True

    with skthreading.OnStart() as start:
        list_of_results = []
        value1 = None
        value2 = None

    with skthreading.BeforeLoop() as before:
        if value1 is None:
            value1 = randint(1, 99999)
        if value2 is None:
            value2 = randint(1, 99999)

    with skthreading.AfterLoop() as after:
        # append last result to list of results
        skthreading.add_last_result(list_of_results)

    with skthreading.OnFinish() as finish:
        # add list of results to global storage
        skglobals.create(list_of_results)

dw_thread = skthreading.create_thread(name="do_work_thread", func=do_work, setup=setup.build(), args=None, kwargs=None)

# end an infinite looping thread or a finite looping thread early and gracefully (let it end its current loop)
skthreading.rejoin(dw_thread)
```
Both threads and processes have a discrete cycle: Execute a block of code once upon creation, execute a block of code once before starting a new loop, execute the actual function (which, in most cases, shouldn't loop itself, as we handle that behavior), execute a block of code after actual function finishes, and when thread is supposed to finish (join), run a block of code once before doing so.

The ProcessSetup and ThreadSetup context manager approach could also be a function based approach. (an on_start function, before_loop function, etc. If this is the case, we might want to make them dunder methods if that is even something that's possible.)

```python
# something like this might be a better/clearer idea!
class DoWorkThread(skthreading.SKThread):

    self.loop_infinitely = True

    def __on_start__(self)
        self.list_of_results = []
        self.value1 = None
        self.value2 = None

    def __before_loop__(self)
        if self.value1 is None:
            self.value1 = randint(1, 99999)
        if self.value2 is None:
            self.value2 = randint(1, 99999)

    # ...

```

---------
SKFunction: SKFunction will remain somewhat the same, but with a slightly different approach that makes for broader usage opportunities and isolates it from other suitkaise modules (before, it was dependent on skglobals).

SKFunctions are packaged instances consisting of a callable, args with set values, kwargs with set values, and metadata that helps us reference, find, and do other things with an SKFunction.

- allows you to call a function with preset arg values at different times
- store all of a function in one object
- delay calling a function
- cleaner, less time consuming execution through use of callable. What I mean by this is that it is a pain in the ass to always organize the positional args exactly in the correct order, and it takes time and space and makes it hard to organize and debug functions with many args.
-- instead of adding args positionally, you can add them just by param name as key and value you want to put in that parameter as value. you can even make a dictionary of args to add to a callable and organize it cleanly!

✅ Encapsulation - Complete execution context in one object
✅ Reusability - Define once, use many times with variations
✅ Testability - Isolated, repeatable function objects
✅ Maintainability - Centralized parameter management
✅ Composition - Build complex operations from simple ones
✅ Registry Pattern - Global function discovery and reuse

Developer Experience Benefits:

✅ No parameter juggling - Named parameter injection
✅ State preservation - Exact execution context saved
✅ Lazy evaluation - Define now, execute later
✅ Performance tracking - Built-in metrics and monitoring
✅ Cross-process support - Serializable function objects

```python
from suitkaise import xprocess, sktree, skfunction

xp = xprocess.CrossProcessing()

# create a machine learning pipeline that works across processes
def preprocess_data(data_path, model_type, batch_size, normalize=True):
    # Expensive preprocessing that takes 10+ minutes
    return processed_data

def train_model(processed_data, model_type, learning_rate, epochs):
    # Training that takes hours!
    return trained_model

# create reusable presets for different trials
image_processing = skfunction.create("image_classifier", preprocess_data, {
    "model_type": "CNN",
    "batch_size": 32,
    "normalize": True
})

# use the same function base callable but with different param values!
nlp_processing = skfunction.create("text_classifier", preprocess_data, {
    "model_type": "Transformer", 
    "batch_size": 16,
    "normalize": False
})

# Register in global function library
tree = sktree.connect()
# will also autoregister to a skfunction registry, allowing you to search either actual location or func rej
tree.add("image_classifier", image_processing, path="ml/preprocessing")
tree.add("text_classifier", nlp_processing, path="ml/preprocessing")

# you can ALSO add a function straight to the function registry
# will FAIL if a tree or global storage isn't connected
tree.add_to_funcrej("image_classifier", image_processing, connection=tree)

# Now ANY process can discover and use these functions themselves
# Process 1: Data preprocessing worker
with xp.ProcessSetup() as setup:
    # get available preprocessing functions (if relpath is given, tries to normalize it first)
    available_functions = tree.get_all_from("ml/preprocessing")
    # or...
    image_classifier = tree.get_from_funcrej("image_classifier")

    # execute correct one based on job type
    if job_type == "images":
        result = available_functions["image_classifier"].call(data_path="./images/")

# Process 2: Hyperparameter tuning worker  
with xprocess.ProcessSetup() as setup:
    # Use the same preprocessing function with different parameters
    preprocessor = tree.get_from_funcrej("image_classifier")
    
    # Override specific parameters for this experiment
    result = preprocessor.call(data_path="./experiments/run_5/", batch_size=64)

# Process 3: Production inference server
@skfunction.cache_results(ttl=3600, save_to_file=True)
def inference_pipeline(image_data):
    preprocessor = tree.get_from_funcrej("image_classifier") 
    model = tree.get("trained_model_v3")
    
    # Cached preprocessing + model inference
    processed = preprocessor.call(image_data)
    return model.predict(processed)

# The power: Functions are discoverable, reusable across processes, 
# cacheable, and maintain full execution context

# NOTE: you can use tree.get instead of tree.get_from_funcrej, but it will take much longer to find the function!
```

And a simpler example:
```python
# Let's say you run a small business and need different reports
from suitkaise import skfunction, sktree, autopath

# Step 1: Define a flexible report function
@autopath(defaultpath="./reports/misc")
def generate_sales_report(store_name, start_date, end_date, 
                         format="PDF", include_charts=True, 
                         email_to=None, save_location_path=None):
    """
    Creates a sales report - normally takes 2-3 minutes to run
    """
    # Imagine this does: fetch data, calculate totals, create charts, format as PDF
    print(f"Generating {format} report for {store_name} from {start_date} to {end_date}")
    # ... complex report generation logic ...
    return f"Report saved to {save_location}"

# Step 2: Create presets for different stores (avoid repetition!)
downtown_store = skfunction.create("downtown_reports", generate_sales_report, {
    "store_name": "Downtown Branch",
    "format": "PDF",
    "include_charts": True,
    "email_to": "manager.downtown@business.com",
    "save_location": "./reports/downtown/"
})

mall_store = skfunction.create("mall_reports", generate_sales_report, {
    "store_name": "Mall Location", 
    "format": "Excel",
    "include_charts": False,  # Mall manager prefers Excel
    "email_to": "manager.mall@business.com",
    "save_location": "./reports/mall/"
})

# Step 3: Save these presets so anyone can use them
tree = sktree.connect()
tree.add("downtown_reports", downtown_store, path="business/reports")
tree.add("mall_reports", mall_store, path="business/reports")

# Now the magic happens...

# ✅ Your assistant can generate reports without knowing all the details:
downtown_report = tree.get("downtown_reports")
downtown_report.call(start_date="2024-01-01", end_date="2024-01-31")
# Automatically uses: PDF format, includes charts, emails to right person, saves to right folder

# ✅ Different computers/processes can run the same reports:
# On your laptop, your server, your assistant's computer - same exact setup (just make sure to include .sk files that have the persistent data!)

# ✅ Override settings when needed:
# Emergency report with different format
downtown_report.call(
    start_date="2024-06-01", 
    end_date="2024-06-28",
    format="Excel",  # Override just this one setting
    email_to="ceo@business.com"  # Send to CEO instead
)

# ✅ Build complex workflows easily:
def monthly_report_batch():
    """Generate all monthly reports automatically"""
    all_report_functions = tree.get_all_from("business/reports")
    
    for store_name, report_func in all_report_functions.items():
        print(f"Generating report for {store_name}...")
        report_func.call(start_date="2024-06-01", end_date="2024-06-30")
    
    print("All monthly reports completed!")

# ✅ Add caching and/or saving so you don't regenerate identical reports:
@skfunction.cache_results(save_to_file="file/to/save/to") # or just skfunction.save_results("file/to/save/to")
def saved_annual_report(store_name, year):
    # Annual reports take 20+ minutes - cache them!
    return generate_sales_report(
        store_name=store_name,
        start_date=f"{year}-01-01", 
        end_date=f"{year}-12-31",
        format="PDF"
    )
```
Before SKFunction:

❌ Remember all parameters every time
❌ Copy-paste settings between scripts
❌ Hard to share setups with team
❌ Re-run expensive reports accidentally

With SKFunction:

✅ Set up once, use everywhere
✅ Override only what you need to change
✅ Share with entire team automatically
✅ Cache results to save time
✅ Build complex workflows from simple pieces

The beginner-friendly part: You don't need to understand multiprocessing, serialization, or caching - you just create functions with presets and the system handles the complexity!

-------
report

reports is Suitkaise's custom logging module, that keeps the original logging formula, but adds more convenience methods to auto log some common statements.

```python
from suitkaise import report, skpath

# report from this file (rptr = reporter)
rptr = report.from_current_file()
# or from another file (like a parent file)
target_file = skpath.SKPath("parent_dir/main_dependent_file")
rptr = report.from_other_file(target_file)

# report from a keyword instead of a file path
rptr = report.from_this_key("Event_Bus")

# using context manager to quickly use a different reporter
# if not a valid in project file path (and not a valid path at all) assumes entry is key
# you could just create another reporter, but...
# this removes the "rq" reporter from memory and looks and feels more intuitive
except exception as e:
    with report.Quickly("a/different/file/path") as rq:
        rq.error(f"{Value1} was set to None so {Value2} was not initialized. {e}")

# create 2 different reporters
bus_rptr = report.from_this_key("Event_Bus")
rptr = report.from_current_file()

# use them for the same message and they will log from different sources
# can report the same major error to different sources
rptr.error(f"{Value1} was set to None so {Value2} was not initialized.")
bus_rptr.error(f"{Value1} was set to None so {Value2} was not initialized.")

# toggling what reports you see
paths = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want", as_str=True)
# supports strings and lists of strings
reporters_to_listen_to = [
    paths,
    "Event_Bus",
    "SYSWARNINGS"
]
report.listen_to(reporters_to_listen_to)

# -------------------------
# basic report functions
from suitkaise import report
import time

# all reports take a float timestamp as an argument and convert it into a time and date depending on set rules
report.set_date_threshold(num_of_seconds, format_to_use)
report.set_time_threshold(num_of_seconds, format_to_use)
# time thresholds go from num_of_seconds to 0, so you can set one for minutes at inf and one for seconds at 60
report.set_time_threshold(float('inf'), "minutes")
report.set_time_threshold(60, "seconds")

# time threshold automatically mirrors for negative numbers
# we also have an assumed default (--d --h --m --.----------s)
# which assumes to measure in --h --m --.----------s if value is greater than 3600, for example

# standard logging
report.info("message", info, end=True, time=time.time())
report.debug()
report.warning()
report.error()
report.critical()

# success or fail
report.success()
report.fail()

# quick state messages
report.setToNone()
report.setToTrue()
report.setToFalse()

# save and load
report.savedObject()
report.savedFile()
report.loadedObject()
report.loadedFile()

# general status (will add more)
report.scanning()
report.scanned()
report.queued()
report.leftQueue()
report.leftQueueEarly()

report.custom(rest of regular args, "custom message")

# adding info to the start or end of a group of messages (default: end=False)
# handles correct spaces depending on if you add at start or end
info = f"(Class: {self.__name__}, Function: {__name__})"
with report.Quickly("any_valid_key_or_path", info, end=True) as rq:
    rq.error(f"{Value1} was set to None so {Value2} was not initialized.")

# Looks like "ERROR: number1 was set to None so registry2 was not initialized. (Class: MyClass, Function: __init__)

# or with existing reporter:
rptr.error("message", info, end=TrueOrFalse)


# Thats the basic concept for sk logging functionality
```

------------
skperf (sk performance)

ExitSummary - gather statistics into a summary that can automatically be accessed after runtime


```python
from suitkaise import ExitSummary

summary = ExitSummary()

# 3 ways to use ExitSummary:

# Option 1 - for Suitkaise performance metrics only
summary.collect_sk_performance_data()

# Option 2 - adding data into lists or dicts
summary.add_data("save_times", [0.1, 0.2, 0.3]) # adds to save_times list if exists otherwise creates one
summary.add_data("mem_usage", {"peak": 45.2, "average": 32.1}) # same behavior as line above

# Option 3 - autocollecting data from global storage/tree with a metadata flag
# remember to narrow your search down first to save time looking for object!
save_times = tree.get("save_times")
save_times.update_metadata({"create_exit_summary": True})
```

REST OF skperf HERE...


---------
skpath - easy, intuitive path operations that ensure good developer habits and make paths easier

get_project_root - requires you to have necessary files in your project root to safely recognize it

Project Root Detection - What get_project_root looks for

Essential Project Files (Necessary)
Your project should have these files in the root directory:

License file: LICENSE, LICENSE.txt, license, etc.
README file: README, README.md, readme.txt, etc.
Requirements file: requirements.txt, requirements.pip, etc.

Strong Project Indicators
These files significantly increase confidence that a directory is a project root:

Python setup files: setup.py, setup.cfg, pyproject.toml
Configuration files: tox.ini, .gitignore, .dockerignore
Environment files: .env, .env.local, etc.
Package initializer: __init__.py

Weak Project Indicators
These files provide some evidence but aren't decisive:

Build files: Makefile, Dockerfile, docker-compose.yml
Example directories/files
Editor configs: pyrightconfig.json

Expected Directory Structure
The algorithm looks for these common project directories:
Strong indicators:

app/ or apps/ - Application code
data/ or datasets/ - Data files
docs/ or documentation/ - Documentation
test/ or tests/ - Test files

Regular indicators:

.git/ - Git repository
src/ or source/ - Source code
examples/ - Example code
venv/ or env/ - Virtual environments
Build/cache folders: __pycache__/, dist/, build/
IDE folders: .vscode/, .idea/

What This Means for Users
The more of these elements your project has, the higher confidence the algorithm will have in correctly identifying your project root. A well-structured project with a README, license, requirements file, and organized directories will be detected most reliably.

SKPath is a special path object that is a dict of 2 paths:
```python
an_skpath = {
    "ap": "an/absolute/system/path",
    "np": "a/normalized/path/up_to_your_project_root"
}
```
All skpath operations return this 2 path dict, and all sk modules accept this dict. Converting this object to a string will return ONLY the absolute path (as to work with other standard path modules and standard programming concepts). this object has methods for comparison as well as the aforementioned string conversion.

```python
from suitkaise import skpath

# get the project root (expects python project necessities)
root = skpath.get_project_root()
# optionally add intended name of project root you'd like to find
# doing this will return None unless a valid root WITH this name is found
root = skpath.get_project_root("Suitkaise")

# create a path object containing both absolute and normalized path
# normalized path: only up to your project root
my_skpath = skpath.SKPath("a/path/goes/here")

# create an SKPath object for the current path with simple initialization
caller_skpath = skpath.SKPath()

# get the SKPath of the file that executed this code with a function
caller_skpath = skpath.get_caller_path()

# get the current directory path that executed this code
current = skpath.get_current_dir()

# check if 2 paths are equal with equalpaths
path1 = skpath.get_caller_path()
path2 = skpath.SKPath("a/path/goes/here")

if equalpaths(path1, path2):
    do_something()

# generate a reproducible ID for your path (shorter identification than whole path)
my_path_id = path_id(my_path)
my_path_shortened_id = path_idshort(my_path)

# get all project paths
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want")
# as abspath strings instead of skpaths
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want", as_str=True)
# including all .gitignore and .skignore paths
proj_path_list = skpath.get_all_project_paths(except_paths="this/one/path/i/dont/want", dont_ignore=True)

# get a nested dictionary representing your project structure
proj_structure = skpath.get_project_structure()
# or a printable, formatted version: (custom_root allows you to only format some of the structure)
fmted_structure = skpath.get_formatted_project_structure(custom_root=None)
```

Finally, skpath has the autopath decorator, which will automatically convert valid paths to SKPaths before running a function. Any parameter with "path" in the name will attempt to convert a valid path to an SKPath object. if the param value is not a valid path, leaves it as is.

autopath will detect if the path parameter accepts SKPaths -- if not, automatically converts SKPaths to string form!

```python
from suitkaise import autopath

# standard autopath functionality
@autopath()
def process_file(path: str | SKPath = None)
    print(f"Processing {path}...")
    # do some processing of the file...

# later...

# relative path will convert to an SKPath automatically before being used
process_file("my/relative/path")

# standard autopath functionality, but function doesn't accept SKPath type!
@autopath()
def process_file(path: str = None) # only accepts strings!
    print(f"Processing {path}...")
    # do some processing of the file...

# later...

# relative path will convert to an absolute path string instead!
process_file("my/relative/path")

# using autofill
@autopath(autofill=True)
def process_files(path: str | SKPath = None)
    print(f"Processing {path}...")
    # do some processing of the file...

# later...

# relative path will convert to an SKPath automatically before being used
# if no path is given, uses caller file path (current file executing this code)
process_file()

# using defaultpath
@autopath(defaultpath="my/default/path")
def save_to_file(data: Any = None, path: str | SKPath = None) -> bool:
    # save data to file with given path...

# later...

# user forgets to add path, or just wants to save all data to same file
saved_to_file = save_to_file(data) # -> still saves to my/default/path!

# NOTE: autofill WILL be ignored if defaultpath is used and has a valid path value!
# autofill WILL be ignored below!
@autopath(autofill=True, defaultpath="a/valid/path/or/skpath_dict")
```

----------
sktime - an expansion on basic timing functionality

```python
from suitkaise import sktime

# get current time (same as time.time())
now = sktime.now()
# longer, clearer alias
now = sktime.get_current_time()

# sleep for n seconds
sktime.sleep(2)

# sleep after yawning twice

# setup to sleep for 3 seconds after yawning 4 times
# log_sleep will tell you when sleep occurs due to yawn if set to true
_yawn = sktime.Yawn(3, 4, log_sleep=True)

# doesnt sleep
_yawn.yawn()
# doesnt sleep
_yawn.yawn()
# doesnt sleep
_yawn.yawn()
# sleeps for 3 seconds!
_yawn.yawn()

# later...
# doesnt sleep
_yawn.yawn()
# doesnt sleep
_yawn.yawn()
# doesnt sleep
_yawn.yawn()
# sleeps for 3 seconds!
_yawn.yawn()

# time operations with a stopwatch
sw = sktime.Stopwatch()

# start the stopwatch
sw.start()
sktime.sleep(2)

# pause the stopwatch
sw.pause()
sktime.sleep(999)

# resume the stopwatch
sw.resume()
sktime.sleep(3)

# lap the stopwatch (about 5 seconds will be the result here)
sw.lap()
lap1 = sw.get_laptime(1)

sktime.sleep(2)

# stop the stopwatch
sw.stop()

# get results
total = sw.total_time
lap2 = sw.get_laptime(2)

# time execution with a decorator or context manager
timer = sktime.Timer()

@sktime.timethis(timer)
def do_work():
    # do some work

# when function finishes, time is logged to timer.
counter = 0
while counter < 100:
    do_work()

last_time = timer.mostrecent
mean_time = timer.mean
median_time = timer.median
max_time = timer.longest
min_time = timer.shortest
std = timer.std
time36 = timer.get_time(36)

# using context manager without and with Timer initialization

# without initalization, we only get most recent result
counter = 0
while counter < 100:
    with sktime.Timer() as timer:
            do_work()

# will only get most recent result
result = timer.result

# with initialization, we get access to full statistics
_timer = sktime.Timer()

counter = 0
while counter < 100:
with _timer.TimeThis() as timer:
    do_work()

last_time = _timer.mostrecent
mean_time = _timer.mean
median_time = _timer.median
max_time = _timer.longest
min_time = _timer.shortest
std = _timer.std

if _timer.times >= 82:
    time82 = _timer.get_time(82)
```

----------
circuit - easy upgrades to incremental, conditional while looping and timeout after failing attempts

```python
from suitkaise import Circuit

objs_to_check = a bunch of dicts
index = 0

# create a Circuit object
circ = Circuit(shorts=4)

# while we have a flowing circuit
while circ.flowing:
    current_obj = objs_to_check[index]

    for item in current_obj.items():
        # we should only add up to 3 LargeSizedObjs total across all dicts
        if isinstance(item, LargeSizedObj):
            # short the circuit. if this circuit shorts 4 times, it will break
            circ.short()
        if isinstance(item, ComplexObject):
            # immediately break the circuit
            circ.break()

        # if the circuit has broken (opposite of flowing, flowing gets set to False)
        if circ.broken:
            break

    # check if circuit has broken.
    if circ.broken:
        pass
    else:
        dicts_with_valid_items.append(current_obj)
    index += 1

------------
# sleeping after a circuit break

while program.running:
    circ = Circuit(100)

    while circ.flowing:
        current_mem_usage = mem_mgr.get_current_usage()

        if current_mem_usage > max_mem_threshold:
            # will sleep execution for 5 seconds if circ.break() is called here
            circ.break(5)

        if current_mem_usage > recc_mem_threshold:
            # will sleep execution for 0.05 seconds if this short causes a break
            circ.short(0.05)
            print(f"Shorted circuit {circ.times_shorted} times.")

        # if circ.broken (or "if not circ.flowing")
        if circ.broken:
            print("Pausing execution because memory usage exceeds max threshold.")
```

----------
fdprint - a super formatter that can format any standard data type, date and time, and more

fdprint (format/debug print) is a tool that allows users to automatically print data in better formats, formatted for better display or better debugging.

```python
my_list = [
    "hello",
    "world",
    "this",
    "is",
    "a",
    "test",
    "of",
    "the",
    "list",
    "functionality"
]

my_dict = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
    "key4": "value4",
    "key5": "value5"
}

my_set = {
    "apple",
    "banana",
    "cherry",
    "date",
    "elderberry"
}

my_tuple = (
    "first",
    "second",
    "third",
    "fourth",
    "fifth"
)

my_int = 42
my_float = 3.14
my_bool = True
my_none = None
my_bytes = b"byte string"
my_complex = 1 + 2j
my_range = range(10)
my_dict_of_lists = {
    "list1": ["item1", "item2", "item3"],
    "list2": ["item4", "item5", "item6"]
}
my_dict_of_sets = {
    "set1": {"item1", "item2", "item3"},
    "set2": {"item4", "item5", "item6"}
}
my_dict_of_tuples = {
    "tuple1": ("item1", "item2", "item3"),
    "tuple2": ("item4", "item5", "item6")
}

def nlprint(*args, **kwargs):
    """
    Print each argument on a new line.
    
    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments (not used).
    """
    for arg in args:
        try:
            print(arg)
        except Exception as e:
            print(f"Error printing argument {arg}: {e}")


nlprint(
    my_list,
    my_dict,
    my_set,
    my_tuple,
    my_int,
    my_float,
    my_bool,
    my_none,
    my_bytes,
    my_complex,
    my_range,
    my_frozenset,
    my_bytearray,
    my_dict_of_lists,
    my_dict_of_sets,
    my_dict_of_tuples
)

```

result:
['hello', 'world', 'this', 'is', 'a', 'test', 'of', 'the', 'list', 'functionality']
{'key1': 'value1', 'key2': 'value2', 'key3': 'value3', 'key4': 'value4', 'key5': 'value5'}
{'banana', 'apple', 'cherry', 'elderberry', 'date'}
('first', 'second', 'third', 'fourth', 'fifth')
42
3.14
True
None
b'byte string'
(1+2j)
range(0, 10)
{'list1': ['item1', 'item2', 'item3'], 'list2': ['item4', 'item5', 'item6']}
{'set1': {'item2', 'item1', 'item3'}, 'set2': {'item4', 'item6', 'item5'}}
{'tuple1': ('item1', 'item2', 'item3'), 'tuple2': ('item4', 'item5', 'item6')}

result with fmt for display:
hello, world, this, is, a, test, of, the, list, functionality

key1: value1
key2: value2
key3: value3 
key4: value4
key5: value5

banana, apple, cherry, elderberry, date

(first, second, third, fourth, fifth)

42
3.14
True
None
byte string
1 + 2j
0, 10


list1: item1, item2, item3
list2: item4, item5, item6

and with color to more easily see what is being printed.

result with fmt for debugging:
(list) [
    
    'hello', 'world', 'this', 'is', 'a', 'test', 'of', 'the', 'list', 'functionality'

        ] (list)

(dict) {

   'key1': 'value1', 
   'key2': 'value2', 
   'key3': 'value3', 
   'key4': 'value4', 
   'key5': 'value5'

} (dict)

(set) {
    
    'banana', 'apple', 'cherry', 'elderberry', 'date'

} (set)

(tuple) (
    
    'first', 'second', 'third', 'fourth', 'fifth'

) (tuple)

(int) 42
(float) 3.14
(bool) True
(None) None
(bytes) 'byte string'
(complex) ( 1 + 2j )
(range) 0, 10

(dict) {

    (list) ['item1', 'item2', 'item3'],
    (list) ['item4', 'item5', 'item6']

} (dict)

and with color to more easily see what is being printed.

```python
from suitkaise import fdprint as fd
import time

# its as easy as...
value1 = {
    "dict": {a dict}
    "list": []
}

fd.fprint("This is value1: {value1}", value1)

# printing dates or times
now = time.time()

# print using our default time format (see report section for more details)
fd.fprint("Printing {value1} at {time:now}", (value1, now))
# or...
# print using our default date format
fd.fprint("Printing {value1} at {date:now}", (value1, now))

# using custom time and date formats

# print using hours, minutes, seconds and microseconds
fd.fprint("Printing {value1} at {hms6:now}", (value1, now))
# print using date and timezone
fd.fprint("Printing {value1} at {datePST:now}", (value1, now))

# using debugging formats automatically
fd.dprint("Your message with vars", (tuple of vars), priority level 1-5)

# toggling if debug messages should be printed

# will only print messages at level 2 or higher
fd.set_dprint_level(2)
```

----------
sklock - autolocking, smart locking, and easy lock tracking

```python
import sklock

# use sklock to enable lock tracking
# log_access logs when and what aquires this class's lock
# decorator creates a special lock or reentrant lock that can track who accesses it
@sklock.rlock(log_access=True)
class MyClass():

    # use this decorator to ensure that sklock exists
    @sklock.ensure()
    def __init__(self):
        self.level = 3
        self.threshold = 0.5

    # automatically use the sklock for this entire method
    # log_access tells user when something uses lock or tries to use lock for just this function
    @sklock.withlock(log_access=True)
    def set_level(self, level: int):
        if level:
            self.level = level

    # use a context manager if you only want to use lock some of the time
    def set_threshold(self, threshold: float):
        with sklock.Use():
            if threshold and 0 <= threshold <= 1:
                self.threshold = threshold

# using these decorators with multiple locks
class TwoLockClass:

    def __init__(self):
        self._lock1 = sklock.RLock()
        self._lock2 = sklock.Lock()
        self.level = 3
        self.threshold = 0.5
        self.brightness = 50

    @sklock.withlock(self._lock1, log_access=True)
    def set_level(self, level: int):
        if level:
            self.level = level

    def set_threshold(self, threshold: float):
        with sklock.Use(self._lock2):
            if threshold and 0 <= threshold <= 1:
                self.threshold = threshold  

# handling deadlocks gracefully
# setting wait to any positive number will allow things to wait a set time to see if lock opens
    @sklock.withlock(self._lock1, log_access=True, wait=1.5)
    def set_brightness(self, brightness: int):
        # set the brightness

    # getting lock history and current lock status
    hist = sklock.get_lock_history()
    is_locked = sklock.get_current_lock_status()

    # if multiple locks are in use, specify what lock you would like to focus on
    hist = sklock.get_lock_history(self._lock1)

    

# debugging or gathering general current lock information

# at start of file
sklock.track()

# later on
sklock.get_lock_information()
# returns all sklocks, name of what they are locking, name of what is currently using them (if in use)
```

Question: should i include anything else to improve the sklock concept?

----------
cerial (formerly cereal), Cerial and CerialBox - better serialization and the serialization engine Suitkaise runs on itself

cerial is the internal magic powering the seamless cross processing. for now, we will focus on internal serialization using cloudpickle as a base.

Cerial is for internal serialization between processes, CerialBox is for external network or cross language serialization.

Question: are there any legal blockades with using cloudpickle as a base for my serialization engine? do i need to contact them and obtain permission?

we will use cloudpickle as a base, and turn it into cerial (mix of the words serial and cereal for some flair)

differences between cloudpickle and Cerial (internal, cross process serialization):

- Cerial is built with extra features on top of cloudpickle to handle extra complex objects. It uses __setstate__ and __getstate__ to handle the deconstruction and reconstruction of these objects.

These include:
- special functions (lambdas, generators, etc.)
- threading locks
- other common NSOs (non-serializable objects)
- all suitkaise specific complex objects
- and more that I think of

Question: anything else I should include?

Additionally, it overrides the standard pickler that multiprocessing.Manager uses, allowing us further freedom while using our global storages. It also handles the automatic intialization and cleanup of custom Managers.

Cerial will function internally as our main serialization engine, but users can also import it and use it to serialize objects themselves if they would like to use it outside of the suitkaise environment, as I want this to be a better version of current serialization methods, once again at the cost of overhead.


-------------
## Summary of preliminary chat "Python Global State Management Design"

Comprehensive Development Summary: Suitkaise Library Architecture and Design Decisions

Core Philosophy and Target Audience

Suitkaise is designed with a revolutionary philosophy: "grand ideas, little coding experience" - democratizing complex application development by making sophisticated multiprocessing, global state management, and cross-process communication accessible to developers of all skill levels. The library prioritizes "magic over transparency" while maintaining "API first, functionality second" development approach.

Target Audience Analysis

Primary: Developers with great ideas but limited experience with complex systems
Secondary: Experienced developers who want rapid prototyping without boilerplate
Use Cases: Small dev studios competing with large corporations, personal projects requiring enterprise-level features, educational environments teaching advanced concepts

Business Model and Open Source Strategy
Dual Licensing Approach:

Free for personal use - encourages adoption and community growth
Commercial licensing with revenue thresholds - companies making significant money contribute back
Potential royalty model - revenue-based rather than user-count based
Challenges identified: Internal corporate tooling bypasses revenue thresholds entirely

Philosophy: "Even the playing field between gigantic tech corporations and small dev studios" while ensuring the library remains accessible for learning and personal development.
Gateway Module Strategy
Three-tiered user acquisition funnel:

Gateway Modules (SKPath, FDPrint, SKTime) - immediate utility, low barrier to entry
Core Power (SKTree, XProcess, SKFunction) - where the real magic happens
Advanced Features (Report, SKPerf, Circuit, SKLock) - specialized functionality

Strategic Goal: Hook users with immediate utility, then showcase ecosystem power to drive deeper adoption.
Module Architecture Overview
SKPath - The Foundational Gateway Module
Revolutionary Design: Smart path objects with dual-path architecture
pythonSKPath = {
    "ap": "absolute/system/path",
    "np": "normalized/path/relative/to/project/root"
}
Key Magical Features:

Zero-argument initialization: SKPath() automatically detects caller's file
Automatic project root detection: Uses sophisticated indicator-based algorithm
String compatibility: str(skpath) returns absolute path for standard library compatibility
Cross-module integration: All SK modules accept SKPath objects seamlessly

Project Root Detection Philosophy:

Two-phase approach: Necessary files (LICENSE, README, requirements) are required, not weighted
Sophisticated scoring: Indicators and weak indicators add confidence
Robust detection: Handles edge cases, symlinks, different installation patterns
Force override system: For uninitialized projects - critical for early development

Advanced Features:

Gitignore integration for path filtering
Formatted project tree visualization
Path ID generation for shorter identifiers
Project structure analysis

SKTree vs SKGlobal Relationship
Architectural Decision: SKTree is an enhanced version of SKGlobal, not a replacement

SKGlobal: Basic cross-process storage - simple key-value with no organization
SKTree: Organized storage that mirrors project structure for large, complex projects
Mutual Exclusivity: Cannot use both simultaneously - users must choose their approach

SKTree Advantages:

Automatic organization by project structure
Path-based variable organization
Natural scaling for large projects
Integration with project analysis tools

XProcess - The Multiprocessing Revolution
Core Innovation: Sophisticated process lifecycle management with automatic sync
Process Lifecycle Architecture:
python# Four-phase process execution
1. OnStart()     # Execute once on process creation
2. BeforeLoop()  # Execute before each function iteration  
3. [Main Function Execution]
4. AfterLoop()   # Execute after each function iteration
5. OnFinish()    # Execute once before process termination
Advanced Features:

Automatic data sync between processes through global storage
Process crash handling and recovery
Background thread auto-creation within processes
Process status reporting and recall capabilities
Configurable join behavior (time-based, iteration-based, manual)

Design Philosophy: Transform multiprocessing from expert-level complexity to beginner-friendly magic through declarative configuration and automatic lifecycle management.
SKFunction - Execution Context Revolution
Breakthrough Concept: Complete execution contexts as serializable, discoverable objects
Architectural Benefits:

✅ Encapsulation: Complete execution context in one object
✅ Reusability: Define once, use many times with variations
✅ Cross-process support: Serializable function objects
✅ Registry pattern: Global function discovery and reuse
✅ Parameter management: Named parameter injection eliminates positional argument juggling

Integration Strategy:

Loose coupling: Works independently without requiring other SK modules
Tight integration: Supercharged when used with SKTree/SKGlobal for function registries
Automatic registration: Functions registered in path-appropriate containers
Caching integration: Built-in result caching with metadata flags

Revolutionary Use Case: Enable complex ML pipelines, report generation, and data processing workflows to be easily shared and reused across processes and even different machines.
Report - Multi-Source Logging Innovation
Core Innovation: Multiple reporters for same events with source-based organization
Key Features:

Multi-source reporting: Same error logged from file context AND logical component context
Selective listening: Filter log noise by choosing specific reporters
Convenience methods: report.savedObject(), report.queued() - domain-specific logging
Central cross-process logging: All processes log to unified system
Intelligent time formatting: Automatic threshold-based formatting

Target Audience Alignment: Pre-built logging patterns for developers who don't know what to log or how to format it effectively.
SKPerf - Transparency Through Performance Monitoring
Philosophy: "Show users exactly what the magic costs" - complete transparency about overhead
Core Components:

Real-time tracking: Memory, CPU, execution time monitoring
Exit summaries: Comprehensive post-execution analysis
SK overhead transparency: Detailed breakdown of library performance impact
Benchmark integration: Direct function performance testing
Smart analysis: Automatic insights and pattern detection

Strategic Importance: Builds user trust by showing exactly what performance they're trading for convenience.
Supporting Modules Philosophy
SKTime, Circuit, SKLock: Positioned as convenience layers rather than core functionality

SKTime: Convenient timing operations (Stopwatch, Timer, Yawn classes)
Circuit: Circuit breaker pattern for controlled failure handling
SKLock: Lock tracking and deadlock prevention for threading
Rationale: "Support modules" that make standard coding easier, even if users don't use the full ecosystem

Advanced Serialization Strategy - Cerial
Foundation: CloudPickle-based with extensive custom handlers

Legal Consideration: CloudPickle is Apache 2.0 licensed - can build upon with proper attribution
Enhanced Capabilities: Custom setstate/getstate for complex objects
Target Objects: Lambdas, generators, threading locks, SK-specific objects
Manager Integration: Override multiprocessing.Manager's default pickler
Dual Purpose: Internal SK engine + standalone utility for users

Data Persistence and State Management
Metadata-Driven Persistence:
pythonobject.update_metadata({"save_to_file": True})
Unified System: Single metadata flag controls persistence across all module types

User settings, cached results, function registries, performance data
File Format Strategy: Hybrid approach - JSON for simple types, custom format for complex objects
Version Migration: .sk files with automatic version-by-version updates
Fault Tolerance: Incremental object-by-object migration with rollback capability

Magical Caller Detection System
Revolutionary Feature: Automatic detection of user files while ignoring SK internal calls
Technical Implementation:

Call stack walking: Traverse frames until non-SK file found
Robust SK detection: Path resolution + installation pattern recognition
Fallback strategies: Graceful degradation when detection fails
Use Cases: get_project_root(), SKPath() auto-initialization

Business Impact: Eliminates configuration overhead - functions "just work" regardless of where they're called from.
Performance Philosophy and Overhead Management
Value Proposition: "90% easier Python for 40% performance overhead"

Target Acceptance: Users gladly trade performance for productivity
Adaptive Systems: Performance categorization (cheap/normal/expensive operations)
Memory vs Disk Trade-offs: Favor disk usage (TB+ SSDs) over memory constraints
Transparency: SKPerf shows exact costs so users make informed decisions

Educational Integration Strategy
Beyond Documentation: Interactive learning ecosystem

Built-in quizzes: Test knowledge of each module's capabilities
Runtime warnings: "Don't create 1000 processes" - educational guardrails
Performance suggestions: "You created 50 processes but only have 8 CPU cores"
Long-form tutorials: Comprehensive learning materials
AI Integration: If successful, leverage ChatGPT/Claude training for user support

Architectural Principles and Design Patterns
Internal vs External Module Separation
Critical Decision: Clean separation between internal functionality and user-facing APIs

Internal modules (_int/core/): Pure utility functions, no external dependencies
External modules (skpath/api.py): User-facing classes and convenience functions
Benefits: Maintainable code, testable components, flexible API evolution

Progressive Complexity Design
User Journey: Start simple, discover power incrementally

Gateway attraction: Immediate utility with simple modules
Power discovery: Realize ecosystem potential through integration
Advanced mastery: Leverage full suite for complex applications

Magic vs Control Balance
Philosophy: Provide magic by default, allow manual override when needed

Automatic behaviors: Project root detection, caller file identification, cross-process sync
Override capabilities: Force project root, manual configuration, disable auto-features
Escape hatches: Access to underlying functionality when magic doesn't fit

Module Integration Philosophy
Ecosystem Thinking: Modules enhance each other but remain functional independently

SKPath + SKTree: Automatic path-based organization
SKFunction + SKTree: Function registries and discovery
XProcess + SKTree: Automatic cross-process state sync
Report + SKPerf: Performance-aware logging
Emergent Capabilities: Combined modules create possibilities greater than sum of parts

Error Handling and Fault Tolerance
Graceful Degradation: System continues functioning even when components fail

Project root detection: Multiple fallback strategies
Cross-process sync: Continue operation if sync fails
File operations: Graceful handling of permission errors
Migration failures: Partial success with error reporting and rollback options

Version Management and Evolution Strategy
Migration Philosophy: Never break user data, always provide upgrade paths

File format evolution: .sk files with version headers
Incremental migration: Object-by-object with progress tracking
Rollback capability: Return to previous version if migration fails
Backward compatibility: Maintain API compatibility across versions

Development Methodology
API-First Development: "API first, functionality second"

User experience priority: Design for how users want to work
Implementation flexibility: Internal systems can evolve without breaking user code
Iterative refinement: Perfect the interface before optimizing implementation
Real-world validation: Test APIs with actual use cases before finalizing

Community and Ecosystem Strategy
Open Source Benefits:

Adoption acceleration: Free use drives community growth
Innovation catalyst: Users discover use cases beyond original vision
Educational impact: Helps developers learn advanced concepts
Competitive advantage: Small teams gain enterprise-level capabilities

Commercial Sustainability:

Value-based pricing: Revenue thresholds align cost with benefit
Enterprise features: Advanced capabilities for commercial users
Support tiers: Professional support for business critical applications

Technical Innovation Summary
Revolutionary Concepts Introduced:

Dual-path objects: Absolute + normalized path architecture
Magical caller detection: Automatic context awareness across call stacks
Process lifecycle management: Declarative multiprocessing configuration
Cross-process function objects: Serializable execution contexts
Multi-source logging: Same events from multiple perspectives
Adaptive performance management: Self-optimizing based on usage patterns
Metadata-driven persistence: Unified state management across all data types

User Experience Breakthroughs:

Zero-configuration magic: Functions work automatically without setup
Progressive disclosure: Simple start, powerful capabilities when needed
Educational integration: Learning built into the development experience
Ecosystem synergy: Modules enhance each other naturally
Transparent performance: Users see exactly what convenience costs

This comprehensive architecture represents a fundamental shift in Python library design - from expert-focused tools to democratized access to sophisticated capabilities, enabling anyone with great ideas to build complex, production-ready applications without deep systems programming expertise.
