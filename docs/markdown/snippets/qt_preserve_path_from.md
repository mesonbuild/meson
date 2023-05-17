## Added `preserve_paths` keyword argument to qt module functions.

In `qt4`, `qt5`, and `qt6` modules, `compile_ui`, `compile_moc`, and
`preprocess` functions now have a `preserve_paths` keyword argument.

If `'true`, it specifies that the output files need to maintain their directory
structure inside the target temporary directory. For instance, when a file
called `subdir/one.input` is processed it generates a file
`{target private directory}/subdir/one.out` when `true`,
and `{target private directory}/one.out` when `false` (default).
