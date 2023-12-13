## New `as_static` and `as_shared` methods on internal dependencies

[[@dep]] object returned by [[declare_dependency]] now has `.as_static()` and
`.as_shared()` methods, to convert to a dependency that prefers the `static`
or the `shared` version of the linked [[@both_libs]] target.

When the same dependency is used without those methods, the
`default_both_libraries` option determines which version is used.
