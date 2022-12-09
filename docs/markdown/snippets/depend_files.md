## Deprecated `depend_files` keyword argument

[[custom_target]] had two similar keyword arguments: `depends` and `depend_files`.
They have been merged together, `depends` now accepts Files and string arguments,
and `depend_files` has been deprecated.

A similar change has been done on functions that use [[custom_target]] internally:
- gnome.genmarshal()
- gnome.compile_schemas()
- windows.compile_resources()
