## Implicit dependency fallback

`dependency('foo')` now automatically fallback if the dependency is not found on
the system but a subproject wrap file or directory exists with the same name.

That means that simply adding `subprojects/foo.wrap` is enough to add fallback
to any `dependency('foo')` call. It is however requires that the subproject call
`meson.override_dependency('foo', foo_dep)` to specify which dependency object
should be used for `foo`.

## Wrap file `provide` section

Wrap files can define the dependencies it provides in the `[provide]` section.
When a wrap file provides the dependency `foo` any call do `dependency('foo')`
will automatically fallback to that subproject even if no `fallback` keyword
argument is given. See [Wrap documentation](Wrap-dependency-system-manual.md#provide_section).
