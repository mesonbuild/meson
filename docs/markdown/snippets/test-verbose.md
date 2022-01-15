## New keyword argument `verbose` for tests and benchmarks

The new keyword argument `verbose` can be used to mark tests and benchmarks
that must always be logged verbosely on the console.  This is particularly
useful for long-running tests, or when a single Meson test() is wrapping
an external test harness.
