## Wildcards in list of tests to run

The `meson test` command now accepts wildcards in the list of test names.
For example `meson test basic*` will run all tests whose name begins
with "basic".

meson will report an error if the given test name does not match any
existing test. meson will log a warning if two redundant test names
are given (for example if you give both "proj:basic" and "proj:").
