## Compiler argument checking for `get_supported_arguments`

The compiler method `get_supported_arguments` now supports
a new keyword argument named `checked` that can be set to
one of `warn`, `require` or `off` (defaults to `off`) to
enforce argument checks.
