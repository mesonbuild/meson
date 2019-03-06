## `meson test -v` prints command lines

When `meson test` is invoked with the `-v` command line options, for
each test that it runs it will print the command line that was invoked.
This makes it a bit easier to cut and paste from a failing test log into
a terminal.
