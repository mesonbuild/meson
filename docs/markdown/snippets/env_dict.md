## Support taking environment values from a dictionary

`environment()` now accepts a dictionary as first argument.  If
provided, each key/value pair is added into the `environment_object`
as if `set()` method was called for each of them.

On the various functions that take an `env:` keyword argument, you may
now give a dictionary.
