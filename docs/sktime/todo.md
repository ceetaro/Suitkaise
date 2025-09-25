# SKTime TODO

First, resolve all the TODOs in time_ops.py and sktime/api.py. *

Next, re update the concept.md file to reflect the small changes. *

## Core Implementation Tasks
- [ ] Create example.py file and update info.md file
- [ ] Re-create all tests to test final api
- [ ] Create benchmark tests and record results
- [ ] Test thread safety

## Documentation TODOs from Concept File
- [ ] Filter timestamps to show last 24h calls in performance monitoring example (concept.md:636)
- [ ] Benchmark test basic functions (now, elapsed) and document performance (concept.md:951)
- [ ] Benchmark test Timer decorators and document performance (concept.md:952)

## Integration and Testing (DEFERRED)
- [ ] Test cross-platform compatibility
- [ ] Ensure that other suitkaise modules are compatible with the sktime module when dealing with time


Follow-up (docs-only): note perf_counter usage, strict paused semantics, and the new clear_global_timers in docs/sktime/concept.md.