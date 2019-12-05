## meson dist --include-subprojects

`meson dist` command line now gained `--include-subprojects` command line option.
When enabled, the source tree of all subprojects used by the current build will
also be included in the final tarball. This is useful to distribute self contained
tarball that can be built offline (i.e. `--wrap-mode=nodownload`).
