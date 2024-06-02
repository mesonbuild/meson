## The Meson test program supports a new "--max-lines" argument

By default `meson test` only shows the last 100 lines of test output from tests
that produce large amounts of output. This default can now be changed with the
new `--max-lines` option. For example, `--max-lines=1000` will increase the
maximum number of log output lines from 100 to 1000.
