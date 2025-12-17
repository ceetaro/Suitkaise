## sktime

organize timer class to have all stats be accessed like this:

timer.stats.mean instead of timer.mean

that way, instead of creating a TimerStats to return data, we can just hold one and return that for get_statistics()
---
have an option to stop the time and not record the result
---
ensure that start and stop dont fail if called like (ex. start when already started or stop while not started)

---
consider removing lap as it can be confusing and redundant with stop + start. there are better options for timing mutliple executions through in all cases (decorator or context manager)

or:

have lap() be a start call if no timing is in progress
and have it be a stop and start call if timing is in progress

but this could be confusing.

---

add an alias for get_statistics() called get_stats()

---

streamline the percentile. why does get_statistics() return a dictionary with 95th and 99th percentile times? but you cant access those directly as properties without using get_statistics()?

---

improve the context manager.

right now, it is accessed like: cm.timer.something

but should it be accessed like: cm.something ?

---

does the yawn class overlap too much with the circuit module? it might be redundant and force more usage of the circuit module.