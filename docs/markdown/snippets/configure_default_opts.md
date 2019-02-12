## meson configure can now print the default options of an unconfigured project

With this release, it is also possible to get a list of all build options
by invoking `meson configure` with the project source directory or
the path to the root `meson.build`. In this case, meson will print the
default values of all options.
