COMPLETED TASKS

- audited all __init__.py files; added missing exports (Pipe, cucumber JSON/IR helpers), added missing __version__ to processing/sk/paths
- fixed processing/__init__.pyi (removed stale Process alias, added Pipe and autoreconnect stubs)
- updated root __init__.pyi to match new exports
- updated setup.cfg (version was 0.1.0, description was stale)
- updated email to suitkaise@suitkaise.info in pyproject.toml and setup.cfg
- bumped version to 0.4.0b0 in all files (pyproject.toml, setup.cfg, README, all __init__.py modules)
- changed classifier from Alpha to Beta; added Python 3.12/3.13 classifiers
- renamed task list file from 1-0-0-* to 0-4-0-beta-*
- reorganized CHANGELOG into Keep a Changelog format
- updated CI to test Python 3.11, 3.12, 3.13 via matrix strategy
- verified licensing (LICENSE, pyproject.toml, setup.cfg, README all consistent Apache 2.0)
- fixed Python 3.12/3.13 TemporaryFileCloser serialization bug (TemporaryFileHandler.can_handle + extract_state updated for 3.12+ internals)
- fixed flaky Share supported types multiprocess test (coordinator stop() handles dead Manager; test verification resilient to Manager death)
- added 116-test network handler test suite (reconnectors, factory, socket handler, db handler mocks, HTTP session handler)
- test coverage increased from 80% to 82% (target met)
- all 12 test suites passing on Python 3.11; WorstPossibleObject tests now pass on 3.12/3.13
- expanded CI matrix to 9 jobs: ubuntu-latest + macos-latest + windows-latest x Python 3.11/3.12/3.13
- audited processing module for Linux (fork) compatibility — confirmed Linux-ready (Manager-backed primitives, no platform assumptions, correct ForkingPickler usage)
- fixed coordinator is_alive returning False in child processes (added _client_mode flag, probes Manager connection instead of checking local _process)
- added _BUILTIN_SHARED_META registry for list/set/dict — mutating methods proxied through coordinator, read-only methods fetch and return values directly
- added dunder protocol methods to _ObjectProxy (__len__, __iter__, __contains__, __bool__, __getitem__, __setitem__, __delitem__, __str__)
- fixed proxy __getattr__ misclassifying user class methods as read-only (empty writes list was falsy)
- fixed shared memory leaks at shutdown — stop()/kill() now always clean up segments, added close_local() for child processes, added __del__ to coordinator
- blocked Sktimer start/stop/pause/resume/lap/discard through Share proxy (_share_blocked_methods) — these rely on perf_counter() and thread-local sessions that produce garbage when replayed in coordinator
- added _share_blocked_methods support in _ObjectProxy — generic mechanism for any class to declare methods that raise TypeError through Share
- added _share_disallowed support in Share.__setattr__ — generic mechanism for any class to prevent being added to Share entirely
- added _share_method_aliases support in _MethodProxy — generic mechanism to route proxy method calls to internal alternatives (e.g. no-sleep variants)
- disallowed Circuit in Share entirely (_share_disallowed) — auto-reset + sleep fundamentally breaks in coordinator
- BreakingCircuit short()/trip() now skip sleep through Share via _share_method_aliases → _nosleep_short/_nosleep_trip; state changes still apply
- fixed Sktimer percentile/get_time/get_statistics/get_stats returning None through Share — read-only methods had {'writes': []} which proxy treated as fire-and-forget; changed to {'reads': ['times']}
- fixed TimeThis and @timethis recording partial timing on exceptions — now only records on successful completion; __exit__ no longer masks original exceptions
- fixed namedtuple serialization in cucumber — NamedTupleHandler existed but was never invoked because isinstance(obj, tuple) intercepted first; now namedtuples route to handler preserving fields/class/module
- updated timing-why.md docs (sktime→timing, Timer→Sktimer)


TEST RELEASE

*1. double check all init patterns and ensure they work
*2. double check that all required project files are included
*2.5. rerun test coverage check (target >82%) — 82% achieved
*3. change version in all files to 0.4.0b0
*4. organize the changelog by date.
*5. build 0.4.0b0 package and upload to test pypi

*5.5. bug fixes

*6. wait for me to test package in a different project space, by running all examples, tests, and benchmarks
*7. confirm that dev has given the go ahead

ACTUAL RELEASE

*8. what do I have to do in github to prepare for release?
*9. anything else I need to do pre release? (licensing verified)
10. build 0.4.2b0 package and upload to pypi
11. test package in a different project space, by running all examples, tests, and benchmarks, ensuring all work (can reuse same test space)


POST RELEASE

12. update site files with new docs
13. reconfigure site to support new version
14. create donation page and feedback form
- thru stripe or paypal
- might need to create something on business side like an llc or something
15. insert all download links into site

16. create social media accounts for suitkaise
- twitter/x
- instagram
- tiktok
- youtube
- reddit
- create a discord account and server
- create a stack overflow account and profile
- anywhere else I should be as a solo developer?
- update my personal linkedin
- update my personal github profile

17. link all social media accounts to site page footers
18. final site review
19. publish site to suitkaise.info (my google workspace domain)

20. post on my personal instagram and linkedin

21. prepare initial posts for all social media accounts
- twitter: single flyer + information video on each module + sick "edit" video (8 posts)
- instagram: single flyer + information video on each module + sick "edit" video (8 posts)
- tiktok: main video + information video on each module + sick "edit" video (8 posts)
- youtube: combine all videos into a single video and post it
- discord: single flyer + link to site and yt

- stack overflow: need help with this
- reddit: need help with this
  - what subreddits? focused on all levels of python developers

22. cold call (email) university pages and/or professors to get feedback
- who is the best person to email?

23. any other cold calls I should make?

