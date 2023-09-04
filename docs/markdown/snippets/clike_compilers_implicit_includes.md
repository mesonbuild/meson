## Clarify of implicitly-included headers in C-like compiler checks

Compiler check methods `compiler.compute_int()`, `compiler.alignment()`
and `compiler.sizeof()` now have their implicitly-included headers
corrected and documented.

`<stdio.h>` was included unintentionally when cross-compiling, which
is less than ideal because there is no guarantee that a standard library
is available for the target platform. Only `<stddef.h>` is included instead.

For projects that depend on the old behavior, the compiler check methods
have an optional argument `prefix`, which can be used to specify additional
`#include` directives.
