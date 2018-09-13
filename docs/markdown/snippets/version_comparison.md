## Version comparison

`dependency(version:)` and other version constraints now handle versions
containing non-numeric characters better, comparing versions using the rpmvercmp
algorithm (as using the `pkg-config` autoconf macro `PKG_CHECK_MODULES` does).

This is a breaking change for exact comparison constraints which rely on the
previous comparison behaviour of extending the compared versions with `'0'`
elements, up to the same length of `'.'`-separated elements.

For example, a version of `'0.11.0'` would previously match a version constraint
of `'==0.11'`, but no longer does, being instead considered strictly greater.

Instead, use a version constraint which exactly compares with the precise
version required, e.g. `'==0.11.0'`.
