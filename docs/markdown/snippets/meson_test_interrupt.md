## Ctrl-C behavior in `meson test`

Starting from this version, sending a `SIGINT` signal (or pressing `Ctrl-C`)
to `meson test` will interrupt the longest running test.  Pressing `Ctrl-C`
three times within a second will exit `meson test`.
