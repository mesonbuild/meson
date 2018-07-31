## New kwarg `console` for `custom_target()`

This keyword argument conflicts with `capture`, and is meant for
commands that are resource-intensive and take a long time to
finish. With the Ninja backend, setting this will add this target to
[Ninja's `console`
pool](https://ninja-build.org/manual.html#_the_literal_console_literal_pool),
which has special properties such as not buffering stdout and
serializing all targets in this pool.

The primary use-case for this is to be able to run external commands
that take a long time to exeute. Without setting this, the user does
not receive any feedback about what the program is doing.
