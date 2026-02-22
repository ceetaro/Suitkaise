# cucumber-2: "The Suitcase"

Showcase for the Reconnector pattern. The metaphor: packing for a trip.

Live connections (DB, sockets) are like water bottles — you can't bring them through
airport security (the serialization/process boundary). cucumber turns them into empty
bottles with labels: "fill with water on the other side." That label is the Reconnector.


## Visual Design

Split into 4 phases. Dark background throughout, consistent with cucumber-1 styling.
The suitcase asset (briefcase-laptop) is the central visual motif.


## Phase 1: The Problem (~8s)

1. Black screen. Fade in text:
   "You have a database connection. You need it in another process."

2. Show a simple code block, typed out:
   ```
   conn = psycopg2.connect(host="db.prod", database="users", password="secret")
   worker = MyWorker(conn)
   worker.start()
   ```

3. Red flash / error shake. Text appears:
   "PicklingError: can't pickle psycopg2.connection objects"

4. Brief pause. Fade to:
   "pickle can't send live connections across processes."
   "The connection is alive here. It doesn't exist over there."

5. Fade out.


## Phase 2: The Suitcase (~12s)

Visual metaphor — show what cucumber does differently.

1. Fade in: the suitcase image (closed) in the center.
   Below it: "cucumber doesn't try to copy the connection."

2. Suitcase opens (image cycle animation, same as cucumber-1).
   Text changes: "It packs what it needs to make a new one."

3. Show the "packing" — metadata items float into the suitcase one by one.
   Each item is a small labeled card/tag:
   - host: "db.prod"
   - database: "users"
   - port: 5432
   - user: "admin"
   - ✗ password (this one is red / crossed out — NOT packed)

   Below: "Credentials are never stored. Security by design."

4. Suitcase closes. A label appears on it: "PostgresReconnector"
   Small text: "All the metadata. None of the secrets."

5. Suitcase slides from left to right across a dotted line labeled
   "process boundary" — it crosses safely.

6. On the right side, the suitcase arrives. Text:
   "On the other side, you reconnect."


## Phase 3: Three Flavors (~18s)

Show the three reconnection styles. Use a tabbed or sequential reveal.
Each flavor gets its own beat.

### Flavor 1: Lazy Reconnect (~5s)

Header: "lazy reconnect"
Subtext: "For connections that don't need credentials."

Typed code:
```
conn = sqlite3.connect("app.db")
data = cucumber.serialize(conn)

restored = cucumber.deserialize(data)
restored.execute("SELECT * FROM users")  ← just use it
```

Highlight the last line with a green glow. Annotation:
"First attribute access triggers reconnect automatically. No extra code."

Small tag below: "SQLite, DuckDB, sockets, threads, subprocesses"

### Flavor 2: Auth Reconnect (~5s)

Header: "auth reconnect"
Subtext: "For connections that need credentials."

Typed code:
```
conn = psycopg2.connect(host="db.prod", password="secret")
data = cucumber.serialize(conn)

restored = cucumber.deserialize(data)
live = restored.reconnect(auth="secret")
```

Highlight `reconnect(auth="secret")` with a green glow. Annotation:
"You provide the password. cucumber never stores it."

Small tag below: "PostgreSQL, MySQL, MongoDB, Redis, Snowflake, Oracle, +10 more"

### Flavor 3: reconnect_all (~8s)

Header: "reconnect_all"
Subtext: "For objects with many connections."

Show a more complex object first:
```
class Pipeline:
    def __init__(self):
        self.db = psycopg2.connect(...)
        self.cache = redis.Redis(...)
        self.analytics = psycopg2.connect(...)
```

Then the one-liner:
```
cucumber.reconnect_all(pipeline, **{
    "psycopg2.Connection": {
        "*": "db_pass",
        "analytics": "analytics_pass"
    },
    "redis.Redis": {"*": "redis_pass"}
})
```

Annotation: "One call. Every connection. Attribute-specific credentials."

Visual: show 3 reconnector placeholders inside the Pipeline object all lighting up
green simultaneously.


## Phase 4: The Punchline (~6s)

1. Fade to black. Then:
   "Or, just let it happen automatically."

2. Show the @autoreconnect decorator:
   ```
   @autoreconnect(**{"psycopg2.Connection": {"*": "secret"}})
   class Worker(Skprocess):
       def __init__(self, db_connection):
           self.db = db_connection

       def __run__(self):
           self.db.execute(...)  # already reconnected
   ```

