## Treat warnings as error in compiler checks

Compiler check methods `compiler.compiles()`, `compiler.links()` and `compiler.run()`
now have a new `werror: true` keyword argument to treat compiler warnings as error.
This can be used to check if code compiles without warnings.
