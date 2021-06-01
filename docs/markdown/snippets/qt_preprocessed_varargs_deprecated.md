## Qt.preprocess positional source arguments deprecated

The `qt.preprocess` method currently has this signature:
`qt.preprocess(name: str | None, *srcs: str)`, this is not a nice signature
because it's confusing, and there's a `sources` keyword argument that does
exactly the same thing. Instead of
```meson
qt.preprocess(name, list, of, sources)
```
use
```meson
qt.preprocess(
    name,
    sources : [list,  of , sources],
)
```