## vs_module_defs keyword now supports indexes of custom_target

This means you can do something like:
```meson
defs = custom_target('generate_module_defs', ...)
shared_library('lib1', vs_module_defs : defs[0])
shared_library('lib2', vs_module_defs : defs[2])
```
