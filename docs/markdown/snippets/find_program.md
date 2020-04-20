## find_program: Fixes when the program has been overridden by executable

When a program has been overridden by an executable, the returned object of
find_program() had some issues:

```meson
# In a subproject:
exe = executable('foo', ...)
meson.override_find_program('foo', exe)

# In main project:
# The version check was crashing meson.
prog = find_program('foo', version : '>=1.0')

# This was crashing meson.
message(prog.path())

# New method to be consistent with built objects.
message(prog.full_path())
```
