## `meson format` file sorting is now disabled by default and uses natural sorting

The `sort_files` option to `meson format`, which sorts the arguments of
`files()` invocations, is now disabled by default.

If the `sort_files` option is enabled, `meson format` now sorts `files()`
arguments [naturally](Style-guide.md#sorting-source-paths) rather than
alphabetically.
