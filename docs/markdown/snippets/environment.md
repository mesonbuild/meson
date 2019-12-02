## environment() now had `separator` and `method` keyword arguments

This is useful to control how initial values are added. `method` must be one of
'set', 'prepend' or 'append' strings.

```meson
environment({'MY_VAR': ['a', 'b']}, method: 'prepend', separator=',')
```
