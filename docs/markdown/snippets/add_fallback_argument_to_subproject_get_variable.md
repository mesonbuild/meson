---
short-description: Add fallback argument to subproject.get_variable()
...

## subproject.get_variable() now accepts a `fallback` argument

Similar to `get_variable`, a fallback argument can now be passed to
`subproject.get_variable()`, it will be returned if the requested
variable name did not exist.

``` meson
var = subproject.get_variable('does-not-exist', 'fallback-value')
```
