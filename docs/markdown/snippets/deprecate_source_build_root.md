## `meson.build_root()` and `meson.source_root()` are deprecated

Those function are common source of issue when used in a subproject because they
point to the parent project root which is rarely what is expected and is a
violation of subproject isolation.

`meson.current_source_dir()` and `meson.current_build_dir()` should be used instead
and have been available in all Meson versions. New functions `meson.project_source_root()`
and `meson.project_build_root()` have been added in Meson 0.56.0 to get the root
of the current (sub)project.
