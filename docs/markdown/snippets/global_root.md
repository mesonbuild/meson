## New `meson.global_build_root()` and `meson.global_source_root()` methods

Returns the root source and build directory of the main project.

Those are direct replacement for `meson.build_root()` and `meson.source_root()`
that have been deprecated since 0.56.0. In some rare occasions they could not be
replaced by `meson.project_source_root()` or `meson.current_source_dir()`, in
which case the new methods can now be used instead. Old methods are still
deprecated because their names are not explicit enough and created many issues
when a project is being used as a subproject.
