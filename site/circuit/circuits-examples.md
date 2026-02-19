/*

synced from suitkaise-docs/circuits/examples.md

*/

rows = 2
columns = 1

# 1.1

title = "`circuits` examples"

# 1.2

text = "
(start of dropdown "Common Patterns")
## Common Patterns

(start of dropdown "`<suitkaise-api>Circuit</suitkaise-api>`")
### `<suitkaise-api>Circuit</suitkaise-api>`

Use `<suitkaise-api>Circuit</suitkaise-api>` when you want to automatically continue after a cooldown.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

# create a circuit that:
# - trips after 10 shorts
# - sleeps 1 second on first trip
# - increases sleep by 1.5x after each trip (1s → 1.5s → 2.25s → ...)
# - caps sleep at 30 seconds max
<suitkaise-api>rate_limiter</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
    num_shorts_to_trip=10,
    sleep_time_after_trip=1.0,
    backoff_factor=1.5,
    max_sleep_time=30.0
)

for request in incoming_requests:
    # check if this request is rate limited
    if is_rate_limited(request):
        # count the rate limit as a "short"
        # after 10 shorts, circuit trips: sleeps, then auto-resets counter
        # short() returns True if it slept, False otherwise
        <suitkaise-api>rate_limiter.short()</suitkaise-api>
    else:
        # not rate limited, process normally
        process(request)
```

(end of dropdown "Circuit")

(start of dropdown "`<suitkaise-api>BreakingCircuit</suitkaise-api>`")
### `<suitkaise-api>BreakingCircuit</suitkaise-api>`

Use `<suitkaise-api>BreakingCircuit</suitkaise-api>` when you want to stop after too many failures.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

# create a circuit that:
# - breaks after 3 shorts
# - sleeps 1 second when it breaks
# - stays broken until manually reset
<suitkaise-api>circ</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0
)

# loop continues as long as circuit is not broken
while not <suitkaise-api>circ.broken</suitkaise-api>:
    try:
        # attempt the risky operation
        result = risky_operation()
        # success - exit the retry loop
        break
    except OperationError:
        # failure - count it as a short
        # after 3 failures, circuit.broken becomes True
        <suitkaise-api>circ.short()</suitkaise-api>

# check if we exited because circuit broke
if <suitkaise-api>circ.broken</suitkaise-api>:
    # handle the failure case (e.g., log, alert, fallback)
    handle_failure()
```

(end of dropdown "BreakingCircuit")

(start of dropdown "Dual usage")
### Dual usage

Use `<suitkaise-api>BreakingCircuit</suitkaise-api>` for inner retries and `<suitkaise-api>Circuit</suitkaise-api>` for outer rate limiting.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>, <suitkaise-api>BreakingCircuit</suitkaise-api>

# outer circuit: rate limits the overall process
# - trips after 5 item failures
# - sleeps 5 seconds, then continues to next item
<suitkaise-api>outer</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>num_shorts_to_trip=5, sleep_time_after_trip=5.0)

# inner circuit: controls retries for each item
# - breaks after 3 failed attempts
# - sleeps 0.5 seconds between retries
<suitkaise-api>inner</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>num_shorts_to_trip=3, sleep_time_after_trip=0.5)

for item in items:
    # reset inner circuit for each new item
    # this clears the broken flag and short counter
    <suitkaise-api>inner.reset()</suitkaise-api>
    
    # retry loop for this item
    while not <suitkaise-api>inner.broken</suitkaise-api>:
        try:
            # attempt to process
            process(item)
            # success - exit retry loop, move to next item
            break
        except TransientError:
            # transient failure - count it
            # after 3 failures, inner.broken becomes True
            <suitkaise-api>inner.short()</suitkaise-api>
    
    # if inner circuit broke, this item completely failed
    if <suitkaise-api>inner.broken</suitkaise-api>:
        # count it as a failure for the outer circuit
        # after 5 failed items, outer circuit sleeps
        <suitkaise-api>outer.short()</suitkaise-api>
```

(end of dropdown "Dual usage")

(start of dropdown "Async pattern")
### Async pattern

```python
import asyncio
import aiohttp
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

# create circuit for rate limiting
# - trips after 5 rate limit responses
# - sleeps 2 seconds (using asyncio.sleep, not blocking)
# - doubles sleep time after each trip
# - adds ±20% randomness to prevent thundering herd
<suitkaise-api>circ</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
    num_shorts_to_trip=5,
    sleep_time_after_trip=2.0,
    backoff_factor=2.0,
    jitter=0.2
)

