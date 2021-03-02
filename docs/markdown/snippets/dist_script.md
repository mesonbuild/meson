## `meson.add_dist_script()` allowd in subprojects

`meson.add_dist_script()` can now be invoked from a subproject, it was a hard
error in earlier versions. Subproject dist scripts will only be executed
when running `meson dist --include-subprojects`. `MESON_PROJECT_SOURCE_ROOT`,
`MESON_PROJECT_BUILD_ROOT` and `MESON_PROJECT_DIST_ROOT` environment variables
are set when dist scripts are run. They are identical to `MESON_SOURCE_ROOT`,
`MESON_BUILD_ROOT` and `MESON_DIST_ROOT` for main project scripts, but for
subproject scripts they have the path to the root of the subproject appended,
usually `subprojects/<subproject-name>`.

Note that existing dist scripts likely need to be modified to use those new
environment variables instead of `MESON_DIST_ROOT` to work properly when used
from a subproject.
