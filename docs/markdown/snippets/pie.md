## Position-independent executables

When `b_pie` option, or `executable()`'s `pie` keyword argument is set to
`true`, position-independent executables are built. All their objects are built
with `-fPIE` and the executable is linked with `-pie`. Any static library they
link must be built with `pic` set to `true` (see `b_staticpic` option).
