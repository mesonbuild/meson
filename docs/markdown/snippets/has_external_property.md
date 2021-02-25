## Check if native or cross-file properties exist

It is now possible to check whether a native property or a cross-file property
exists with `meson.has_external_property('foo')`. This is useful if the
property in question is a boolean and one wants to distinguish between
"set" and "not provided" which can't be done the usual way by passing a
fallback parameter to `meson.get_external_property()` in this particular case.
