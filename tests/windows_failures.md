Failed tests (recap across suites):
  ✗ [Path Utilities Tests] streamline_path long path
     └─ TypeError: streamline_path() got an unexpected keyword argument 'max_length'
  ✗ [Process Class Tests] Concurrent processes
     └─ Concurrent should be ~100ms, got 1.5290805000113323
  ✗ [Process Class Tests] stop() limited process
     └─ Should have counted at least once, got 0
  ✗ [Pool Class Tests] Pool.map parallel
     └─ Should be parallel (< 200ms sequential), got 1.7080899000866339
  ✗ [Pool Class Tests] Pool workers cap
     └─ Expected capped pool to be slower. capped=1.489s uncapped=1.680s
  ✗ [Share Class Tests] Share Counter increment()
  ✗ [Share Class Tests] Share DataStore operations
