## rust.bindgen accepts a dependency argument

The `bindgen` method of the `rust` module now accepts a dependencies argument.
Any include paths in these dependencies will be passed to the underlying call to
`clang`, and the call to `bindgen` will correctly depend on any generatd sources.
