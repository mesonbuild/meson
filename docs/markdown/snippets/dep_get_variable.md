## `dep.get_variable(varname)`

`dep.get_variable()` now has `varname` as first positional argument.
It is used as default value for `cmake`, `pkgconfig`, `configtool` and `internal`
keyword arguments. It is useful in the common case where `pkgconfig` and `internal`
use the same variable name, in which case it's easier to write `dep.get_variable('foo')`
instead of `dep.get_variable(pkgconfig: 'foo', internal: 'foo')`.

