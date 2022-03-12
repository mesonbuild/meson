## D compiler checks

Some compiler checks are implemented for D:
 - `run`
 - `sizeof`
 - `has_header` (to check if a module is present)
 - `alignment`

Example:

```meson
ptr_size = meson.get_compiler('d').sizeof('void*')
```
