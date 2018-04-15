## New keyword arguments: 'check' and 'capture' for run_command()

If `check:` is `true`, then the configuration will fail if the command returns a
non-zero exit status. The default value is `false` for compatibility reasons.

`run_command()` used to always capture the output and stored it for use in
build files. However, sometimes the stdout is in a binary format which is meant
to be discarded. For that case, you can now set the `capture:` keyword argument
to `false`.
