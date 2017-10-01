## Portability improvements to Boost Dependency

The Boost dependency has been improved to better detect the various ways to
install boost on multiple platforms. At the same time the `modules` semantics
for the dependency has been changed. Previously it was allowed to specify
header directories as `modules` but it wasn't required. Now, modules are only
used to specify libraries that require linking.

This is a breaking change and the fix is to remove all modules that aren't
found.