3. Annotation: "Connections auto-reconnect when the process starts. Zero manual work."

4. Final tagline, centered, larger text:
   "Pack anything. Cross any boundary. Reconnect on the other side."

5. Replay button appears.


## HTML Structure

```html
<div class="cuke2-showcase" id="cuke2Showcase">

    <!-- Phase 1: The Problem -->
    <div class="cuke2-scene cuke2-problem" id="cuke2Problem">
        <div class="cuke2-text" id="cuke2ProbText1"></div>
        <div class="cuke2-code" id="cuke2ProbCode"></div>
        <div class="cuke2-error" id="cuke2Error"></div>
        <div class="cuke2-text" id="cuke2ProbText2"></div>
    </div>

    <!-- Phase 2: The Suitcase -->
    <div class="cuke2-scene cuke2-suitcase" id="cuke2Suitcase">
        <div class="cuke2-text" id="cuke2SuitText"></div>
        <div class="cuke2-case-wrap" id="cuke2CaseWrap">
            <img class="cuke2-case-img" id="cuke2CaseImg"
                 src="__assets__/briefcase-laptop-closed.png" alt="">
        </div>
        <div class="cuke2-tags" id="cuke2Tags"></div>
        <div class="cuke2-label" id="cuke2Label"></div>
        <div class="cuke2-boundary" id="cuke2Boundary">
            <span class="cuke2-boundary-text">process boundary</span>
        </div>
    </div>

    <!-- Phase 3: Three Flavors -->
    <div class="cuke2-scene cuke2-flavors" id="cuke2Flavors">
        <div class="cuke2-flavor" id="cuke2Lazy">
            <div class="cuke2-flavor-header">lazy reconnect</div>
            <div class="cuke2-flavor-sub"></div>
            <pre class="cuke2-flavor-code"></pre>
            <div class="cuke2-flavor-note"></div>
            <div class="cuke2-flavor-tag"></div>
        </div>
        <div class="cuke2-flavor" id="cuke2Auth">
            <div class="cuke2-flavor-header">auth reconnect</div>
            <div class="cuke2-flavor-sub"></div>
            <pre class="cuke2-flavor-code"></pre>
            <div class="cuke2-flavor-note"></div>
            <div class="cuke2-flavor-tag"></div>
        </div>
        <div class="cuke2-flavor" id="cuke2All">
            <div class="cuke2-flavor-header">reconnect_all</div>
            <div class="cuke2-flavor-sub"></div>
            <pre class="cuke2-flavor-code"></pre>
            <div class="cuke2-flavor-note"></div>
        </div>
    </div>

    <!-- Phase 4: Punchline -->
    <div class="cuke2-scene cuke2-punchline" id="cuke2Punchline">
        <div class="cuke2-text" id="cuke2AutoText"></div>
        <pre class="cuke2-code" id="cuke2AutoCode"></pre>
        <div class="cuke2-note" id="cuke2AutoNote"></div>
        <div class="cuke2-tagline" id="cuke2Tagline"></div>
        <button class="cuke2-replay-btn" id="cuke2Replay">replay</button>
    </div>

</div>
```


## Animation Timing

| Phase | Duration | Cumulative |
|-------|----------|------------|
| 1     | ~8s      | 0-8s       |
| 2     | ~12s     | 8-20s      |
| 3     | ~18s     | 20-38s     |
| 4     | ~6s      | 38-44s     |

Total: ~44 seconds. Similar pace to cucumber-1 (~45s before battle).


## JS Function

`setupCucumber2Showcase()` — follows same pattern as `setupWPOShowcase()` and
`setupProcessingShowcase()`. Called from the home page setup block.

Key animations:
- typeCode() — reuse existing typing animation helper
- Tag float-in — CSS keyframes, staggered delays
- Suitcase slide — CSS transform translateX with transition
- Green glow on code lines — CSS class toggle
- Flavor reveal — sequential opacity/translateY transitions

The showcase should be interruptible (reset on carousel slide change) and
replayable (replay button).


## Key Points to Sell

1. Security: passwords are NEVER serialized. Emphasize this visually (red X on password).
2. Simplicity: lazy reconnect = zero code. Auth reconnect = one line. reconnect_all = one call.
3. Coverage: 16+ database types supported out of the box.
4. @autoreconnect: the "I don't even have to think about it" level.
