## skpath improvements

- for all functions in the api that just call private versions of themselves:

- get rid of the unnecessary extra "_function_name" call, and just move the non underscore version to the _int.py file.

- keep the docstrings from the api

- just import the public versions you moved to _int.py back into the api file.


- change path_id() to id(). remove path id short and add a length param to id()

- remove the id_short property from the SKPath class.

for get_project_paths, get_project_structure, and get_formatted_project_tree:

- force keyword only args

- change ignore to use_ignore_files
- change except_paths to exclude
- change as_str to as_strings
- change custom_root to root

- change show_files to include_files
- change max_depth to depth


- move SKPath to the _int.py file.


- change force project root to set_custom_root
- change clear_forced_root to clear_custom_root
- change get_forced_root to get_custom_root
- change ForceRoot to CustomRoot


- autopath should also convert for lists and other single typed iterables of valid types based on its existing rules.
- remove default param from autopath. let users just set a default value for the parameter in the function definition.

- need a way to convert ids back to SKPaths.
- need to be able to create an SKPath from an id.


- remove the returning none for get_project_root, let it raise a PathDetectionError if it can't find a root with expected_name.

- maybe change get_module_path to get_source or get_origin

- make equalpaths() private and streamline all comparisons to use path1 == path2 syntax (which uses equalpaths() internally if a SKPath is present)

- maybe even remove id() function and just have it be a property of SKPath.

### reworking ?s

are all of the SKPath properties and methods needed or are some redundant?

do we need to look at directory names to determine the project root? or just files? if we only had to look at files, it could be a lot more consistent. or at least get rid of some of the dirs that could vary by user or project.

