## Qt.preprocess source arguments deprecated

The `qt.preprocess` method currently has this signature:
`qt.preprocess(name: str | None, *srcs: str)`, this is not a nice signature
because it's confusing, and there's a `sources` keyword argument as well.
Both of these pass sources through unmodified, this is a bit of a historical
accident, and not the way that any other module works. These have been
deprecated, so instead of:
```meson
sources = qt.preprocess(
    name,
    list, of, sources,
    sources : [more, sources],
    ... # things to process,
)

executable(
    'foo',
    sources,
)
```
use
```meson
processed = qt.preprocess(
    name,
    ... # thins to process
)

executable(
    'foo',
    'list', 'of', 'sources', 'more', 'sources', processed,
)
```
