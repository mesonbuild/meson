## `meson format` has a new `--check-diff` option

When using `meson format --check-only` to verify formatting in CI, it would
previously silently exit with an error code if the code was not formatted
correctly.

A new `--check-diff` option has been added which will instead print a diff of
the required changes and then exit with an error code.
