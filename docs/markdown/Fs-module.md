# FS (filesystem) module

This module provides functions to inspect the file system. It is
available starting with version 0.53.0.

## File lookup rules

Non-absolute paths are looked up relative to the directory where the
current `meson.build` file is.

### exists

Takes a single string argument and returns true if an entity with that
name exists on the file system. This can be a file, directory or a
special entry such as a device node.

### is_dir

Takes a single string argument and returns true if a directory with
that name exists on the file system. This method follows symbolic
links.

### is_file

Takes a single string argument and returns true if an file with that
name exists on the file system. This method follows symbolic links.

### is_symlink

Takes a single string argument and returns true if the path pointed to
by the string is a symbolic link.
