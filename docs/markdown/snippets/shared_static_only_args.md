## `<lang>_(shared|static)_args` for both_library, library, and build_target

We now allow passing arguments like `c_static_args` and `c_shared_args`. This
allows a [[both_libraries]] to have arguments specific to either the shared or
static library, as well as common arguments to both.

There is a drawback to this, since Meson now cannot re-use object files between
the static and shared targets. This could lead to much higher compilation time
when using a [[both_libraries]] if there are many sources.
