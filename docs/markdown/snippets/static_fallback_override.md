## `static` keyword argument to `meson.override_dependency()`

It is now possible to override shared and/or static dependencies separately.
When the `static` keyword argument is not specified in `dependency()`, the first
override will be used (`static_dep` in the example below).
```meson
static_lib = static_library()
static_dep = declare_dependency(link_with: static_lib)
meson.override_dependency('foo', static_dep, static: true)

shared_lib = shared_library()
shared_dep = declare_dependency(link_with: shared_lib)
meson.override_dependency('foo', shared_dep, static: false)

# Returns static_dep
dependency('foo')

# Returns static_dep
dependency('foo', static: true)

# Returns shared_dep
dependency('foo', static: false)
```

When the `static` keyword argument is not specified in `meson.override_dependency()`,
the dependency is assumed to follow the value of `default_library` option.
```meson
dep = declare_dependency(...)
meson.override_dependency('foo', dep)

# Always works
dependency('foo')

# Works only if default_library is 'static' or 'both'
dependency('foo', static: true)

# Works only if default_library is 'shared' or 'both'
dependency('foo', static: false)
```

## `dependency()` sets `default_library` on fallback subproject

When the `static` keyword argument is set but `default_library` is missing in
`default_options`, `dependency()` will set it when configuring fallback
subproject. `dependency('foo', static: true)` is now equivalent to
`dependency('foo', static: true, default_options: ['default_library=static'])`.
