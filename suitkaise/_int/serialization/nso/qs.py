import inspect

def get_module_file_path(obj):
    module = inspect.getmodule(obj)
    if module:
        return module.__file__
    return None

# Example usage
class ExampleClass:
    pass

file_path = get_module_file_path(ExampleClass)
print(f"File path of the module: {file_path}")