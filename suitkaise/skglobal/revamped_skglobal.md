Revamping SKGlobal to incorporate SKTree (formerly SKRoot).

we should revamp skglobal to incorporate sktree as an option on how to structure global, xprocess storage. that way, we can use the cleaner, more magical sktree concept that makes directories and files in your project smart global containers. 

- tree system first: a main concern of the old skglobal is that it is over engineered for simpler needs or single process programs.
- with a design that creates containers for you, you dont have to declare top vs local storage.
-- auto sync automatically happens if there are multiple processes or scripts created through xprocess.
- isolate skfunction as its core functionality does not depend on skglobal
- revamp Cereal by splitting into Cereal (for internal xprocessing) and CerealBox (for external, cross language or network communication) (Not yet covered in this MarkDown)

what is xprocess (and skthreading)? xprocess is suitkaise's process and thread manager. it allows you to create new processes similar to multiprocessing, but also allows you to add tasks to complete when initializing every new process/thread. additionally, it will automatically sync serializable data to other processes (through the process that contains what is right now called "top level storage"). it also automatically handles process crashes or blocks due to errors, is able to report processes' statuses, recall processes, auto create background threads in processes, etc. 

NOTE: code is conceptual, and in the ballpark of what I want it to look like. Syntax may be wrong and code may be incorrect.

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
image_processing = skfunction.create_preset("image_classifier", preprocess_data, {
    "model_type": "CNN",
    "batch_size": 32,
    "normalize": True
})

# use the same function base callable but with different param values!
nlp_processing = skfunction.create_preset("text_classifier", preprocess_data, {
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
from suitkaise import skfunction, sktree

# Step 1: Define a flexible report function
def generate_sales_report(store_name, start_date, end_date, 
                         format="PDF", include_charts=True, 
                         email_to=None, save_location="./reports/"):
    """
    Creates a sales report - normally takes 2-3 minutes to run
    """
    # Imagine this does: fetch data, calculate totals, create charts, format as PDF
    print(f"Generating {format} report for {store_name} from {start_date} to {end_date}")
    # ... complex report generation logic ...
    return f"Report saved to {save_location}"

# Step 2: Create presets for different stores (avoid repetition!)
downtown_store = skfunction.create_preset("downtown_reports", generate_sales_report, {
    "store_name": "Downtown Branch",
    "format": "PDF",
    "include_charts": True,
    "email_to": "manager.downtown@business.com",
    "save_location": "./reports/downtown/"
})

mall_store = skfunction.create_preset("mall_reports", generate_sales_report, {
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
# On your laptop, your server, your assistant's computer - same exact setup

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

# ✅ Add caching so you don't regenerate identical reports:
@skfunction.cache_results(save_to_file=True)
def cached_annual_report(store_name, year):
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

reports is Suitkaises custom logging module, that keeps the original logging formula, but adds more convenience methods to auto log some common statements.

```python
from suitkaise import report

# report from this file (rpr = reporter)
rpr = report.from_current_file()
# or from another file (like a parent file)
target_file = report.get_file_path("parent_dir/main_dependent_file")
rpr = report.from_other_file(target_file)

# report from this key
rpr = report.from_this_key("Event_Bus")

# using context manager to quickly use a different reporter
# if not a valid in project file path (and not a valid path at all) assumes entry is key
# you could just create another reporter, but...
# this removes the "rq" reporter from memory and
# looks and feels more intuitive
except exception as e:
    with report.Quickly("a/different/file/path") as rq:
        rq.error(f"{Value1} was set to None so {Value2} was not initialized. {e}")

# create 2 different reporters
report_as_event_bus = report.from_this_key("Event_Bus")
rpr = report.from_current_file()

# use them for the same message and they will log from different sources
# can report the same major error to different sources
rpr.error(f"{Value1} was set to None so {Value2} was not initialized.")
report_as_event_bus.error(f"{Value1} was set to None so {Value2} was not initialized.")

# toggling what reports you see
paths = report.get_all_project_paths()
# supports strings and lists of strings
reporters_to_listen_to = [
    paths,
    "Event_Bus",
    "SYSWARNINGS"
]
report.listen_to(reporters_to_listen_to)

# basic report functions
from suitkaise import report

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
report.info("message", info, end=False, time)
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

# general status
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
rpr.error("message", info, end=TrueOrFalse)


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
All skpath operations return this 2 path dict, and all sk modules accept this dict. Converting this object to a string will return ONLY the absolute path (as to work with other standard path modules and standard programming concepts)

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

# get the SKPath of the file that executed this code
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

# standard autopath functionality, but function doesn't accept SKPath
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
saved_to_file = save_to_file(data=data) # -> still saves to my/default/path!

# NOTE: autofill WILL be ignored if defaultpath is used and has a valid path value!
# autofill WILL be ignored below!
@autopath(autofill=True, defaultpath="a/valid/path/or/skpath_dict")
```

----------
sktime

