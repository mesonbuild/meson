## Added `include_type` kwarg to `dependency`

The `dependency()` function now has a `include_type` kwarg. It can take the
values `'preserve'`, `'system'` and `'non-system'`. If it is set to `'system'`,
all include directories of the dependency are marked as system dependencies.

The default value of `include_type` is `'preserve'`.

Additionally, it is also possible to check and change the `include_type`
state of an existing dependency object with the new `include_type()` and
`as_system()` methods.