async def fetch_url(session: aiohttp.ClientSession, url: str) -> dict | None:
    """Fetch a single URL with circuit breaker protection."""
    try:
        # make the async HTTP request
        async with session.get(url) as response:
            # check for rate limiting (HTTP 429)
            if response.status == 429:
                # count rate limit as a short
                # .asynced()() returns an async version that uses asyncio.sleep
                # first () gets the async function, second () calls it
                await <suitkaise-api>circ.short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
                # return None to indicate we didn't get data
                return None
            
            # success - parse and return JSON
            return await response.json()
    
    except aiohttp.ClientError:
        # network error - also count as a short
        await <suitkaise-api>circ.short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
        return None

async def fetch_all(urls: list[str]) -> list[dict]:
    """Fetch multiple URLs sequentially with shared circuit."""
    results = []
    
    # create a single session for all requests
    async with aiohttp.ClientSession() as session:
        for url in urls:
            # fetch each URL
            result = await fetch_url(session, url)
            # only keep successful results
            if result:
                results.append(result)
    
    return results

async def main():
    urls = [
        "https://api.example.com/data/1",
        "https://api.example.com/data/2",
        "https://api.example.com/data/3",
    ]
    
    # fetch all URLs
    results = await fetch_all(urls)
    
    # print summary
    print(f"Fetched {len(results)} results")
    print(f"<suitkaise-api>Circuit</suitkaise-api> tripped {<suitkaise-api>circ.total_trips</suitkaise-api>} times")

# run the async main function
asyncio.run(main())
```

(end of dropdown "Async pattern")

(start of dropdown "Multithreading with a shared circuit")
### Multithreading with a shared circuit

Multiple threads share a `<suitkaise-api>BreakingCircuit</suitkaise-api>`. When one thread breaks it, the others stop immediately.

```python
import threading
from queue import Queue
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

def worker(worker_id: int, queue: Queue, circuit: <suitkaise-api>BreakingCircuit</suitkaise-api>, results: list):
    """Worker function that processes items from a shared queue."""
    
    # loop continues as long as circuit is not broken
    # when ANY thread breaks the circuit, ALL threads see it
    while not circuit.broken:
        # try to get an item from the queue
        try:
            # timeout allows us to periodically check circuit.broken
            item = queue.get(timeout=0.1)
        except:
            # queue is empty or timed out
            # loop back to check circuit.broken again
            continue
        
        try:
            # attempt to process the item
            result = process_item(item)
            # success - add to shared results
            results.append(result)
        
        except FatalError:
            # fatal error - immediately break circuit for ALL workers
            print(f"Worker {worker_id}: Fatal error, breaking circuit")
            # trip() immediately sets circuit.broken = True
            circuit.trip()
        
        except TransientError:
            # transient error - count it
            # after threshold, circuit.broken becomes True
            circuit.short()
        
        finally:
            # always mark task as done (for queue.join())
            queue.task_done()
    
    # we exit the loop when circuit.broken is True
    print(f"Worker {worker_id}: <suitkaise-api>Circuit</suitkaise-api> broken, stopping")


# MAIN CODE

# create a shared circuit
# - breaks after 5 transient errors across ALL workers
# - no sleep time (we just want to stop, not pause)
<suitkaise-api>circuit</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>num_shorts_to_trip=5, sleep_time_after_trip=0.0)

# create a shared queue for work items
queue = Queue()

# shared list for results (thread-safe for append)
results = []

# fill the queue with work items
for item in items:
    queue.put(item)

# start 4 worker threads
threads = []
for i in range(4):
    # each thread gets the same circuit, queue, and results list
    t = threading.Thread(target=worker, args=(i, queue, circuit, results))
    t.start()
    threads.append(t)

# wait for all threads to finish
for t in threads:
    t.join()

# check final state
if circuit.broken:
    # some items were not processed
    print(f"Stopped early: {queue.qsize()} items remaining")
    # optionally reset and retry later
    circuit.reset()
else:
    print(f"All items processed: {len(results)} results")
```

When any worker calls `circuit.trip()` or `circuit.short()` enough times, all workers see `circuit.broken == True` and exit their loops. This provides coordinated shutdown across threads.

(end of dropdown "Multithreading with a shared circuit")
(end of dropdown "Common Patterns")

(start of dropdown "More specific examples")
## More specific examples

(start of dropdown "API client with circuit breaker")
### API client with circuit breaker

```python
import requests
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

