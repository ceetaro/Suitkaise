change `SKPath.np` to one of these:

- `rp` — relative path
- `sp` - short path
- `sp` - special path
- `p` - path
- `skp` - sk/suitkaise path (my choice right now)

add path validation utils

- is_valid_filename() - checks if a filename is valid


- streamline_path() - sanitizes a path by removing invalid characters

this is something the user can use to streamline path names
- cut down to a max length
- replace invalid characters with a different character
- lowercase the path
- strip whitespace
- allow/disallow unicode characters


add examples of common tasks like getting all files with a certain suffix

