## Diff files for wraps

Wrap files can now define `diff_files`, a list of local patch files in `diff`
format. Meson will apply the diff files after extracting or cloning the project,
and after applying the overlay archive (`patch_*`). For this feature, the
`patch` or `git` command-line tool must be available.
