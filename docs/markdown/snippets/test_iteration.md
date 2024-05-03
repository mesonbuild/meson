## meson test now sets the `MESON_TEST_ITERATION` environment variable

`meson test` will now set the `MESON_TEST_ITERATION` environment variable to the
current iteration of the test. This will always be `1` unless `--repeat` is used
to run the same test multiple times.
