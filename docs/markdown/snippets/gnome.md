## `gnome.compile_schemas()` sets `GSETTINGS_SCHEMA_DIR` into devenv

When using `gnome.compile_schemas()` the location of the compiled schema is
added to `GSETTINGS_SCHEMA_DIR` environment variable when using
[`meson devenv`](Commands.md#devenv) command.
