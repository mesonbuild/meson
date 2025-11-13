## `rustc` will receive `-C embed-bitcode=no` and `-C lto` command line options

With this release, Meson passes command line arguments to `rustc` to
enable LTO when the `b_lto` built-in option is set to true.  As an
optimization, Meson also passes `-C embed-bitcode=no` when LTO is
disabled; note that this is incompatible with passing `-C lto` via
`rust_args`.
