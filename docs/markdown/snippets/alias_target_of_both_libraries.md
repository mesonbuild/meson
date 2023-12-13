## `alias_target` of `both_libraries`

Previously, when passing a [[@both_libs]] object to [[alias_target]], the alias
would only point to the shared library. It now points to both the static and the
shared library.
