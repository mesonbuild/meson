## Added integer base conversions to `str.to_int()` and `int.to_string()`

Meson strings can now be converted from hexadecimal, octal, and binary
integer literals with `str.to_int()`. Integers can also be formatted back to
strings in those bases with `int.to_string(format:)`.

```meson
assert('0xff'.to_int() == 255)
assert(255.to_string(format: 'hex') == '0xff')
```
