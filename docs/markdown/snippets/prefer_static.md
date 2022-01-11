## New prefer_static built-in option

Users can now set a boolean, `prefer_static`, that controls whether or not
static linking should be tried before shared linking. This option acts as
strictly a preference. If the preferred linking method is not successful,
then Meson will fallback and try the other linking method. Specifically
setting the `static` kwarg in the meson.build will take precedence over
the value of `prefer_static` for that specific `dependency` or
`find_library` call.
