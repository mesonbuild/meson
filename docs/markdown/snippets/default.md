## Add a new `default()` function and object

This function and object allow setting a keyword argument to it's default value.
This is especially useful for cases when a non-default value is wanted in some
cases but not all.

For example:
```meson
library(
  ...
  name_prefix : host_machine.system() == 'windows' ? '' : default(),
)
```
