## `unset_variable()`

`unset_variable()` can be used to unset a variable. Reading a variable after
calling `unset_variable()` will raise an exception unless the variable is set
again.

```meson
# tests/meson.build
tests = ['test1', 'test2']

# ...

unset_variable('tests')

# tests is no longer usable until it is set again
```
