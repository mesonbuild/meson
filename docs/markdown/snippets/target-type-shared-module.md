## `target_type` in `build_targets` accepts the value 'shared_module'

The `target_type` keyword argument in `build_target()` now accepts the
value `'shared_module'`.

The statement

```meson
build_target(..., target_type: 'shared_module')
```

is equivalent to this:

```meson
shared_module(...)
```
