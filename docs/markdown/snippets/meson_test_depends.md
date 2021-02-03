## `meson test` only rebuilds test dependencies

Until now, `meson test` rebuilt the whole project independent of the
requested tests and their dependencies.  With this release, `meson test`
will only rebuild what is needed for the tests or suites that will be run.
This feature can be used, for example, to speed up bisecting regressions
using commands like the following:

    git bisect start <broken commit> <working commit>
    git bisect run meson test <failing test name>

This would find the broken commit automatically while at each step
rebuilding only those pieces of code needed to run the test.

However, this change could cause failures when upgrading to 0.57, if the
dependencies are not specified correctly in `meson.build`.
