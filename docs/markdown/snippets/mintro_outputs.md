## Redirect introspection outputs to stderr

`meson introspect` used to disable logging to `stdout` to not interfere with generated json.
It now redirect outputs to `stderr` to allow printing warnings to the console
while keeping `stdout` clean for json outputs.
