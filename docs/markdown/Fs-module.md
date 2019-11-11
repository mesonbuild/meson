# FS (filesystem) module

This module provides functions to inspect the file system. It is
available starting with version 0.53.0.

## File lookup rules

Non-absolute paths are looked up relative to the directory where the
current `meson.build` file is.

If specified, `~` is expanded to the user home directory.

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

## Filename modification

### with_suffix

The `with_suffix` method is a *string manipulation* convenient for filename modifications.
It allows changing the filename suffix like:

## swap suffix

```meson
original = '/opt/foo.ini'
new = fs.with_suffix('.txt')  # /opt/foo.txt
```

#### add suffix

```meson
original = '/opt/foo'
new = fs.with_suffix('.txt')  # /opt/foo.txt
```

#### compound suffix swap

```meson
original = '/opt/foo.dll.a'
new = fs.with_suffix('.so')  # /opt/foo.dll.so
```

#### delete suffix

```meson
original = '/opt/foo.dll.a'
new = fs.with_suffix('')  # /opt/foo.dll
```

The files need not actually exist yet for this method, as it's just string manipulation.