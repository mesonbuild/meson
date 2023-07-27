## `fs.copyfile`` now accept build target as source

It is now possible to use a build target as the first argument of
`fs.copyfile``.

One usecase is, on Windows, to copy a DLL beside a PYD that uses it,
for running tests, or to install it.
