# FS (filesystem) module

This module provides functions to inspect the file system. It is
available starting with version 0.53.0.

## File lookup rules

Non-absolute paths are looked up relative to the directory where the
current `meson.build` file is.

If specified, a leading `~` is expanded to the user home directory.

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

## File Parameters

### hash

The `fs.hash(filename, hash_algorithm)` method returns a string containing
the hexidecimal `hash_algorithm` digest of a file.
`hash_algorithm` is a string; the available hash algorithms include:
md5, sha1, sha224, sha256, sha384, sha512.

### size

The `fs.size(filename)` method returns the size of the file in integer bytes.
Symlinks will be resolved if possible.

### samefile

The `fs.samefile(filename1, filename2)` returns boolean `true` if the input filenames refer to the same file.
For example, suppose filename1 is a symlink and filename2 is a relative path.
If filename1 can be resolved to a file that is the same file as filename2, then `true` is returned.
If filename1 is not resolved to be the same as filename2, `false` is returned.
If either filename does not exist, an error message is raised.

Examples:

```meson
x = 'foo.txt'
y = 'sub/../foo.txt'
z = 'bar.txt'  # a symlink pointing to foo.txt

fs.samefile(x, y)  # true
fs.samefile(x, z)  # true
```


## Filename modification

### replace_suffix

The `replace_suffix` method is a *string manipulation* convenient for filename modifications.
It allows changing the filename suffix like:

#### swap suffix

```meson
original = '/opt/foo.ini'
new = fs.replace_suffix(original, '.txt')  # /opt/foo.txt
```

#### add suffix

```meson
original = '/opt/foo'
new = fs.replace_suffix(original, '.txt')  # /opt/foo.txt
```

#### compound suffix swap

```meson
original = '/opt/foo.dll.a'
new = fs.replace_suffix(original, '.so')  # /opt/foo.dll.so
```

#### delete suffix

```meson
original = '/opt/foo.dll.a'
new = fs.replace_suffix(original, '')  # /opt/foo.dll
```

The files need not actually exist yet for this method, as it's just string manipulation.