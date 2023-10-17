## Machine files: `pkgconfig` field deprecated and replaced by `pkg-config`

Meson used to allow both `pkgconfig` and `pkg-config` entries in machine files,
the former was used for `dependency()` lookup and the latter was used as return
value for `find_program('pkg-config')`.

This inconsistency is now fixed by deprecating `pkgconfig` in favor of
`pkg-config` which matches the name of the binary. For backward compatibility
it is still allowed to define both with the same value, in that case no
deprecation warning is printed.
