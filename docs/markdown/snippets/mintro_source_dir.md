## `introspect` command now accepts source dir as argument

Previously, the [meson introspect](Commands.md#introspect) command was
accepting the path to the `meson.build` file as argument, but not the source
directory itself. It is now possible to give to `introspect` command the path to
the source directory, and the contained `meson.build` file will be analysed.
