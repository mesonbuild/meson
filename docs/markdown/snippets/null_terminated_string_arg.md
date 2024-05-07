## Added support for GCC's `null_terminated_string_arg` function attribute

You can now check if a compiler support the `null_terminated_string_arg`
function attribute via the `has_function_attribute()` method on the
[[@compiler]] object.

```meson
cc = meson.get_compiler('c')

if cc.has_function_attribute('null_terminated_string_arg')
  # We have it...
endif
```
