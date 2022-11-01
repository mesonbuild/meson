## Add fs.relative_to function to get a path relative to another path

Finding what is the path to a directory relative to another directory is now possible.
For instance to find the path to `/foo/lib` as if we were in `/foo/bin` we now can use:

```meson
fs = import('fs')
fs.relative_to('/foo/lib', '/foo/bin')` #  '../lib'
```

