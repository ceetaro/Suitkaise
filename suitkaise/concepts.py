# lets focus just on the process management for now, and data syncing later

class CrossProcessing:
    def __init__(self):
        self._processes = {}  # Process registry
        self._active = True

class Process:
    def __init__(self, name, num_loops=None):
        self.name = name
        self.pid = None  # Set when actually started
        self.num_loops = num_loops
        self.current_loop = 0
        self.metadata = {
            'name': name,
            'pid': None,
            'num_loops': num_loops,
            'completed_loops': 0
            # for future use when we add data syncing and global variables
            'remove_on_process_join': True,
        }

        self._should_continue = True
        
    # Lifecycle hooks (user overrides these)

    # called automatically before every loop iteration
    def __preloop__(self): pass

    # NEW! HAVE to use this for main loop logic
    def __loop__(self): pass

    # called automatically after every loop iteration
    def __postloop__(self): pass  

    # called automatically when process needs to join and last __postloop__ is done
    def __onfinish__(self): pass

    
    # Control methods

    # finishes current loop (before, loop, after) and then calls __onfinish__
    def rejoin(self): 
        """Graceful shutdown after current loop"""
        
    # does not finish current loop, immediately calls __onfinish__
    # use with caution!
    def skip_and_rejoin(self): 
        """Immediate shutdown"""

    # immediately stops process, no hooks called
    # use with extreme caution!
    def instakill(self):
        """Kill process immediately, no hooks called"""


class _ProcessRunner:
    def __init__(self, process_setup, config, *args, **kwargs):
        self.process_setup = process_setup  # User's Process instance
        self.config = config
        
    def run(self):
        # Initialize process
        self.process_setup._start_process()
        
        try:
            # Main execution loop
            # the position of counters and loop timers is subject to change
            while self._should_continue():
                self.process_setup.current_loop += 1
                self.process_setup.__preloop__()
                self._start_loop_timer()
                self.process_setup.__loop__()
                self.end_loop_timer()
                self.process_setup.__postloop__()
                # check if we should continue

                
        except Exception as e:
            # our custom error handling


        finally:
            self.process_setup.__onfinish__()
            self.process_setup._join_process()



self.process_setup.current_loop += 1
self._start_loop_timer()
self.process_setup.__preloop__()
self.process_setup.__loop__()
self.end_loop_timer()
self.process_setup.__postloop__()

# check if we should continue

# DEFUALT BEHAVIOR

def __preloop__(self): pass

# timer starts here
def __loop__(self): pass
# timer ends here

def __postloop__(self): pass  


def __onfinish__(self): pass


# CUSTOM BEHAVIOR

# functions to use in init
def __init__(self, ...):
    # in __init__...

    # start timer before preloop
    start_timer_before_preloop()

    # these two are functionally the same
    start_timer_after_preloop()
    start_timer_before_loop()

    # these two are functionally the same
    end_timer_after_loop()
    end_timer_before_postloop()
    
    # end timer after postloop
    end_timer_after_postloop()

# in the case of end_timer_after_postloop, last timing result would
#  have to be processed in next preloop, so not as intuitive


# question: what if a process is running and realizes it needs to dynamically 
# create another process? 
# should we handle this or just stick to users declaring processes in that one context manager?
# reason i bring this up is becuase this is logic that might not be in the main script under the context manager.

def main():
    with CrossProcessing() as xp:
        # Set up data processing workers
        processor1 = DataProcessor("processor-1", "database")
        processor2 = DataProcessor("processor-2", "files")
        
        # Set up monitoring
        api_monitor = APIMonitor("api-monitor", "https://api.example.com")
        
        # Create and start all processes
        xp.create_process(processor1, get_data_processor_config())
        xp.create_process(processor2, get_data_processor_config())

        # **for some reason this process wants to make another process
        xp.create_process(api_monitor, get_monitor_config())
        
        # Let them run
        xp.join_all()
    # Automatic cleanup

if __name__ == "__main__":
    main()


# **
# 1. is this just a subprocess? is that a thing?
# 2. how do we currently handle this?
# is our current handling of this following intuitive coding principles?