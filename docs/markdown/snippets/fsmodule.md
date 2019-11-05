## A new module for filesystem operations

The new `fs` module can be used to examine the contents of the current
file system.

```meson
fs = import('fs')
assert(fs.exists('important_file'),
       'The important file is missing.')
```
