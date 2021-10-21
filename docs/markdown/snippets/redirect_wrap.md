## Redirect wraps are deprecated

When Meson promote a `.wrap` file from another subproject, it used to create
a new `.wrap` file in the main project with `[wrap-redirect]` section.

Those files created lots of confusion so Meson will not create them any more.
Existing files will keep working but will produce a deprecation warning.
