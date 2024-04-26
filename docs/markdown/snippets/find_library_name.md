## dependencies created by compiler.find_library implement the `name()` method

Previously, for a [[@dep]] that might be returned by either [[dependency]] or
[[compiler.find_library]], the method might or might not exist with no way
of telling.
