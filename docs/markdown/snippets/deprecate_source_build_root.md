## `meson.build_root()` and `meson.source_root()` are deprecated

Those function are common source of issue when used in a subproject because they
point to the parent project root which is rarely what is expected and is a
violation of subproject isolation.
