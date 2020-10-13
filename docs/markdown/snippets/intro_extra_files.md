## New `extra_files` key in target introspection

The target introspection (`meson introspect --targets`, `intro-targets.json`)
now has the new `extra_files` key which lists all files specified via the
`extra_files` kwarg of a build target (see `executable()`, etc.)

