## File object now has `full_path()` method

Returns a full path pointing to the file. This is useful for printing the path
with e.g [[message]] function for debugging purpose.

**NOTE:** In most cases using the object itself will do the same job
as this and will also allow Meson to setup dependencies correctly.
