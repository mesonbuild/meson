## New logging format for `meson test`

The console output format for `meson test` has changed in several ways.
The major changes are:

* if stdout is a tty, `meson` includes a progress report.

* if `--print-errorlogs` is specified, the logs are printed as tests run
rather than afterwards.  All the error logs are printed rather than only
the first ten.

* if `--verbose` is specified and `--num-processes` specifies more than
one concurrent test, test output is buffered and printed after the
test finishes.

* the console logs include a reproducer command.  If `--verbose` is
specified, the command is printed for all tests at the time they start;
otherwise, it is printed for failing tests at the time the test finishes.

* for TAP and Rust tests, Meson is able to report individual subtests.  If
`--verbose` is specified, all tests are reported.  If `--print-errorlogs`
is specified, only failures are.

In addition, if `--verbose` was specified, Meson used not to generate
logs.  This limitation has now been removed.

These changes make the default `ninja test` output more readable, while
`--verbose` output provides detailed, human-readable logs that
are well suited to CI environments.