class APIClient:
    """API client with circuit breaker for fault tolerance."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        
        # create circuit breaker
        # - breaks after 3 consecutive failures
        # - sleeps 1 second when broken (before user can retry)
        # - doubles sleep time after each reset (1s → 2s → 4s → ...)
        # - caps at 60 seconds max
        # - adds ±10% randomness
        self.<suitkaise-api>circuit</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>
            num_shorts_to_trip=3,
            sleep_time_after_trip=1.0,
            backoff_factor=2.0,
            max_sleep_time=60.0,
            jitter=0.1
        )
    
    def get(self, endpoint: str) -> dict | None:
        """Make a GET request with circuit breaker protection."""
        
        # first, check if circuit is broken
        # if broken, fail fast without making request
        if self.circuit.broken:
            return None
        
        try:
            # make the HTTP request
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                timeout=5  # 5 second timeout
            )
            # raise exception for 4xx/5xx status codes
            response.raise_for_status()
            # success - return parsed JSON
            return response.json()
        
        except requests.RequestException:
            # any request error (timeout, connection, HTTP error)
            # count as a short - may break circuit
            self.circuit.short()
            return None
    
    def reset(self):
        """Reset the circuit to try again."""
        self.circuit.reset()


# USAGE

# create client
client = APIClient("https://api.example.com")

for user_id in user_ids:
    # try to fetch user data
    data = client.get(f"users/{user_id}")
    
    if data:
        # success - process the data
        process_user(data)
    
    elif client.circuit.broken:
        # circuit is broken - API is down
        # stop making requests
        print("API is down, stopping")
        break
    
    # else: request failed but circuit not broken yet
    # continue to next user

# later, when we want to try again
client.reset()
```

(end of dropdown "API client with circuit breaker")

(start of dropdown "Database connection pool")
### Database connection pool

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

class ConnectionPool:
    """Connection pool with circuit breaker for database failures."""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        
        # circuit breaker for connection failures
        # - breaks after 5 failed connection attempts
        # - sleeps 0.5 seconds when broken
        # - increases sleep by 1.5x after each reset
        # - caps at 5 seconds
        self.<suitkaise-api>circuit</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>
            num_shorts_to_trip=5,
            sleep_time_after_trip=0.5,
            backoff_factor=1.5,
            max_sleep_time=5.0
        )
    
    def get_connection(self):
        """Get a database connection with circuit breaker protection."""
        
        # fail fast if circuit is broken
        if self.circuit.broken:
            raise ConnectionPoolExhausted("<suitkaise-api>Circuit</suitkaise-api> breaker is open")
        
        try:
            # attempt to acquire a connection
            return self._acquire_connection()
        
        except ConnectionError:
            # connection failed - count it
            self.circuit.short()
            # re-raise so caller knows it failed
            raise
    
    def mark_healthy(self):
        """Call when operations succeed to reset the circuit."""
        
        # only reset if currently broken
        if self.circuit.broken:
            # reset the broken flag
            self.circuit.reset()
            # also reset backoff to original sleep time
            self.circuit.reset_backoff()
    
    def _acquire_connection(self):
        """Internal method to actually get a connection."""
        # ... implementation details ...
        pass
```

(end of dropdown "Database connection pool")

(start of dropdown "File processor with rate limiting")
### File processor with rate limiting

```python
from pathlib import Path
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

def process_files(directory: Path, max_errors_per_batch: int = 10):
    """Process all .txt files with automatic pausing on errors."""
    
    # circuit for error rate limiting
    # - trips after max_errors_per_batch errors
    # - sleeps 5 seconds on first trip
    # - doubles sleep time after each trip
    # - caps at 60 seconds
    <suitkaise-api>circ</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
        num_shorts_to_trip=max_errors_per_batch,
        sleep_time_after_trip=5.0,
        backoff_factor=2.0,
        max_sleep_time=60.0
    )
    
    # counters for summary
    processed = 0
    errors = 0
    
    # iterate over all .txt files recursively
    for file_path in directory.rglob("*.txt"):
        try:
            # attempt to process the file
            process_file(file_path)
            # success - increment counter
            processed += 1
        
        except ProcessingError as e:
            # error - increment counter and log
            errors += 1
            print(f"Error processing {file_path}: {e}")
            
            # count the error as a short
            # short() returns True if circuit tripped and slept
            if <suitkaise-api>circ.short()</suitkaise-api>:
                # we just paused - log it
                print(f"Too many errors, paused for {<suitkaise-api>circ.current_sleep_time</suitkaise-api>:.1f}s")
    
    # print summary
    print(f"Processed: {processed}, Errors: {errors}, Trips: {<suitkaise-api>circ.total_trips</suitkaise-api>}")
```

(end of dropdown "File processor with rate limiting")

(start of dropdown "Worker with graceful degradation")
### Worker with graceful degradation

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>, <suitkaise-api>BreakingCircuit</suitkaise-api>

class Worker:
    """Worker that falls back to secondary service if primary fails."""
    
    def __init__(self):
        # primary service circuit - auto-recovers
        # - trips after 3 failures
        # - sleeps 1 second, then auto-resets
        # - doubles sleep time after each trip
        # - caps at 30 seconds
        self.<suitkaise-api>primary</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
            num_shorts_to_trip=3,
            sleep_time_after_trip=1.0,
            backoff_factor=2.0,
            max_sleep_time=30.0
        )
        
        # fallback service circuit - stops if it also fails
        # - breaks after 5 failures
        # - sleeps 0.5 seconds when broken
        self.<suitkaise-api>fallback</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>
            num_shorts_to_trip=5,
            sleep_time_after_trip=0.5
        )
    
    def process(self, item):
        """Process an item, falling back to secondary service if needed."""
        
        # STEP 1: try primary service
        try:
            return self._process_primary(item)
        except PrimaryServiceError:
            # primary failed - count it
            # circuit will sleep if threshold reached
            self.primary.<suitkaise-api>short</suitkaise-api>()
        
        # STEP 2: try fallback service (only if not broken)
        if not self.fallback.<suitkaise-api>broken</suitkaise-api>:
            try:
                return self._process_fallback(item)
            except FallbackServiceError:
                # fallback also failed - count it
                # may break the fallback circuit
                self.fallback.<suitkaise-api>short</suitkaise-api>()
        
        # STEP 3: both services failed
        return None
    
    def _process_primary(self, item):
        """Process using primary service."""
        # ... implementation ...
        pass
    
    def _process_fallback(self, item):
        """Process using fallback service."""
        # ... implementation ...
        pass
```

(end of dropdown "Worker with graceful degradation")

(start of dropdown "Monitoring circuit state")
### Monitoring circuit state

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>, <suitkaise-api>BreakingCircuit</suitkaise-api>

def log_circuit_state(name: str, circ: <suitkaise-api>Circuit</suitkaise-api> | <suitkaise-api>BreakingCircuit</suitkaise-api>):
    """Log the current state of a circuit."""
    
    print(f"[{name}]")
    
    # shorts: how many failures since last trip/reset
    # num_shorts_to_trip: threshold before trip
    print(f"  shorts: {<suitkaise-api>circ.times_shorted</suitkaise-api>}/{<suitkaise-api>circ.num_shorts_to_trip</suitkaise-api>}")
    
    # total_trips: lifetime count of all trips
    print(f"  total trips: {<suitkaise-api>circ.total_trips</suitkaise-api>}")
    
    # current_sleep_time: sleep duration (after backoff applied)
    print(f"  current sleep: {<suitkaise-api>circ.current_sleep_time</suitkaise-api>:.2f}s")
    
    # broken: only exists on BreakingCircuit
    if isinstance(circ, <suitkaise-api>BreakingCircuit</suitkaise-api>):
        print(f"  broken: {<suitkaise-api>circ.broken</suitkaise-api>}")


# USAGE

# create a circuit
<suitkaise-api>circ</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0
)

# process real files and count failures
from pathlib import Path
import json

data_dir = Path("data/circuits")
data_dir.mkdir(parents=True, exist_ok=True)

# seed files (some invalid)
files = []
for i in range(20):
    path = data_dir / f"item_{i}.json"
    content = json.dumps({"id": i}) if i % 6 else '{"id":'
    path.write_text(content)
    files.append(path)

for path in files:
    try:
        json.loads(path.read_text())
    except json.JSONDecodeError:
        # count a short on bad input
        <suitkaise-api>circ.short()</suitkaise-api>
    
    # check if we just tripped (counter resets to 0 after trip)
    if <suitkaise-api>circ.times_shorted</suitkaise-api> == 0:
        # log the state right after a trip
        log_circuit_state("my_circuit", circ)
```

(end of dropdown "Monitoring circuit state")
(end of dropdown "More specific examples")

(no dropdown for the full script needed)
## Full script using `<suitkaise-api>circuits</suitkaise-api>`

A web scraper with rate limiting and failure handling.

```python
"""
In-memory scraper with circuit breakers for rate limiting and failures.

