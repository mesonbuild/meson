## pkg-config dependencies can now get a variable with multiple replacements

When using [[dep.get_variable]] and defining a `pkgconfig_define`, it is
sometimes useful to remap multiple dependency variables. For example, if the
upstream project changed the variable name that is interpolated and it is
desirable to support both versions.

It is now possible to pass multiple pairs of variable/value.

The same applies to the compatibility [[dep.get_pkgconfig_variable]] method.
