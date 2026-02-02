show what happens when cucumber cannot serialize an object

add async serialization

allow people to add their own handlers maybe

- 2 args: function to serialize and function to deserialize
- user passed handlers need to serialize to pickle native types or bytes.
- cucumber will return a UserHandlerError if a UserHandler fails to serialize.

add a module page called benchmarks and supported types to show the speed of cucumber compared against other serialization libraries for a certain object for all types cucumber can serialize and deserialize


