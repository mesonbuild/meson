## Add support for `find_library` in Emscripten

The `find_library` method can be used to find your own JavaScript
libraries. The limitation is that they must have the file extension
`.js`. Other library lookups will look up "native" libraries from the
system like currently. A typical usage would look like this:

```meson
glue_lib = cc.find_library('gluefuncs.js',
                           dirs: meson.current_source_dir())
executable('prog', 'prog.c',
           dependencies: glue_lib)
```
