## `gnome.compile_schemas()` sets `GSETTINGS_SCHEMA_DIR` into devenv

When using `gnome.compile_schemas()` the location of the compiled schema is
added to `GSETTINGS_SCHEMA_DIR` environment variable when using
[`meson devenv`](Commands.md#devenv) command.

## `update_desktop_database` added to `gnome.post_install()`

Applications that install a `.desktop` file containing a `MimeType` need to update
the cache upon installation. Most applications do that using a custom script,
but it can now be done by Meson directly.

See [`gnome.post_install()`](Gnome-module.md#gnomepost_install).
