## gtkdoc-check support

`gnome.gtkdoc()` now has a `check` keyword argument. If `true` runs it will run
`gtkdoc-check` when running unit tests. Note that this has the downside of
rebuilding the doc for each build, which is often very slow. It usually should
be enabled only in CI.

## `gnome.gtkdoc()` returns target object

`gnome.gtkdoc()` now returns a target object that can be passed as dependency to
other targets using generated doc files (e.g. in `content_files` of another doc).