Uses two <suitkaise-api>circuits</suitkaise-api>:
- <suitkaise-api>Circuit</suitkaise-api> for rate limiting (auto-recovers after cooldown)
- <suitkaise-api>BreakingCircuit</suitkaise-api> for failures (stops after too many errors)
"""

import asyncio
import json
import hashlib
from dataclasses import dataclass
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>, <suitkaise-api>BreakingCircuit</suitkaise-api>


@dataclass
class ScrapeResult:
    """Result of scraping a single URL."""
    url: str
    status: str  # "success", "rate_limited", "server_error", "client_error", "skipped"
    data: dict | None = None
    error: str | None = None


class WebScraper:
    """Scraper with circuit breaker protection (in-memory data)."""
    
    def __init__(
        self,
        data_store: dict[str, tuple[int, dict]],
        max_rate_limits: int = 10,
        max_failures: int = 5,
        rate_limit_sleep: float = 2.0,
        failure_sleep: float = 1.0,
    ):
        self.data_store = data_store
        # CIRCUIT 1: rate limiting
        self.<suitkaise-api>rate_limiter</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
            num_shorts_to_trip=max_rate_limits,
            sleep_time_after_trip=rate_limit_sleep,
            backoff_factor=1.5,
            max_sleep_time=30.0,
            jitter=0.2
        )
        # CIRCUIT 2: failure handling
        self.<suitkaise-api>failure_circuit</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>
            num_shorts_to_trip=max_failures,
            sleep_time_after_trip=failure_sleep,
            backoff_factor=2.0,
            max_sleep_time=60.0,
            jitter=0.1
        )
    
    async def scrape(self, urls: list[str]) -> list[ScrapeResult]:
        """Scrape multiple URLs with circuit breaker protection."""
        results = []
        for url in urls:
            if self.<suitkaise-api>failure_circuit.broken</suitkaise-api>:
                results.append(ScrapeResult(
                    url=url,
                    status="skipped",
                    error="Too many failures, circuit broken"
                ))
                continue
            result = await self._scrape_url(url)
            results.append(result)
        return results
    
    async def _scrape_url(self, url: str) -> ScrapeResult:
        """Scrape a single URL with error handling."""
        status, payload = self.data_store[url]
        
        # perform real work regardless of status
        data_bytes = json.dumps(payload).encode()
        digest = hashlib.sha256(data_bytes).hexdigest()
        
        if status == 429:
            await self.<suitkaise-api>rate_limiter.short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
            return ScrapeResult(url=url, status="rate_limited")
        
        if status >= 500:
            await self.<suitkaise-api>failure_circuit.short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
            return ScrapeResult(url=url, status="server_error", error=f"HTTP {status}")
        
        if status >= 400:
            return ScrapeResult(url=url, status="client_error", error=f"HTTP {status}")
        
        # success: parse and return with hash
        data = json.loads(data_bytes)
        data["hash"] = digest[:8]
        return ScrapeResult(url=url, status="success", data=data)
    
    def get_stats(self) -> dict:
        """Get current circuit statistics."""
        return {
            "rate_limit_trips": self.<suitkaise-api>rate_limiter.total_trips</suitkaise-api>,
            "rate_limit_sleep": self.<suitkaise-api>rate_limiter.current_sleep_time</suitkaise-api>,
            "failure_trips": self.<suitkaise-api>failure_circuit.total_trips</suitkaise-api>,
            "failure_circuit_broken": self.<suitkaise-api>failure_circuit.broken</suitkaise-api>,
        }
    
    def reset(self):
        """Reset <suitkaise-api>circuits</suitkaise-api> for a new batch of URLs."""
        self.<suitkaise-api>failure_circuit.reset()</suitkaise-api>
        self.<suitkaise-api>rate_limiter.reset_backoff()</suitkaise-api>
        self.<suitkaise-api>failure_circuit.reset_backoff()</suitkaise-api>


async def main():
    # in-memory responses: url -> (status_code, payload)
    data_store = {
        "mem://users/1": (200, {"id": 1, "name": "Ada"}),
        "mem://users/2": (200, {"id": 2, "name": "Lin"}),
        "mem://users/3": (429, {"detail": "rate limited"}),
        "mem://users/4": (500, {"detail": "server error"}),
        "mem://users/5": (404, {"detail": "not found"}),
    }
    
    urls = list(data_store.keys())
    
    scraper = WebScraper(
        data_store=data_store,
        max_rate_limits=2,
        max_failures=2,
        rate_limit_sleep=2.0,
        failure_sleep=1.0,
    )
    
    results = await scraper.scrape(urls)
    
    success = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status in ("server_error",))
    skipped = sum(1 for r in results if r.status == "skipped")
    
    print(f"Results: {success} success, {failed} failed, {skipped} skipped")
    print(f"Stats: {scraper.get_stats()}")
    
    if scraper.<suitkaise-api>failure_circuit.broken</suitkaise-api>:
        print("<suitkaise-api>Circuit</suitkaise-api> broke, will reset and retry later...")
        scraper.reset()


if __name__ == "__main__":
    asyncio.run(main())
```
"
