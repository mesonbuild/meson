## New action 'copy' for configure_file()

In addition to `configuration:` and `command:`,
[`configure_file()`](#Reference-manual.md#configure_file) now accepts a keyword
argument `copy:` which specifies a new action: copying the file specified with
the `input:` keyword argument to a file in the build directory with the name
specified with the `output:` keyword argument.

These three keyword arguments are, as before, mutually exclusive. You can only
do one action at a time.
