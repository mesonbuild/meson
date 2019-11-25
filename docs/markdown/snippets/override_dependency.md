## `dependency()` consistency

The first time a dependency is found, using `dependency('foo', ...)`, the return
value is now cached. Any subsequent call will return the same value as long as
version requested match, otherwise not-found dependency is returned. This means
that if a system dependency is first found, it won't fallback to a subproject
in a subsequent call any more and will rather return not-found instead if the
system version does not match. Similarly, if the first call returns the subproject
fallback dependency, it will also return the subproject dependency in a subsequent
call even if no fallback is provided.

For example, if the system has `foo` version 1.0:
```meson
# d2 is set to foo_dep and not the system dependency, even without fallback argument.
d1 = dependency('foo', version : '>=2.0', required : false,
                fallback : ['foo', 'foo_dep'])
d2 = dependency('foo', version : '>=1.0', required : false)
```
```meson
# d2 is not-found because the first call returned the system dependency, but its version is too old for 2nd call.
d1 = dependency('foo', version : '>=1.0', required : false)
d2 = dependency('foo', version : '>=2.0', required : false,
                fallback : ['foo', 'foo_dep'])
```

## Override `dependency()`

It is now possible to override the result of `dependency()` to point
to any dependency object you want. The overriding is global and applies to
every subproject from there on.

For example, this subproject provides 2 libraries with version 2.0:

```meson
project(..., version : '2.0')

libfoo = library('foo', ...)
foo_dep = declare_dependency(link_with : libfoo)
meson.override_dependency('foo', foo_dep)

libbar = library('bar', ...)
bar_dep = declare_dependency(link_with : libbar)
meson.override_dependency('bar', bar_dep)
```

Assuming the system has `foo` and `bar` 1.0 installed, and master project does this:
```meson
foo_dep = dependency('foo', version : '>=2.0', fallback : ['foo', 'foo_dep'])
bar_dep = dependency('bar')
```

This used to mix system 1.0 version and subproject 2.0 dependencies, but thanks
to the override `bar_dep` is now set to the subproject's version instead.

Another case this can be useful is to force a subproject to use a specific dependency.
If the subproject does `dependency('foo')` but the main project wants to provide
its own implementation of `foo`, it can for example call
`meson.override_dependency('foo', declare_dependency(...))` before configuring the
subproject.

## Simplified `dependency()` fallback

In the case a subproject `foo` calls `meson.override_dependency('foo-2.0', foo_dep)`,
the parent project can omit the dependency variable name in fallback keyword
argument: `dependency('foo-2.0', fallback : 'foo')`.
