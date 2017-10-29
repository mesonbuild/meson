# Adds support for additional Qt5-Module keyword `moc_extra_arguments`

When `moc`-ing sources, the `moc` tool does not know about any
preprocessor macros. The generated code might not match the input
files when the linking with the moc input sources happens.

This amendment allows to specify a a list of additional arguments
passed to the `moc` tool. They are called `moc_extra_arguments`.