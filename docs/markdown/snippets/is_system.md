## Added `is_system` kwarg to `dependency`

Similar to `include_directories()`, the `dependency()` function now
also has a `is_system` kwarg. If it is enabled, all include directories
of the dependency are marked as system dependencies.

Additionally, it is also possible to check and change the `is_system`
state of an existing dependency object with the new `is_system()` and
`as_system()` methods.
