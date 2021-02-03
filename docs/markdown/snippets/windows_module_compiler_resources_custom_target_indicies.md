## `windows.compiler_resources` now accepts indices of `custom_targets`

You may now write:
```meson
ct = custom_target(...)

win = import('windows')
win.compile_resources(ct[0])
```
