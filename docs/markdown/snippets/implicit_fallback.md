## Implicit dependency fallback

`dependency('foo')` now automatically fallback if the dependency is not found on
the system but a subproject wrap file or directory exists with the same name.

That means that simply adding `subprojects/foo.wrap` is enough to add fallback
to any `dependency('foo')` call. It is however requires that the subproject call
`meson.override_dependency('foo', foo_dep)` to specify which dependency object
should be used for `foo`.
