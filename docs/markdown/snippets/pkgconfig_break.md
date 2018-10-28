## Deprecation warning in pkg-config generator

All libraries passed to the `libraries` keyword argument of the `generate()`
method used to be associated with that generated pkg-config file. That means
that any subsequent call to `generate()` where those libraries appear would add
the filebase of the `generate()` that first contained them into `Requires:` or
`Requires.private:` field instead of adding an `-l` to `Libs:` or `Libs.private:`.

This behaviour is now deprecated. The library that should be associated with
the generated pkg-config file should be passed as first positional argument
instead of in the `libraries` keyword argument. The previous behaviour is
maintained but prints a deprecation warning and support for this will be removed
in a future Meson release. If you can not create the needed pkg-config file
without this warning, please file an issue with as much details as possible
about the situation.

For example this sample will write `Requires: liba` into `libb.pc` but print a
deprecation warning:
```meson
liba = library(...)
pkg.generate(libraries : liba)

libb = library(...)
pkg.generate(libraries : [liba, libb])
```

It can be fixed by passing `liba` as first positional argument::
```meson
liba = library(...)
pkg.generate(liba)

libb = library(...)
pkg.generate(libb, libraries : [liba])
```
