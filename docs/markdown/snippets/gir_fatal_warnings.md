## Fatal warnings in `gnome.generate_gir()`

`gnome.generate_gir()` now has `fatal_warnings` keyword argument to abort when
a warning is produced. This is useful for example in CI environment where it's
important to catch potential issues.
