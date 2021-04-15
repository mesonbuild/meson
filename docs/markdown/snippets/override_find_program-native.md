## Meson.override_find_program now tracks host and build overrides correctly

Previously Meson tracked the overrides in a single flat list, this means that
if you write
```meson
exe_for_host = executable(..., native : false)
exe_for_build = executable(..., native : true)
meson.override_find_program('exe', exe_for_host)
meson.override_find_program('exe', exe_for_build)
```
Meson would raise an error because `'exe'` had already been overwritten. This
has been fixed.
