## Compiler object now has `find_framework()` method

Returns a dependency equivalent to one from `dependency(..., method: 'extraframeworks')`.
Allows the user to specify search paths for the framework.

**NOTE:** Only use this function over other methods to find frameworks if it is necessary
to specify the paths in which the framework may be found.
