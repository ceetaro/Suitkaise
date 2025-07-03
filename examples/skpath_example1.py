from suitkaise import skpath

@skpath.autopath(autofill=True)
def print_file_path(path: str = None):
    print(f"File path: {path}")

@skpath.autopath(defaultpath=skpath.get_project_root())
def gen_id(path: str = None, short: bool = False):
    """
    Generate a short ID from the given path.
    
    If no path is provided, it uses the project root as default.
    """
    return skpath.path_id(path, short=short)



def main():
    # This will automatically fill 'path' with the caller's file path
    print_file_path()

    print(skpath.get_project_root())
    print(skpath.get_current_dir())

    path1 = skpath.SKPath()
    path2 = "/some/other/path/to/file.txt"

    if not skpath.equalpaths(path1, path2):
        print(f"Paths are different: {path1} != {path2}")

    print(path1.np)
    
    idshort = gen_id()
    print(f"Short ID: {idshort}")




if __name__ == "__main__":
    main()
