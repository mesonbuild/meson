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

### is_samepath

The `fs.is_samepath(path1, path2)` returns boolean `true` if both paths resolve to the same path.
For example, suppose path1 is a symlink and path2 is a relative path.
If path1 can be resolved to path2, then `true` is returned.
If path1 is not resolved to path2, `false` is returned.
If path1 or path2 do not exist, `false` is returned.

Examples:

```meson
x = 'foo.txt'
y = 'sub/../foo.txt'
z = 'bar.txt'  # a symlink pointing to foo.txt
j = 'notafile.txt'  # non-existant file

fs.is_samepath(x, y)  # true
fs.is_samepath(x, z)  # true
fs.is_samepath(x, j)  # false

p = 'foo/bar'
q = 'foo/bar/../baz'
r = 'buz'  # a symlink pointing to foo/bar
s = 'notapath'  # non-existant directory

fs.is_samepath(p, q)  # true
fs.is_samepath(p, r)  # true
fs.is_samepath(p, s)  # false
```


## Filename modification

The files need not actually exist yet for this method, as it's just string manipulation.

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

### parent

Returns the parent directory (i.e. dirname).

### name

Returns the last component of the path (i.e. basename).
