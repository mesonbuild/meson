## `compiler.run()` results are marked as not compiled if the program fails

When the program given to `compiler.run()` was built successfully but exited with a nonzero
status, the `compiled()` method of the result used to return `true`.  It now returns `false`,
as it does for a program that does not compile.  For backwards compatibility you can
still check for zero `returncode()`, in addition to checking for `compiled()` being `true`.
