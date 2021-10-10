## Deprecated project options

Project options declared in `meson_options.txt` can now be marked as deprecated
and Meson will warn when user sets a value to it. It is also possible to deprecate
only some of the choices, and map deprecated values to a new value.

```meson
# Option fully deprecated, it warns when any value is set.
option('o1', type: 'boolean', deprecated: true)

# One of the choices is deprecated, it warns only when 'a' is in the list of values.
option('o2', type: 'array', choices: ['a', 'b'], deprecated: ['a'])

# One of the choices is deprecated, it warns only when 'a' is in the list of values
# and replace it by 'c'.
option('o3', type: 'array', choices: ['a', 'b', 'c'], deprecated: {'a': 'c'})

# A boolean option has been replaced by a feature, old true/false values are remapped.
option('o4', type: 'feature', deprecated: {'true': 'enabled', 'false': 'disabled'})

# A feature option has been replaced by a boolean, enabled/disabled/auto values are remapped.
option('o5', type: 'boolean', deprecated: {'enabled': 'true', 'disabled': 'false', 'auto': 'false'})
```
