## Added new `namingscheme` option

Traditionally Meson has named output targets so that they don't clash
with each other. This has meant, among other things, that on Windows
Meson uses a nonstandard `.a` suffix for static libraries because both
static libraries and import libraries have the suffix `.lib`.

There is now an option `namingscheme` that can be set to
`platform`. This new platform native naming scheme that replicates
what Rust does. That is, shared libraries on Windows get a suffix
`.dll`, static libraries get `.lib` and import libraries have the name
`.dll.lib`.

We expect to change the default value of this option to `platform` in
a future major version. Until that happens we reserve the right to
alter how `platform` actually names its output files.
