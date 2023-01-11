## coercing values in the option() function is deprecated

Currently code such as:
```meson
option('foo', type : 'boolean', value : 'false')
```
works, because Meson coerces `'false'` to `false`.

This should be avoided, and will now result in a deprecation warning.
