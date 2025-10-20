# SKTime TODO

-1: time_ops was moved to ..sktime/_int/time_ops.py. ensure that all reference imports to time_ops are updated to the new location across the project. *DONE*

0. ensure that init files work as intended and documented (incl. documented in quiz) *DONE*
options to import:
- from suitkaise import sktime
- from suitkaise.sktime import (something)

1. ensure that concept.md matches api content *DONE*
- the api represents the final rendition of v1.0.0 of the module. the concept file has not been updated to reflect this.

2. recreate the info.md file to actually explain how each component works internally *DONE*
- the info file needs to be redone completely from scratch and actually document exactly how sktime works

3. recreate the final test suite and test everything
- including performance tests
- including thread safety tests

4. create the example.py file that will give an in-depth example of how to use the module
5. ensure that quiz is accurate and correctly formatted (and that content in questions is possible, works, and accurately matches the api)

6. create the final documentation for the module
7. create the suitkaise website
8. update project status and dependencies
9. check that only sktime works when uploaded to test pypi
10. upload to pypi

