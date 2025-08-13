this is an unreleased project, so backwards compatibility is not needed.

concept.md: goal api for the module and simple explanations of how to use said goal api. refer to the skpath concept.md file for an example of how to do these files.

most of the api will already be present in the concept.md files. if there is implemented code that doesn't have api, we will sort it out. do not directly change api in the concept, rather bring up discrepancies between the concept and the code in api.py for that module.

for real world examples, the examples should be snapshots of real code and show how pain points are resolved using the module, with contextual explanation outside of the code.

info.md: 

1. we take an item from __all__ in the api.py file
2. we explain how it actually works under the hood in detail
3. we rinse and repeat for every item in __all__

4. we reread the data in info.md,and organize sections that repeat themselves over several items into one section, and then reference the section where the item is explained.

todo.md: what needs to happen in order to get current code to the next steps. this is a very short term checklist, as the concept.md file outlines the long term goals.

example.py: file that runs the api seen in the concept file, as well as applicable real usage examples. gives the user the decision to run certain examples.