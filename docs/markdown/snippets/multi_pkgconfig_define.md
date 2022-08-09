## `pkgconfig_define` kwarg now supports multiple variables

The `pkgconfig_define` kwarg of [[dep.get_variable]] and `define_variable` kwarg of [[dep.get_pkgconfig_variable]] now accept multiple variables, consistent with pkg-config’s handling of `--define-variable` flag.
