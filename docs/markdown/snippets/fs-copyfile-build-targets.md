## `fs.copyfile()` now accepts build targets as input

`fs.copyfile()` now accepts `build_tgt`, `custom_tgt`, and `custom_idx`
as the source argument, in addition to `File` and `str`. This makes it
possible to copy build artifacts without resorting to a `custom_target`.
