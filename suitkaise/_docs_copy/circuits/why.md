# Why you would use `circuit`

In electical engineering, a circuit breaker is a device that protects an electrical circuit by interrupting the flow of electricity when a fault occurs.

In software engineering, a circuit breaker is a pattern that protects your code by interrupting the flow of execution when an error occurs.

`circuit` gives you two patterns to manage your code.

- `Circuit`
Auto-resets after sleeping. Great for rate limiting, resource management, and more.

- `BreakingCircuit`
Stays broken until manually reset. Great for halting execution with control after a certain number of failures.

## What separates `circuits` from other circuit breaker libraries?

`circuits` is thread-safe.

`circuits` has native async support.

### Without `circuits` - 


### With `circuits` - 




