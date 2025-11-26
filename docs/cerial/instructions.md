# instructions for ai agents to understand cerial and related modules used to build it

1. cerial

read docs/cerial/concept.md

2. if you are reviewing the file handle handler, review skpath

understand how skpath works by reading docs/skpath/concept.md

- we use skpath to streamline path handling for file handle serialization and deserialization/reconstruction.

3. review handlers and ensure that implementations are correct and complete.

- this is where we are now.
- ensure that we handle enums.

4. NEXT: redo the worst possible object to ensure that it correctly tests everything.