## The qt modules now accept generated outputs as inputs for qt.compile_*

This means you can uset `custom_target`, custom_target indecies
(`custom_target[0]`, for example), or the output of `generator.process` as
inputs to the various `qt.compile_*` methods.

```meson
qt = import('qt5')

ct = custom_target(...)

out = qt.compile_ui(sources : ct)
```
