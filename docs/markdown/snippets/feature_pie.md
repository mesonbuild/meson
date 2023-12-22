## Option `b_pie` is now a feature option

The `b_pie` option can now be passed the values `enabled`, `auto`, `disabled`.
The previously accepted values `true` and `false` map to `enabled` and `auto`
respectively, but are deprecated.  This makes it possible to force Meson to
build position-*dependent* executables on platforms that support them.

On some platforms position-dependent code is not supported at all (for example,
Android).  On those platforms, `b_pie` will have no effect even if disabled.

For backwards compatibility, `get_option('b_pie')` will return a boolean unless
the required Meson version (as declared in the `project()` statement) is at
least 1.4.0.
