## `introspect --buildoptions` can now be used without configured build directory

It is now possible to run `meson introspect --buildoptions /path/to/meson.build`
without a configured build directory.

Running `--buildoptions` without a build directory produces the same output as running
it with a freshly configured build directory.

However, this behavior is not guaranteed if subprojects are present. Due to internal
limitations all subprojects are processed even if they are never used in a real meson run.
Because of this options for the subprojects can differ.