## Controlling subproject dependencies with  `dependency(allow_fallback: ...)`

As an alternative to the `fallback` keyword argument to `dependency`,
you may use `allow_fallback`, which accepts a boolean value. If `true`
and the dependency is not found on the system, Meson will fallback
to a subproject that provides this dependency, even if the dependency
is optional. If `false`, Meson will not fallback even if a subproject
provides this dependency.
