## `unstable_external_project` improvements

- Default arguments are added to `add_project()` in case some tags are not found
  in `configure_options`: `'--prefix=@PREFIX@'`, `'--libdir=@PREFIX@/@LIBDIR@'`,
  and `'--includedir=@PREFIX@/@INCLUDEDIR@'`. It was previously considered a fatal
  error to not specify them.

- When the `verbose` keyword argument is not specified, or is false, command outputs
  are written on file in `<builddir>/meson-logs/`.

- The `LD` environment variable is not passed any more when running the configure
  script. It caused issues because Meson sets `LD` to the `CC` linker wrapper but
  autotools expects it to be a real linker (e.g. `/usr/bin/ld`).
