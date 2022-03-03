## D features in `declare_dependency`

`declare_dependency`accepts parameters for D specific features.
Accepted new parameters are `d_module_features` and `d_import_dirs`.

This can be useful to propagate conditional compilation versions. E.g.:

```meson
my_lua_dep = declare_dependency(
    # ...
    d_module_features: ['LUA_53'],
    d_import_dirs: include_directories('my_lua_folder'),
)
```
