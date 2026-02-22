we need to manually check every single module site page and update the docs if needed for the initial release.

circuits - DONE
- why - DONE
- quick start - DONE
- how to use - DONE
- how it works - DONE
- examples - DONE

cucumber
- why - DONE
- quick start - DONE
- how to use - DONE
- how it works
- examples
- supported types - DONE
- performance - DONE
- worst possible object - DONE

timing
- why - DONE
- quick start 
- how to use - DONE
- how it works - DONE
- examples

paths
- why - DONE
- quick start
- how to use - DONE
- how it works - DONE
- examples

processing
- why
- quick start
- how to use
- how it works
- examples

sk
- why - DONE
- quick start
- how to use - DONE
- how it works - DONE
- examples
- blocking calls - DONE


NEXT, we need to:

1. update the about page in the main nav bar
- dropdowns need to be restandardized to the regular style in the module pages
- ensure __about__.md is actually streamlined to look like a site.md file
- copy over to html

2. add the quick start for all modules page on the main nav bar

3. add the feedback page on the main nav bar
- links are in _survey_links.md

4. create the footer for all site pages. make this look professional with the actual social media icons. add the footer to all pages except the password page and loading page.
    - link to each social
        - instagram - https://www.instagram.com/__suitkaise__?igsh=NTc4MTIwNjQ2YQ%3D%3D&utm_source=qr
        - discord - placeholder
        - youtube - placeholder
        - reddit - placeholder
        - twitter - placeholder
        - tiktok - placeholder
        - github - placeholder
        - email - suitkaise@suitkaise.info

    - link to the feedback page in footer as well


5. add the technical info page on the main nav bar


home page showcases

the worst possible object showcase (cucumber-1) always shows first. other than that, order is random.


## cucumber-2: "The Suitcase" (reconnector pattern)

The suitcase metaphor — fits the library name.
Your database connection is like a bottle of water: you can't bring it through airport security
(the serialization boundary). The Reconnector is like an empty bottle with a label that says
"fill with water on the other side."

Animation:
- object goes into suitcase, crosses the process boundary
- reconnect() is called, connection springs back to life
- show all three flavors: lazy reconnect (water gets auto refilled) reconnect_all (you refill multiple bottles), and auth reconnect (you fill a bottle with a specific liquid like lemonade instead)


## share-1: "It's Just Python" (ease of use)

Show simple Share code — attribute assignment, list append, logging.
It looks like a beginner exercise. Then the reveal:
"This is running across 4 separate processes. In separate memory spaces. On separate CPU cores."

- Phase 1: code appears. Label fades in: "What do you think this code does?"
- Phase 2: zoom out. The code was inside one of four process boxes. Arrows show data flowing
  between them and a central Share object. Counter climbing, results growing, logger logging.
- Phase 3: side by side. Left: Share code. Right: multiprocessing.Manager equivalent —
  Manager(), Value(), Lock(), manual .value access, no logger support. 3-4x longer and
  doesn't even support everything the left side does.

Punchline: "look how normal this is." Nothing to learn. You already know how to use it.


## share-2: "Put Anything On It" (works with any object)

The Gauntlet — increasingly "impossible" objects appear one by one.
Each one: created, assigned to Share, used from a subprocess, green checkmark.

| Object                              | Why it's hard                          |
| ----------------------------------- | -------------------------------------- |
| int, str                            | Baseline — even Manager can do this    |
| list, dict                          | Manager can too (slowly)               |
| logging.Logger                      | Manager can't. pickle can't.           |
| Custom class with nested state      | Manager can't without proxy classes    |
| Lambda / closure                    | pickle chokes                          |
| re.Pattern                          | Awkward to serialize                   |
| Database connection (psycopg2)      | Completely impossible normally         |
| Generator with state                | Nothing handles this                   |
| Object containing all of the above  | Game over                              |

After dict: red X on "without suitkaise" side, green checkmark on Share side.
The code never changes. Object gets more complex, code stays identical.


## share-3: "It Just Stays In Sync" (everything syncs)

4 process boxes on screen, Share object in the center with share.counter = 0.
All 4 processes increment simultaneously. Counter climbs from 0 to 100.
No locks. No race conditions. No Manager. Just self.share.counter += 1.
Freeze animation, show the code.

Tagline: "10 workers. 10 runs each. 100 increments. Zero bugs. Zero boilerplate."

Optional escalation: swap counter for dict, logger, list — everything syncs the same way.


## processing-3: "Power-Ups" (modified pools with .star() and sk modifiers)

Show a plain pool.map() call, then power it up one modifier at a time:
.star() to unpack args, .retry() for fault tolerance, .timeout() for safety,
.rate_limit() for API calls, .asynced() for async, .background() for fire-and-forget.

Each modifier snaps onto the call like a game power-up. You never rewrite the function,
you just chain modifiers at the call site.


## sk-1: "The Swiss Army Knife" (every modifier)

One function, displayed as a Swiss Army knife. Each modifier is a blade that unfolds:
.retry(3), .timeout(5), .background(), .rate_limit(10), .asynced().

For each, a tiny animation of what it does (retry: attempts, timeout: clock,
background: Future coming back, etc.).
End with chaining: func.retry(3).timeout(5).rate_limit(10)() — all blades open at once.


## timing-1: "The One-Liner" — DONE (combined with timing-2)

4 steps: ugly vanilla (15 lines) → @timethis one-liner → stats grid → punchline.
Shows the stats you get for free: mean, median, stdev, p95, p99, min, max, variance.


## paths-1: "Lost in Translation" — DONE

3 steps: problem (3 OS terminals, different paths, red glow) → fix (Skpath.rp, all match, green glow) → punchline.
Tagline: "Same project, any machine, zero path bugs."


## paths-2: "@autopath: The Pit of Success" — DONE

3 steps: callers send str/Path/Skpath + ugly isinstance boilerplate → @autopath flow diagram → punchline.
Tagline: "Once it's on, wrong paths can't get in."


## circuits-1: "Failure Handling, Solved." — DONE

4 steps: ugly manual backoff code → Circuit + backoff ladder animation → coordinated shutdown with 4 workers + .trip() → punchline.
Tagline: "Retry smart. Fail together. Recover gracefully."