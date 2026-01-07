## `python_installation.install_sources()` now supports custom targets

Previously, `python_installation.install_sources()` only supported
`File` and `str` type sources. Now, you can use it with any file-like
variables, including those produced by `custom_target()`.
