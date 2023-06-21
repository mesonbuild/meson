## Add a `link_with` keyword to `rust.test()`

This can already be be worked around by creating `declare_dependency()` objects
to pass to the `dependencies` keyword, but this cuts out the middle man.
