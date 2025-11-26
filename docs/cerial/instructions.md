# instructions for ai agents to understand cerial and related modules used to build it

1. cerial

read docs/cerial/concept.md
- ALWAYS DO THIS!!!

2. if and only if you are reviewing the file handle handler, review skpath

understand how skpath works by reading docs/skpath/concept.md

- we use skpath to streamline path handling for file handle serialization and deserialization/reconstruction.

3. review handlers and ensure that implementations are correct and complete.

- COMPLETED ✓
- enums are now handled ✓
- fixed critical import bug (advanced_handler -> advanced_py_handler) ✓

4. double check all handlers and make sure the initial eye test passes.

- COMPLETED ✓
- all handlers follow the Handler base class pattern correctly
- extraction and reconstruction logic is properly implemented
- handlers do NOT call other handlers (central serializer handles recursion)
- all handlers return clean state dicts for the central serializer
- enum handler added and integrated

5. NEXT: start work on the central serializer and deserializer/reconstructor.