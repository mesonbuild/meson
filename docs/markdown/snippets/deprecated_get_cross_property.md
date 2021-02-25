## `meson.get_cross_property()` has been deprecated

It's a pure subset of `meson.get_external_property`, and works strangely in
host == build configurations, since it would be more accurately described as
`get_host_property`.
