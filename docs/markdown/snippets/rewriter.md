## Rewriter improvements

The [rewriter](Rewriter.md) added support for writing the `project()`
`license_files` argument and for reading dict-valued kwargs.

It also removed the unused but mandatory `value` arguments to the
`default-options delete` and `kwargs delete` CLI subcommands.  To allow
scripts to continue supporting previous releases, these arguments are
still accepted (with a warning) if they're all equal to the empty string.
